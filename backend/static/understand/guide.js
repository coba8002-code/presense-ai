'use strict';
(()=>{
 const el=id=>document.getElementById(id),parameters=new URLSearchParams(location.search);
 const language=['ko','en'].includes(parameters.get('lang'))?parameters.get('lang'):navigator.language.startsWith('ko')?'ko':'en';
 const t=PetSenseCase.copy[language],j=PetSenseJournal.copy[language];
 document.documentElement.lang=language;document.title='PetSense AI · '+t.title;
 for(const node of document.querySelectorAll('[data-i18n]'))node.textContent=t[node.dataset.i18n];
 for(const node of document.querySelectorAll('[data-journal]'))node.textContent=j[node.dataset.journal];
 for(const id of ['before','during','after'])el(id).placeholder=t.placeholder;
 el('language').value=language;el('language').onchange=()=>location.assign('/understand?lang='+el('language').value);
 el('observed-time').value=PetSenseJournal.localTime(new Date());
 let card=null,session=null,pets=[],busy=false,pending=null;
 const identity=()=>session?.csrf_token||'';
 const selectedId=()=>pets.some(p=>p.id===el('guide-profile').value)?el('guide-profile').value:'';
 function say(value){el('guide-status').textContent=value;}
 function controls(){
  el('guide-profile').disabled=busy||!session;el('profiles-refresh').disabled=busy||!session;el('save-case').disabled=busy||!session||!card;
  for(const field of document.querySelectorAll('#case-form input,#case-form select,#case-form textarea,#case-form button,#retention-days,#storage-consent'))field.disabled=busy;
 }
 function notify(){window.dispatchEvent(new Event('petsense-guide-change'));}
 function clearCard(){card=null;el('case-card').hidden=true;el('empty').hidden=false;el('case-note').textContent='';controls();}
 function invalidate(){
  session=null;pets=[];pending=null;el('guide-profile').replaceChildren();
  for(const id of ['before','during','after'])el(id).value='';
  clearCard();el('storage-consent').checked=false;notify();
 }
 async function api(path,options={}){
  const mine=identity();if(!mine)throw new Error(j.needProfile);
  const response=await fetch(path,{...options,credentials:'same-origin',headers:{'X-PetSense-CSRF':mine,'X-PetSense-Request':'web',...options.headers}});
  if(identity()!==mine)throw new Error(j.error);
  if(response.status===401||response.status===403){invalidate();throw new Error(j.needProfile);}
  if(!response.ok)throw new Error(j.error);
  const value=response.status===204?null:await response.json();if(identity()!==mine)throw new Error(j.error);return value;
 }
 for(const id of ['behavior','before','during','after','duration','change','dogs','health','observed-time'])el(id).addEventListener('input',()=>{clearCard();say(t.changed);});
 el('retention-days').onchange=()=>{el('storage-consent').checked=false;};
 el('guide-profile').onchange=()=>{el('storage-consent').checked=false;pending=null;notify();};
 el('case-form').onsubmit=event=>{
  event.preventDefault();try{
   PetSenseJournal.utcTime(el('observed-time').value);
   const data={health:el('health').checked};for(const id of ['behavior','before','during','after','duration','change','dogs'])data[id]=el(id).value;
   card=PetSenseCase.report(data,language);el('case-note').textContent=card.note;el('health-advice').hidden=!card.health_concern;
   el('case-card').hidden=false;el('empty').hidden=true;say('');controls();
  }catch(error){clearCard();say(t.invalid);}
 };
 function download(value,filename){const blob=new Blob([JSON.stringify(value,null,2)],{type:'application/json;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 el('download').onclick=()=>{if(card)download({...card,created_at:new Date().toISOString(),display_timezone:Intl.DateTimeFormat().resolvedOptions().timeZone},'petsense-guardian-context.json');};
 async function load(){
  const response=await api('/v1/me/pets');pets=response.items;el('guide-profile').replaceChildren();
  const choose=document.createElement('option');choose.value='';choose.textContent=t.choose;el('guide-profile').append(choose);
  for(const pet of pets){const option=document.createElement('option');option.value=pet.id;option.textContent=pet.name;el('guide-profile').append(option);}
  el('storage-consent').checked=false;pending=null;notify();say(t.ready);
 }
 async function action(fn){if(busy)return;busy=true;controls();try{await fn();}catch(error){say(j.error);}finally{busy=false;controls();}}
 el('profiles-refresh').onclick=()=>action(load);
 el('save-case').textContent=j.save;
 el('save-case').onclick=()=>action(async()=>{
  if(!card||!selectedId()||!el('storage-consent').checked){say(j.needConsent);return;}
  const profile=selectedId(),mine=identity(),data=PetSenseJournal.caseBody(card,profile,el('observed-time').value,Number(el('retention-days').value)),body=JSON.stringify(data);
  if(!pending||pending.body!==body||pending.identity!==mine)pending={body,key:crypto.randomUUID(),identity:mine};
  const result=await api('/v1/me/journal',{method:'POST',headers:{'Content-Type':'application/json','X-Journal-Consent':'journal-storage-v1','Idempotency-Key':pending.key},body});
  if(identity()!==mine||selectedId()!==profile)return;
  say(j.saved);window.dispatchEvent(new CustomEvent('petsense-case-saved',{detail:{id:result.id}}));
 });
 const ready=(async()=>{
  try{
   const config=await fetch('/v1/auth/config');if(!config.ok||!(await config.json()).enabled){say(t.needLogin);return;}
   const response=await fetch('/v1/auth/session',{credentials:'same-origin'});if(!response.ok){say(t.needLogin);return;}
   session=await response.json();await load();
  }catch(error){invalidate();say(t.needLogin);}finally{controls();}
 })();
 globalThis.PetSenseGuide={ready,identity,selectedId,api,invalidate,language,download};
 window.addEventListener('pagehide',invalidate);
 window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
})();
