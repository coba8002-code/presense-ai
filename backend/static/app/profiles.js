'use strict';
(()=>{
 const el=id=>document.getElementById(id);
 const identity=()=>globalThis.PetSenseSession?.identity()??el('notes-session').value;
 const authHeaders=()=>globalThis.PetSenseSession?.headers()??{'X-PetSense-Session':el('notes-session').value};
 let pets=[],binding='',epoch=0,active=null;
 const detailIds=['breed-kind','breed-name','age','weight','ears','tail','muzzle','coat'];
 const controls=['profile-create','profile-update','profile-load','profile-select','profile-name',...detailIds.map(id=>'profile-'+id)];
 function fillDetails(d){d=d||{};for(const [id,key] of [['breed-kind','breed_kind'],['breed-name','breed_name'],['age','age_months'],['weight','weight_kg'],['ears','ears'],['tail','tail'],['muzzle','muzzle'],['coat','coat']])el('profile-'+id).value=d[key]??(['breed-name','age','weight'].includes(id)?'':'unknown');}
 function details(){
  const kind=el('profile-breed-kind').value,name=el('profile-breed-name').value.trim();
  if(kind==='unknown'&&name)throw new Error('견종 이름을 입력하려면 믹스 또는 알고 있는 견종을 선택하세요.');
  return {breed_kind:kind,breed_name:name||null,age_months:el('profile-age').value===''?null:Number(el('profile-age').value),weight_kg:el('profile-weight').value===''?null:Number(el('profile-weight').value),ears:el('profile-ears').value,tail:el('profile-tail').value,muzzle:el('profile-muzzle').value,coat:el('profile-coat').value};
 }
 function busy(value){for(const id of controls)el(id).disabled=value||Boolean(globalThis.PetSenseSession?.enabled()&&!identity());}
 function option(value,label){const node=document.createElement('option');node.value=value;node.textContent=label;el('profile-select').append(node);}
 function render(){
  const selected=el('profile-select').value;el('profile-select').replaceChildren();option('','프로필 미선택 · 이름만 사용');
  pets.forEach((pet,index)=>option(pet.id,pet.name+' · 등록 '+(index+1)));
  if(pets.some(p=>p.id===selected))el('profile-select').value=selected;
  el('profile-list').replaceChildren();
  for(const pet of pets){const row=document.createElement('article');row.className='record';const label=document.createElement('strong');label.textContent=pet.name;row.append(label);const expiry=document.createElement('p');expiry.textContent='보관 만료 '+new Date(pet.expires*1000).toLocaleDateString();row.append(expiry);const button=document.createElement('button');button.textContent='프로필·연결 메모 삭제';button.className='secondary';button.onclick=()=>{if(active||!confirm('이 프로필과 연결된 서버 메모·분석 작업·일지/후속 기록을 삭제할까요? 이름만 저장한 메모와 브라우저 기록은 남습니다.'))return;return action(async api=>{await api('/'+encodeURIComponent(pet.id),'DELETE');globalThis.PetSenseJobs?.reset();await load(api);el('profile-status').textContent='프로필과 연결 메모·분석 작업·일지/후속 기록을 삭제했습니다.';});};row.append(button);el('profile-list').append(row);}
  window.dispatchEvent(new Event('petsense-profile-change'));
 }
 function reset(){epoch++;if(active)active.abort();active=null;pets=[];binding='';busy(false);el('profile-select').value='';render();el('profile-name').value='';fillDetails(null);el('profile-status').textContent='';}
 async function action(fn){
  if(active)return;const session=identity();
  if(!session){el('profile-status').textContent='발급받은 계정 세션을 입력하세요.';return;}
  const mine=epoch,controller=new AbortController();active=controller;busy(true);
  const current=()=>mine===epoch&&session===identity();
  async function api(path='',method='GET',body){
   if(!current())throw new Error('세션이 변경되었습니다.');
   const response=await fetch('/v1/me/pets'+path,{method,signal:controller.signal,headers:{'Content-Type':'application/json',...authHeaders(),'X-Storage-Consent':String(el('notes-consent').checked),'X-Delete-Confirm':method==='DELETE'?'delete-pet':''},body:body?JSON.stringify(body):undefined});
   if(response.status===401)globalThis.PetSenseSession?.invalidate();
   if(!response.ok)throw new Error(({401:'세션이 만료되었거나 철회되었습니다.',403:'프로필·메모 보관 동의를 확인하세요.',404:'프로필을 찾을 수 없습니다.',409:'프로필은 계정당 20개까지 보관할 수 있습니다.',422:'이름·견종 선택·개월 수·체중 범위를 확인하세요.',503:'서버 계정 설정을 확인하세요.'})[response.status]||'프로필 요청에 실패했습니다.');
   const data=response.status===204?null:await response.json();if(!current())throw new Error('세션이 변경되었습니다.');return data;
  }
  try{await fn(api,session);}catch(error){if(current())el('profile-status').textContent=error.message;}
  finally{if(active===controller){active=null;busy(false);}}
 }
 async function load(api){const data=await api();pets=data.items;binding=identity();render();el('profile-status').textContent='반려견 프로필 '+pets.length+'개 · 기본30일, 일지 별도 동의에 따라 연장 가능';}
 el('profile-load').onclick=()=>action(load);
 el('profile-create').onclick=()=>action(async api=>{const pet=await api('','POST',{name:el('profile-name').value,details:details()});await load(api);el('profile-select').value=pet.id;el('profile-select').onchange();});
 el('profile-update').onclick=()=>action(async api=>{const id=globalThis.PetSenseProfiles.selectedId();if(!id)throw new Error('수정할 프로필을 선택하세요.');const pet=await api('/'+encodeURIComponent(id),'PATCH',{name:el('profile-name').value,details:details()});await load(api);el('profile-select').value=pet.id;el('profile-select').onchange();});
 el('profile-select').onchange=()=>{const pet=pets.find(p=>p.id===el('profile-select').value);if(pet){el('pet').value=pet.name;el('profile-name').value=pet.name;}fillDetails(pet?.details);window.dispatchEvent(new Event('petsense-profile-change'));};
 el('notes-session').addEventListener('input',reset);
 window.addEventListener('petsense-session-change',reset);
 el('pet').addEventListener('input',()=>{el('profile-select').value='';});
 globalThis.PetSenseProfiles={reset,selectedId:()=>binding===identity()&&pets.some(p=>p.id===el('profile-select').value)?el('profile-select').value:null};
 render();
})();
