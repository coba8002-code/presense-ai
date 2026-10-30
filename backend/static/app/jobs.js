'use strict';
(()=>{
 const el=id=>document.getElementById(id);
 const names={queued:'대기 중',running:'분석 중',succeeded:'완료',failed:'실패',cancelled:'취소됨',expired:'기한 만료'};
 let epoch=0,active=null,timer=null,polls=0;
 function text(tag,value,parent){const node=document.createElement(tag);node.textContent=value;parent.append(node);return node;}
 function reset(){epoch++;clearTimeout(timer);if(active)active.abort();active=null;el('job-submit').disabled=false;el('jobs-refresh').disabled=false;el('jobs-list').replaceChildren();el('jobs-status').textContent='';}
 async function action(fn){
  if(active)return;const session=el('notes-session').value,mine=epoch,controller=new AbortController();
  if(!session){el('jobs-status').textContent='계정 세션을 입력하세요.';return;}
  active=controller;el('job-submit').disabled=true;el('jobs-refresh').disabled=true;
  const current=()=>epoch===mine&&el('notes-session').value===session;
  async function api(path='',method='GET',body,extra={}){
   if(!current())throw new Error('세션이 변경되었습니다.');
   let response;try{response=await fetch('/v1/me/audio-jobs'+path,{method,signal:controller.signal,headers:{'X-PetSense-Session':session,'X-Delete-Confirm':method==='DELETE'?'cancel-job':'',...extra},body});}
   catch(error){throw new Error('연결을 확인하세요. 접수 여부는 작업 목록에서 확인하고 다시 등록하세요.');}
   if(!response.ok)throw new Error(({401:'세션이 만료되었거나 철회되었습니다.',403:'분석·임시 보관 동의를 확인하세요.',404:'작업 또는 반려견 프로필을 찾을 수 없습니다.',409:'같은 접수 번호의 내용이 다릅니다.',413:'선택 구간이 너무 큽니다.',422:'반려견 프로필과 소리 형식을 확인하세요.',429:'작업 한도에 도달했습니다. 완료 후 다시 시도하세요.',503:'서버의 분석 작업 설정이 필요합니다.'})[response.status]||'분석 작업 요청에 실패했습니다.');
   const data=await response.json();if(!current())throw new Error('세션이 변경되었습니다.');return data;
  }
  try{await fn(api,current);}catch(error){if(current())el('jobs-status').textContent=error.message;}
  finally{if(active===controller){active=null;el('job-submit').disabled=false;el('jobs-refresh').disabled=false;}}
 }
 function render(rows){
  el('jobs-list').replaceChildren();
  for(const row of rows){const article=text('article','',el('jobs-list'));article.className='record';text('strong',(names[row.status]||'확인 필요')+' · '+new Date(row.created*1000).toLocaleString('ko-KR'),article);
   if(row.error)text('p',({worker_lost:'작업자가 중단됐습니다. 소리를 확인한 뒤 새 작업으로 등록하세요.',deadline_exceeded:'분석 제한 시간을 초과했습니다.',model_unavailable:'모델 캐시·실행 환경을 확인하세요.',expired:'대기 가능한 시간이 지났습니다.',session_revoked:'등록 세션이 만료되거나 철회되었습니다.',client_cancelled:'취소하고 원본·결과를 삭제했습니다.'})[row.error]||'분석을 완료하지 못했습니다.',article);
   if(row.status==='succeeded'&&row.result){text('p','소리 사건 점수 · 감정·원인 판단 보류',article);for(const score of row.result.dog_event_scores||[])text('p',score.label+': '+Number(score.score).toFixed(3),article);}
   if(!['cancelled','expired'].includes(row.status)){const button=text('button','작업 취소·결과 삭제',article);button.className='secondary';button.onclick=()=>{if(active||!confirm('이 작업을 취소하고 보관 중인 소리·결과를 삭제할까요?'))return;return action(async api=>{await api('/'+encodeURIComponent(row.id),'DELETE');await load(api);});};}
  }
 }
 async function load(api){const data=await api();render(data.items);clearTimeout(timer);const pending=data.items.some(r=>['queued','running'].includes(r.status));
  if(pending&&polls<60){polls++;timer=setTimeout(()=>action(load),1000);el('jobs-status').textContent='작업을 처리하고 있습니다. 이 화면을 닫아도 서버 작업은 계속됩니다.';}
  else el('jobs-status').textContent=pending?'자동 조회를 잠시 멈췄습니다. 작업 조회로 다시 확인하세요.':'최근 분석 작업 '+data.items.length+'개를 확인했습니다.';
 }
 el('jobs-refresh').onclick=()=>{polls=0;return action(load);};
 el('job-submit').onclick=()=>action(async(api,current)=>{
  const petId=globalThis.PetSenseProfiles?.selectedId();
  if(!petId)throw new Error('분석할 반려견 프로필을 먼저 선택하세요.');
  if(!el('consent').checked||!el('job-consent').checked)throw new Error('분석 동의와 별도의 임시 보관 동의를 확인하세요.');
  const source=globalThis.PetSenseAnalysisInput();if(!source.file)throw new Error('녹음하거나 소리 파일을 선택하세요.');
  el('jobs-status').textContent='선택 구간을 준비하고 있습니다.';
  const input=await PetSenseAudio.convert(source.file,source.start);
  if(!current())return;
  if(!el('consent').checked||!el('job-consent').checked||globalThis.PetSenseProfiles?.selectedId()!==petId)throw new Error('동의나 선택 프로필이 변경되어 등록하지 않았습니다.');
  await api('','POST',input.blob,{'Content-Type':'audio/wav','X-Audio-Consent':'true','X-Audio-Species':'dog','X-Job-Storage-Consent':'true','X-PetSense-Pet-ID':petId,'Idempotency-Key':crypto.randomUUID()});
  polls=0;await load(api);
 });
 el('notes-session').addEventListener('input',reset);
 window.addEventListener('pagehide',reset);
 globalThis.PetSenseJobs={reset};
})();
