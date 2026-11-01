'use strict';
(() => {
 const $=id=>document.getElementById(id), video=$('video');
 let url=null, epoch=0, controller=null, times=[], ready=false, events=[];
 const allowed=()=> $('consent').checked && $('identity').checked;
 function clear(message='취소·기록 삭제됨') {
  epoch++;if(controller)controller.abort();controller=null;ready=false;times=[];
  video.pause();video.controls=true;video.removeAttribute('src');video.load();if(url)URL.revokeObjectURL(url);url=null;
  events=[];$('event-input').disabled=true;$('event-status').textContent='이벤트 없음 · 발성 개체 미확인';$('event-start').value='';$('event-end').value='';$('clip').value='';$('frames').replaceChildren();$('result').textContent='판단 유보 · 관찰 기록 없음';
  $('extract').disabled=true;$('summarize').disabled=true;$('status').textContent=message;
 }
 function wait(event,signal,action) {
  return new Promise((resolve,reject)=>{
   let timer;const finish=(error)=>{clearTimeout(timer);video.removeEventListener(event,done);video.removeEventListener('error',fail);signal.removeEventListener('abort',abort);error?reject(error):resolve();};
   const done=()=>finish(),fail=()=>finish(new Error('decode')),abort=()=>finish(new Error('cancel'));
   video.addEventListener(event,done,{once:true});video.addEventListener('error',fail,{once:true});signal.addEventListener('abort',abort,{once:true});timer=setTimeout(()=>finish(new Error('timeout')),5000);
   try{action();}catch(e){finish(e);}
  });
 }
 for(const id of ['consent','identity'])$(id).addEventListener('change',()=>{clear('동의·개체 확인 변경으로 영상과 기록을 지웠습니다.');$('clip').disabled=!allowed();});
 $('cancel').onclick=()=>clear('취소됨 · 영상과 관찰 기록을 지웠습니다.');
 $('clip').onchange=async()=>{
  const file=$('clip').files[0];clear('파일 확인 중');if(!file)return;
  if(!allowed()||!['video/mp4','video/webm'].includes(file.type)||file.size>25*1024*1024||!file.size){$('status').textContent='지원되는 25 MB 이하 MP4/WebM을 선택하세요.';return;}
  controller=new AbortController();const signal=controller.signal, ticket=epoch;
  url=URL.createObjectURL(file);
  try{await wait('loadedmetadata',signal,()=>{video.src=url;});
   if(ticket!==epoch)return;
   if(!Number.isFinite(video.duration)||video.duration<.5||video.duration>30||!video.videoWidth||video.videoWidth>1920||video.videoHeight>1080)throw new Error('bounds');
   ready=true;$('event-input').disabled=false;$('event-add').disabled=false;$('events-clear').disabled=false;$('extract').disabled=false;$('status').textContent=`${video.duration.toFixed(2)}초 · 모델 미연결 · 기기 내 관찰 준비됨`;
  }catch(e){if(ticket===epoch)clear('영상 길이·해상도·디코딩을 확인할 수 없습니다. 다른 짧은 영상을 선택하세요.');}
 };
 function invalidateFrames(){
  epoch++;if(controller)controller.abort();video.pause();video.controls=true;times=[];
  $('frames').replaceChildren();$('summarize').disabled=true;$('extract').disabled=!ready;
  $('result').textContent='판단 유보 · 이벤트 변경으로 장면을 다시 확인하세요.';
 }
 $('event-add').onclick=()=>{
  if(!ready||!allowed())return;
  try{
   const a=$('event-start').value,b=$('event-end').value;if(a===''||b==='')throw new Error('missing');
   events=PetTimeline.normalize([...events,{label:$('event-label').value,start:Number(a),end:Number(b)}],video.duration);
   invalidateFrames();const summary=PetTimeline.summarize(events);
   $('event-status').textContent=`보호자 표시 ${summary.count}개 · 발성 개체 미확인 · 간격: ${summary.intervals.join(', ')||'없음'}초 · 첫 3개 이벤트 주변만 추출`;
  }catch(e){$('event-status').textContent='시작·종료 시각과 최대 20개 한도를 확인하세요.';}
 };
 $('events-clear').onclick=()=>{events=[];invalidateFrames();$('event-status').textContent='이벤트 없음 · 발성 개체 미확인';};
 function select(id,options){const s=document.createElement('select');s.id=id;for(const [value,text]of options){const o=document.createElement('option');o.value=value;o.textContent=text;s.append(o);}s.onchange=()=>{$('result').textContent='판단 유보 · 관찰 변경됨. 다시 확인하세요.';};return s;}
 $('extract').onclick=async()=>{
  if(!ready||!allowed())return;
  epoch++;const ticket=epoch;if(controller)controller.abort();controller=new AbortController();const signal=controller.signal;
  $('extract').disabled=true;$('summarize').disabled=true;$('frames').replaceChildren();times=[];$('result').textContent='판단 유보 · 장면 추출 중';video.pause();video.controls=false;
  try{
   const targets=PetTimeline.plan(video.duration,events);
   for(let i=0;i<targets.length;i++){
    const target=targets[i];
    await wait('seeked',signal,()=>{video.currentTime=target;});
    if(ticket!==epoch||!allowed())return;
    if(Math.abs(video.currentTime-target)>.25)throw new Error('alignment');
    const canvas=document.createElement('canvas');canvas.width=Math.min(640,video.videoWidth);canvas.height=Math.round(canvas.width*video.videoHeight/video.videoWidth);
    canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);const actual=video.currentTime;times.push(actual);
    const card=document.createElement('article');card.className='frame';const title=document.createElement('h3');title.textContent=`${i+1} · ${actual.toFixed(2)}초`;
    const img=document.createElement('img');img.src=canvas.toDataURL('image/jpeg',.75);img.alt=`${actual.toFixed(2)}초 장면`;
    card.append(title,img);
    for(const [key,name,opts]of [
     ['visible','가시성',[['unknown','판단 불가 / 다른 개'],['clear','같은 개 · 명확히 보임']]],
     ['posture','자세',[['unknown','모름'],['crouching','웅크림'],['standing','서 있음'],['sitting','앉음'],['lying','누움']]],
     ['ears','귀',[['unknown','모름 / 가려짐'],['back','뒤로 향함'],['forward','앞으로 향함'],['neutral','중립']]],
     ['tail','꼬리',[['unknown','모름 / 가려짐'],['tucked','다리 사이로 말림'],['raised','올라감'],['lowered','내려감']]]]){
      const label=document.createElement('label');label.textContent=name;label.append(select(`${key}-${i}`,opts));card.append(label);
    }
    $('frames').append(card);
   }
   $('summarize').disabled=false;$('status').textContent=`${times.length}개 장면 준비됨 · 자동 행동 분석이 아닙니다.`;
  }catch(e){if(ticket===epoch)clear('추출 중단 · 부분 장면은 폐기했습니다. 지원되는 영상으로 다시 시도하세요.');}
  finally{if(ticket===epoch){video.controls=true;$('extract').disabled=!ready;}}
 };
 $('summarize').onclick=()=>{
  if(!allowed()||times.length<1)return;
  const accepted=times.map((t,i)=>({t,i})).filter(f=>$(`visible-${f.i}`).value==='clear');
  const support=accepted.filter(f=>$(`posture-${f.i}`).value==='crouching'&&$(`ears-${f.i}`).value==='back'&&$(`tail-${f.i}`).value==='tucked');
  const opposing=accepted.filter(f=>!support.includes(f));
  const candidate=support.length>=2&&support.length===accepted.length&&support.at(-1).t-support[0].t>=.5;
  $('result').textContent=`근거 출처: 보호자 직접 입력 · AI 추론 없음\n명확한 동일 개체 장면: ${accepted.length}/${times.length}\n`+(candidate?
   `검증 전 가설: 회피 가능성\n근거 시각: ${support.map(f=>f.t.toFixed(2)+'초').join(', ')}\n단서: 웅크림·뒤로 향한 귀·말린 꼬리\n대안: 일시적 자세, 카메라·환경 반응, 관찰되지 않은 맥락\n`:'판단 유보: 단서 부족 또는 상충하는 자세가 있습니다.\n')+
   `반대·불일치 근거 시각: ${opposing.map(f=>f.t.toFixed(2)+'초').join(', ')||'선택 장면에서 확인되지 않음'}\n부족 정보: 실제 자극·장면 사이 동작·개체 추적·독립 검토\n보호자 표시 소리 ${events.length}개 · 발성 개체 미확인\n`+
   '감정·의도·행동 원인: 판단할 수 없음\n다음 관찰: 직전 자극, 자발적 접근·후퇴, 회복 상황을 기록하세요.\n장면 사이 움직임과 소리는 분석하지 않았습니다.';
 };
 video.addEventListener('error',()=>{if(ready)clear('영상 재생 중단 · 기록 삭제됨');});
 window.addEventListener('pagehide',()=>clear());
})();

