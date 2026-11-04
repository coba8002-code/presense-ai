'use strict';
(()=>{
 const guide=PetSenseGuide,el=id=>document.getElementById(id),ko=guide.language==='ko';
 const t=ko?{title:'05 / 함께 돌보기',intro:'선택한 개의 보관 중인 전체 상황·후속 일지를 읽기 전용으로 공유합니다. 만료 전 새 일지도 포함됩니다. 소리·회원 정보는 제외됩니다. 상대가 이미 보거나 복사한 내용은 철회해도 회수할 수 없습니다.',days:'공유 기간',day:'1일',week:'7일',consent:'위 공유 범위를 이해하고 초대 생성 또는 수락에 동의합니다.',create:'선택한 개의 초대 코드 만들기',code:'받은 초대 코드',accept:'초대 수락',load:'공유 목록 새로고침',sent:'내가 보낸 공유',received:'받은 공유',read:'일지 읽기',revoke:'공유 철회 / 나가기',confirm:'이 공유 접근을 즉시 종료할까요?',pending:'수락 대기',accepted:'수락됨',empty:'공유가 없습니다.',created:'아래 코드는 한 번만 표시됩니다. 신뢰하는 한 사람에게 직접 전달하세요. 수락 기한: ',failed:'요청을 완료하지 못했습니다. 로그인·동의·코드·만료를 확인하세요. 초대 생성 응답이 불확실하면 목록에서 이전 초대를 철회한 뒤 다시 만드세요.',done:'완료했습니다.',next:'다음 50개',detail:'상황 및 후속 보기',source:'보호자 진술 · 모델 분석/교정 효과 증거 아님',expires:'접근 만료'}:{title:'05 / Care together',intro:'Share read-only access to all retained cases and followups for the selected dog, including new cases until expiry. Audio and member details are excluded. Revoking access cannot recall anything already viewed or copied.',days:'Access duration',day:'1 day',week:'7 days',consent:'I understand this scope and consent to creating or accepting an invitation.',create:'Create an invitation for the selected dog',code:'Invitation code received',accept:'Accept invitation',load:'Refresh sharing',sent:'Invitations I sent',received:'Shared with me',read:'Read journal',revoke:'Revoke / leave',confirm:'End this shared access now?',pending:'Pending',accepted:'Accepted',empty:'No shared access.',created:'This code is shown once. Send it directly to one trusted person. Accept before: ',failed:'Could not complete the request. Check login, consent, code and expiry. If creation is uncertain, refresh and revoke the old invitation before creating another.',done:'Completed.',next:'Next 50',detail:'Read case and followups',source:'Guardian report · not model analysis or evidence of training efficacy',expires:'Access expires'};
 const panel=el('care');let epoch=0,active=null;
 const date=value=>new Date(value*1000).toLocaleString(ko?'ko-KR':'en');
 const text=(tag,value,parent)=>{const node=document.createElement(tag);node.textContent=value;parent.append(node);return node;};
 for(const node of panel.querySelectorAll('[data-care]'))node.textContent=t[node.dataset.care];
 function controls(){for(const node of panel.querySelectorAll('button,input,select'))node.disabled=Boolean(active)||!guide.identity();el('care-create').disabled=Boolean(active)||!guide.identity()||!guide.selectedId();}
 function reset(){epoch++;active?.abort();active=null;for(const id of ['care-secret','care-status','care-sent','care-received','care-cases','care-detail'])el(id).replaceChildren();el('care-code').value='';el('care-consent').checked=false;controls();}
 async function action(fn){
  if(active||!guide.identity())return;
  const mine=epoch,identity=guide.identity(),controller=new AbortController();active=controller;controls();
  const current=()=>mine===epoch&&guide.identity()===identity;
  const api=async(path='',options={})=>{const result=await guide.api('/v1/me/care-shares'+path,{...options,signal:controller.signal});if(!current())throw new Error();return result;};
  try{await fn(api);}catch(error){if(current())el('care-status').textContent=t.failed;}finally{if(active===controller){active=null;controls();}}
 }
 function button(label,parent,fn){const node=text('button',label,parent);node.type='button';node.className='secondary';node.onclick=fn;return node;}
 async function list(api){
  const data=await api();
  for(const side of ['sent','received']){
   const container=el('care-'+side);container.replaceChildren();
   if(!data[side].length)text('p',t.empty,container);
   for(const grant of data[side]){
    const item=text('article','',container);item.className='journal-entry';
    text('strong',grant.pet_name+' · '+t[grant.status],item);text('p',grant.id+' · '+t.expires+': '+date(grant.expires),item);
    if(side==='received')button(t.read,item,()=>action(api=>cases(api,grant.id)));
    button(t.revoke,item,()=>{if(confirm(t.confirm))action(async api=>{await api('/'+grant.id,{method:'DELETE',headers:{'X-Delete-Confirm':'leave-or-revoke'}});el('care-secret').replaceChildren();el('care-cases').replaceChildren();el('care-detail').replaceChildren();await list(api);});});
   }
  }
 }
 async function cases(api,id,offset=0){
  el('care-cases').replaceChildren();el('care-detail').replaceChildren();
  const data=await api('/'+id+'/journal?offset='+offset),container=el('care-cases');
  if(!data.items.length)text('p',t.empty,container);
  for(const row of data.items){const item=text('article','',container);item.className='journal-entry';text('strong',row.pet_name+' · '+(PetSenseCase.copy[guide.language][row.data.behavior]||row.data.behavior),item);button(t.detail,item,()=>action(async api=>{
   el('care-detail').replaceChildren();const detail=await api('/'+id+'/journal/'+row.id),target=el('care-detail');text('h3',t.source,target);
   // Render values as text only; no HTML from another guardian is interpreted.
   const c=PetSenseCase.copy[guide.language],j=PetSenseJournal.copy[guide.language],data=detail.data;
   text('p',new Date(data.observed_at).toLocaleString(ko?'ko-KR':'en'),target);
   for(const [key,label] of [['before',c.noteBefore],['during',c.noteDuring],['after',c.noteAfter]])text('p',label+': '+(data[key]||'—'),target);
   for(const [key,label] of [['duration',c.noteDuration],['change',c.noteChange],['dogs',c.noteDogs]])text('p',label+': '+c[data[key]],target);
   if(data.health_concern)text('p',c.healthAdvice,target);
   text('h3',j.followups,target);
   for(const follow of detail.followups){const f=follow.data; text('p',new Date(f.observed_at).toLocaleString(ko?'ko-KR':'en')+' · '+j[f.action]+' · '+f.what_done+' · '+j[f.outcome]+' · '+f.note,target);}
  }));}
  if(data.next_offset!==null)button(t.next,container,()=>action(api=>cases(api,id,data.next_offset)));
 }
 el('care-load').onclick=()=>action(async api=>{el('care-cases').replaceChildren();el('care-detail').replaceChildren();await list(api);});
 el('care-create').onclick=()=>action(async api=>{
  if(!el('care-consent').checked||!guide.selectedId())throw new Error();
  el('care-secret').replaceChildren();const grant=await api('',{method:'POST',headers:{'Content-Type':'application/json','X-Journal-Consent':'care-sharing-v1'},body:JSON.stringify({pet_id:guide.selectedId(),days:Number(el('care-days').value)})});
  text('p',t.created+date(grant.invite_expires),el('care-secret'));text('code',grant.code,el('care-secret'));el('care-consent').checked=false;await list(api);
 });
 el('care-accept').onclick=()=>action(async api=>{
  if(!el('care-consent').checked)throw new Error();
  await api('/accept',{method:'POST',headers:{'Content-Type':'application/json','X-Journal-Consent':'care-sharing-v1'},body:JSON.stringify({code:el('care-code').value.trim()})});el('care-code').value='';el('care-consent').checked=false;await list(api);el('care-status').textContent=t.done;
 });
 el('care-days').onchange=()=>{el('care-consent').checked=false;};
 window.addEventListener('petsense-guide-change',reset);window.addEventListener('pagehide',reset);guide.ready.then(controls);controls();
})();
