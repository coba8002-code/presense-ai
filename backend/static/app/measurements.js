'use strict';
(()=>{
 const $=id=>document.getElementById(id),session=globalThis.PetSenseSession;
 let epoch=0,active=null,contexts=[];
 const identity=()=>session?.identity()||'',pet=()=>globalThis.PetSenseProfiles?.selectedId()||'';
 const stratum=()=>[$('measurement-device').value,$('measurement-condition').value,$('measurement-source').value].join('|');
 function clear(){epoch++;active?.abort();active=null;$('measurements-load').disabled=!identity();$('measurement-baseline').replaceChildren();$('measurement-list').replaceChildren();$('measurements-status').textContent='';}
 function reset(){clear();$('measurement-device').value='';$('measurement-condition').value='unknown';$('measurement-source').value='pretrained_model';contexts=[];$('measurement-contexts').replaceChildren();$('measurement-consent').checked=false;$('measurement-identity').checked=false;}
 function text(tag,value,parent){const node=document.createElement(tag);node.textContent=value;parent.append(node);return node;}
 function consent(){return $('measurement-consent').checked&&$('measurement-identity').checked;}
 async function action(fn,requiresDevice=true){
  if(active)return;const who=identity(),dog=pet(),group=stratum(),ticket=epoch;
  if(!who||!dog||(requiresDevice&&!$('measurement-device').value)){$('measurements-status').textContent='로그인·반려견 프로필·기기 구분명을 확인하세요.';return;}
  const controller=new AbortController();active=controller;$('measurements-load').disabled=true;
  const current=()=>ticket===epoch&&who===identity()&&dog===pet()&&group===stratum();
  const api=async(path='',options={})=>{
   if(!current())throw new Error('changed');
   const r=await fetch('/v1/me/observations'+path,{...options,credentials:'same-origin',signal:controller.signal,headers:{'Content-Type':'application/json',...session.headers(),'X-Observation-Consent':consent()?'model-metadata-v1':'',...options.headers}});
   if(r.status===401)session.invalidate();if(!r.ok)throw new Error(String(r.status));
   const data=r.status===204?null:await r.json();if(!current())throw new Error('changed');return data;
  };
  try{await fn(api,dog);}catch(e){if(current())$('measurements-status').textContent='출처·동의·같은 개·기기/조건을 확인하세요. 변경 불가 기록은 삭제 후 다시 저장할 수 있습니다.';}
  finally{if(active===controller){active=null;$('measurements-load').disabled=!identity();}}
 }
 async function load(api,dog){
  const q=new URLSearchParams({pet_id:dog,device_id:$('measurement-device').value,condition:$('measurement-condition').value,source_kind:$('measurement-source').value});
  const r=await api('?'+q);$('measurement-list').replaceChildren();$('measurement-baseline').replaceChildren();
  const b=r.baseline;const pane=$('measurement-baseline');
  text('p','출처: '+b.source_kind+' · 같은 모델/버전·기기·상황·길이 구간만 비교 · 단위: 미보정 점수',pane);
  text('p',b.ready?'과거 '+b.historical_days+'일의 일별 점수 평균 중앙값 (발성 빈도·감정·개선 효과 아님)':'모델 점수 기준선 미충족 · 확인한 측정 상황과 이전 날짜 5일 이상 필요',pane);
  if(b.medians)for(const [label,value]of Object.entries(b.medians))text('p',label+': '+value.toFixed(3)+' · 최신 점수 차이 '+b.deltas[label].toFixed(3),pane);
  for(const row of r.items){const box=text('article','',$('measurement-list'));box.className='record';box.dataset.observationId=row.id;
   text('strong','관찰 '+row.id,box);text('p',row.source_kind+' · '+row.model+' @ '+row.revision,box);text('p','작업 제출 시각 '+new Date(row.submitted*1000).toLocaleString()+' · 실제 촬영 시각/개체 확인 아님',box);
   for(const s of row.scores)text('p',s.label+': '+s.score.toFixed(3),box);
   text('p','피드백: '+(row.feedback?({unreviewed:'미검토',reviewed_not_training_approved:'검토 기록 있음 (정답 검증 아님)',needs_more_evidence:'추가 근거 필요',disputed:'검토 불일치'}[row.feedback.status]||'확인 필요')+' ('+row.feedback.reason+')':'없음')+' · 학습 정답 아님',box);
   const reasons=document.createElement('select');reasons.setAttribute('aria-label','피드백 이유');for(const [value,name]of [['not_sure','모르겠음'],['noise','소음 우려'],['wrong_dog','다른 개 우려'],['context_missing','맥락 부족'],['seems_right','비슷해 보임']]){const o=document.createElement('option');o.value=value;o.textContent=name;reasons.append(o);}box.append(reasons);
   const feedback=text('button','피드백 제출',box);feedback.onclick=()=>{if(!consent()){$('measurements-status').textContent='피드백 보관 동의를 확인하세요.';return;}action(async(a,d)=>{await a('/'+row.id+'/feedback',{method:'POST',body:JSON.stringify({reason:reasons.value})});await load(a,d);});};
   if(row.feedback){const withdraw=text('button','피드백 철회',box);withdraw.onclick=()=>action(async(a,d)=>{await a('/'+row.id+'/feedback',{method:'DELETE',headers:{'X-Delete-Confirm':'delete-feedback'}});await load(a,d);});}
   const erase=text('button','관찰·피드백 삭제',box);erase.onclick=()=>action(async(a,d)=>{await a('/'+row.id,{method:'DELETE',headers:{'X-Delete-Confirm':'delete-observation'}});await load(a,d);});
  }
  $('measurements-status').textContent=r.items.length+'개 · 원본 소리 비보관 · 자동 학습 없음';
 }
 globalThis.PetSenseMeasurements={saveJob:row=>{
  if(!consent()||pet()!==row.pet_id){$('measurements-status').textContent='같은 프로필·개체 확인·별도 보관 동의가 필요합니다.';return;}
  // Changing source here invalidates old rows, never reclassifies a stored measurement.
  $('measurement-source').value=row.result.execution_kind;clear();
  return action(async(api,dog)=>{await api('',{method:'POST',body:JSON.stringify({job_id:row.id,device_id:$('measurement-device').value,condition:$('measurement-condition').value,same_dog_confirmed:true})});await load(api,dog);});
 },reset};
 $('measurement-contexts-load').onclick=()=>action(async api=>{
  const q=new URLSearchParams({pet_id:pet(),device_id:'_',condition:'unknown',source_kind:'pretrained_model'});const r=await api('?'+q);contexts=r.strata;
  $('measurement-contexts').replaceChildren();const blank=document.createElement('option');blank.value='';blank.textContent='조건 선택';$('measurement-contexts').append(blank);
  contexts.forEach((c,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=c.device_id+' / '+c.condition+' / '+c.source_kind;$('measurement-contexts').append(o);});
 },false);
 $('measurement-contexts').onchange=()=>{const c=contexts[Number($('measurement-contexts').value)];if($('measurement-contexts').value===''||!c)return;$('measurement-device').value=c.device_id;$('measurement-condition').value=c.condition;$('measurement-source').value=c.source_kind;clear();};
 $('measurements-load').onclick=()=>action(load);
 for(const id of ['measurement-device','measurement-condition','measurement-source'])$(id).addEventListener(id==='measurement-device'?'input':'change',clear);
 for(const id of ['measurement-consent','measurement-identity'])$(id).onchange=()=>{if(!consent())clear();};
 for(const event of ['petsense-session-change','petsense-profile-change','petsense-observations-invalidated','pagehide'])window.addEventListener(event,reset);
 session.ready.then(clear);clear();
})();
