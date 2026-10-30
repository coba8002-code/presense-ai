'use strict';
(()=>{
 const el=id=>document.getElementById(id);let offset=0,busy=false;
 function add(tag,value,parent){const node=document.createElement(tag);node.textContent=value;parent.append(node);return node;}
 async function api(path,method='GET',body){
  const session=el('notes-session').value;
  if(!session)throw new Error('PC에서 발급받은 기록 보관 세션을 입력하세요.');
  const response=await fetch(path,{method,headers:{'X-PetSense-Session':session,'X-Storage-Consent':String(el('notes-consent').checked),'X-Delete-Confirm':method==='DELETE'&&path.endsWith('/account')?'delete-account':'','Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
  if(!response.ok)throw new Error(({401:'세션이 만료되었거나 유효하지 않습니다.',403:'서버 보관 동의를 확인하세요.',404:'메모를 찾을 수 없습니다.',409:'보관 한도 500개에 도달했습니다.',422:'이름과 메모 길이를 확인하세요.',503:'서버의 계정 보관 설정이 필요합니다.'})[response.status]||'서버 메모 요청에 실패했습니다.');
  return response.status===204?null:response.json();
 }
 async function action(fn){if(busy)return;busy=true;for(const id of ['notes-load','notes-save','notes-next','notes-delete-account','notes-session'])el(id).disabled=true;try{await fn();}catch(error){el('notes-list').replaceChildren();el('notes-next').hidden=true;el('notes-status').textContent=error.message;}finally{busy=false;for(const id of ['notes-load','notes-save','notes-next','notes-delete-account','notes-session'])el(id).disabled=false;}}
 async function load(){const response=await api('/v1/me/notes?offset='+offset);el('notes-list').replaceChildren();el('notes-next').hidden=response.items.length<100;for(const row of response.items){const article=add('article','',el('notes-list'));article.className='record';add('strong',row.pet,article);add('p',row.context||'상황 미입력',article);add('p','보호자 메모 · 보관 만료 '+new Date(row.expires*1000).toLocaleString('ko-KR'),article);const button=add('button','이 서버 메모 삭제',article);button.className='secondary';button.onclick=()=>action(async()=>{await api('/v1/me/notes/'+encodeURIComponent(row.id),'DELETE');await load();});}el('notes-status').textContent=`서버 메모 ${offset+1}번째부터 ${response.items.length}개 조회했습니다.`;}
 el('notes-load').onclick=()=>action(async()=>{offset=0;await load();});
 el('notes-next').onclick=()=>action(async()=>{offset+=100;await load();});
 el('notes-save').onclick=()=>action(async()=>{const pet=el('pet').value.trim(),context=el('context').value;if(!pet)throw new Error('반려견 이름을 입력하세요.');const body={pet,context},petId=globalThis.PetSenseProfiles?.selectedId();if(petId)body.pet_id=petId;await api('/v1/me/notes','POST',body);offset=0;await load();el('notes-status').textContent='이름·상황 메모를 서버에 보관했습니다. 분석 결과와 음성은 포함하지 않았습니다.';});
 el('notes-delete-account').onclick=()=>{if(!confirm('이 계정의 서버 프로필·메모와 발급된 세션을 모두 삭제할까요? 브라우저 관찰 기록은 따로 남습니다.'))return;return action(async()=>{await api('/v1/me/account','DELETE');el('notes-session').value='';globalThis.PetSenseProfiles?.reset();globalThis.PetSenseJobs?.reset();el('notes-list').replaceChildren();el('notes-next').hidden=true;el('notes-status').textContent='서버 프로필·메모와 세션을 삭제했습니다.';});};
 el('notes-session').oninput=()=>{offset=0;el('notes-list').replaceChildren();el('notes-next').hidden=true;el('notes-status').textContent='';};
})();
