'use strict';
(()=>{
 const el=id=>document.getElementById(id);
 let pets=[],binding='',epoch=0,active=null;
 const controls=['profile-create','profile-update','profile-load','profile-select','profile-name'];
 function busy(value){for(const id of controls)el(id).disabled=value;}
 function option(value,label){const node=document.createElement('option');node.value=value;node.textContent=label;el('profile-select').append(node);}
 function render(){
  const selected=el('profile-select').value;el('profile-select').replaceChildren();option('','프로필 미선택 · 이름만 사용');
  pets.forEach((pet,index)=>option(pet.id,pet.name+' · 등록 '+(index+1)));
  if(pets.some(p=>p.id===selected))el('profile-select').value=selected;
  el('profile-list').replaceChildren();
  for(const pet of pets){const row=document.createElement('article');row.className='record';const label=document.createElement('strong');label.textContent=pet.name;row.append(label);const button=document.createElement('button');button.textContent='프로필·연결 메모 삭제';button.className='secondary';button.onclick=()=>{if(active||!confirm('이 프로필과 연결된 서버 메모를 삭제할까요? 이름만 저장한 메모와 브라우저 기록은 남습니다.'))return;return action(async api=>{await api('/'+encodeURIComponent(pet.id),'DELETE');globalThis.PetSenseJobs?.reset();await load(api);el('profile-status').textContent='프로필과 연결 메모를 삭제했습니다.';});};row.append(button);el('profile-list').append(row);}
 }
 function reset(){epoch++;if(active)active.abort();active=null;pets=[];binding='';busy(false);el('profile-select').value='';render();el('profile-name').value='';el('profile-status').textContent='';}
 async function action(fn){
  if(active)return;const session=el('notes-session').value;
  if(!session){el('profile-status').textContent='발급받은 계정 세션을 입력하세요.';return;}
  const mine=epoch,controller=new AbortController();active=controller;busy(true);
  const current=()=>mine===epoch&&session===el('notes-session').value;
  async function api(path='',method='GET',body){
   if(!current())throw new Error('세션이 변경되었습니다.');
   const response=await fetch('/v1/me/pets'+path,{method,signal:controller.signal,headers:{'Content-Type':'application/json','X-PetSense-Session':session,'X-Storage-Consent':String(el('notes-consent').checked),'X-Delete-Confirm':method==='DELETE'?'delete-pet':''},body:body?JSON.stringify(body):undefined});
   if(!response.ok)throw new Error(({401:'세션이 만료되었거나 철회되었습니다.',403:'프로필·메모 보관 동의를 확인하세요.',404:'프로필을 찾을 수 없습니다.',409:'프로필은 계정당 20개까지 보관할 수 있습니다.',422:'이름은 공백 없이 1~40자로 입력하세요.',503:'서버 계정 설정을 확인하세요.'})[response.status]||'프로필 요청에 실패했습니다.');
   const data=response.status===204?null:await response.json();if(!current())throw new Error('세션이 변경되었습니다.');return data;
  }
  try{await fn(api,session);}catch(error){if(current())el('profile-status').textContent=error.message;}
  finally{if(active===controller){active=null;busy(false);}}
 }
 async function load(api){const data=await api();pets=data.items;binding=el('notes-session').value;render();el('profile-status').textContent='반려견 프로필 '+pets.length+'개 · 등록/이름 수정부터 30일 보관';}
 el('profile-load').onclick=()=>action(load);
 el('profile-create').onclick=()=>action(async api=>{const pet=await api('','POST',{name:el('profile-name').value});await load(api);el('profile-select').value=pet.id;el('profile-select').onchange();});
 el('profile-update').onclick=()=>action(async api=>{const id=globalThis.PetSenseProfiles.selectedId();if(!id)throw new Error('이름을 수정할 프로필을 선택하세요.');const pet=await api('/'+encodeURIComponent(id),'PATCH',{name:el('profile-name').value});await load(api);el('profile-select').value=pet.id;el('profile-select').onchange();});
 el('profile-select').onchange=()=>{const pet=pets.find(p=>p.id===el('profile-select').value);if(pet){el('pet').value=pet.name;el('profile-name').value=pet.name;}};
 el('notes-session').addEventListener('input',reset);
 el('pet').addEventListener('input',()=>{el('profile-select').value='';});
 globalThis.PetSenseProfiles={reset,selectedId:()=>binding===el('notes-session').value&&pets.some(p=>p.id===el('profile-select').value)?el('profile-select').value:null};
 render();
})();
