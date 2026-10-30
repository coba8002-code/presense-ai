'use strict';
(()=>{
 const el=id=>document.getElementById(id),parameters=new URLSearchParams(location.search);
 const language=['ko','en'].includes(parameters.get('lang'))?parameters.get('lang'):navigator.language.startsWith('ko')?'ko':'en';
 const t=PetSenseCase.copy[language];document.documentElement.lang=language;document.title='PetSense AI · '+t.title;
 for(const node of document.querySelectorAll('[data-i18n]'))node.textContent=t[node.dataset.i18n];
 for(const id of ['before','during','after'])el(id).placeholder=t.placeholder;
 el('language').value=language;el('language').onchange=()=>location.assign('/understand?lang='+el('language').value);
 let card=null,session=null,pets=[],busy=false;
 function say(value){el('guide-status').textContent=value;}
 function controls(){el('guide-profile').disabled=busy||!session;el('profiles-refresh').disabled=busy||!session;el('save-case').disabled=busy||!session||!card;}
 function invalidate(){session=null;pets=[];el('guide-profile').replaceChildren();controls();}
 function clearCard(){card=null;el('case-card').hidden=true;el('empty').hidden=false;el('case-note').textContent='';controls();say(t.changed);}
 for(const id of ['behavior','before','during','after','duration','change','dogs','health'])el(id).addEventListener('input',clearCard);
 el('case-form').onsubmit=event=>{event.preventDefault();try{const data={health:el('health').checked};for(const id of ['behavior','before','during','after','duration','change','dogs'])data[id]=el(id).value;card=PetSenseCase.report(data,language);el('case-note').textContent=card.note;el('health-advice').hidden=!card.health_concern;el('case-card').hidden=false;el('empty').hidden=true;say('');controls();}catch(error){clearCard();say(t.invalid);}};
 el('download').onclick=()=>{if(!card)return;const data={...card,created_at:new Date().toISOString(),display_timezone:Intl.DateTimeFormat().resolvedOptions().timeZone};const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='petsense-guardian-context.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
 async function load(){const response=await fetch('/v1/me/pets',{credentials:'same-origin'});if(!response.ok){if(response.status===401)invalidate();throw new Error();}pets=(await response.json()).items;el('guide-profile').replaceChildren();const choose=document.createElement('option');choose.value='';choose.textContent=t.choose;el('guide-profile').append(choose);for(const pet of pets){const option=document.createElement('option');option.value=pet.id;option.textContent=pet.name;el('guide-profile').append(option);}say(t.ready);}
 async function action(fn){if(busy)return;busy=true;controls();try{await fn();}catch(error){say(t.failed);}finally{busy=false;controls();}}
 el('profiles-refresh').onclick=()=>action(load);
 el('save-case').onclick=()=>action(async()=>{const pet=pets.find(p=>p.id===el('guide-profile').value);if(!card||!session||!pet||!el('storage-consent').checked){say(t.makeFirst);return;}const response=await fetch('/v1/me/notes',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-PetSense-CSRF':session.csrf_token,'X-PetSense-Request':'web','X-Storage-Consent':'true'},body:JSON.stringify({pet:pet.name,pet_id:pet.id,context:card.note})});if(!response.ok){if(response.status===401)invalidate();throw new Error();}say(t.saved);});
 (async()=>{try{const config=await fetch('/v1/auth/config');if(!config.ok||!(await config.json()).enabled){say(t.needLogin);return;}const response=await fetch('/v1/auth/session',{credentials:'same-origin'});if(!response.ok){say(t.needLogin);return;}session=await response.json();await load();}catch(error){invalidate();say(t.needLogin);}finally{controls();}})();
 window.addEventListener('pagehide',()=>{card=null;session=null;pets=[];});
})();
