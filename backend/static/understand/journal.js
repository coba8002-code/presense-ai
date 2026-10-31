'use strict';
(()=>{
 const el=id=>document.getElementById(id),guide=PetSenseGuide,core=PetSenseJournal,t=core.copy[guide.language],c=PetSenseCase.copy[guide.language];
 let epoch=0,active=null,selected=null,next=null,pending=null;
 const buttons=['journal-load','journal-next','follow-save','journal-export','journal-delete'];
 const date=value=>new Date(typeof value==='number'?value*1000:value).toLocaleString(guide.language==='ko'?'ko-KR':'en',{timeZone:Intl.DateTimeFormat().resolvedOptions().timeZone});
 function text(tag,value,parent){const node=document.createElement(tag);node.textContent=value;parent.append(node);return node;}
 function say(value){el('journal-status').textContent=value;}
 function controls(){
  el('journal-window').disabled=Boolean(active)||!guide.identity()||!guide.selectedId();
  for(const id of buttons)el(id).disabled=Boolean(active)||!guide.identity()||!guide.selectedId();
  for(const id of ['journal-export','journal-delete','follow-save'])el(id).disabled=Boolean(active)||!selected;
  for(const field of el('followup-form').querySelectorAll('input,select,textarea,button'))field.disabled=Boolean(active)||!selected;
  el('journal-next').hidden=next===null;
 }
 function clearDetail(){selected=null;pending=null;el('journal-detail').hidden=true;el('journal-context').replaceChildren();el('followup-list').replaceChildren();el('followup-form').reset();}
 function reset(){epoch++;active?.abort();active=null;next=null;clearDetail();el('journal-summary').replaceChildren();el('journal-list').replaceChildren();say('');controls();}
 async function action(fn){
  if(active)return;if(!guide.identity()||!guide.selectedId()){say(t.needProfile);return;}
  const mine=epoch,identity=guide.identity(),profile=guide.selectedId(),controller=new AbortController();active=controller;controls();
  const current=()=>epoch===mine&&guide.identity()===identity&&guide.selectedId()===profile;
  async function api(path='',options={}){if(!current())throw new Error();const data=await guide.api('/v1/me/journal'+path,{...options,signal:controller.signal});if(!current())throw new Error();return data;}
  try{await fn(api,profile);}catch(error){if(current())say(t.error);}finally{if(active===controller){active=null;controls();}}
 }
 async function summary(api,profile){
  const container=el('journal-summary');container.replaceChildren();
  const report=await api('/summary?pet_id='+encodeURIComponent(profile)+'&days='+el('journal-window').value);
  text('p',date(report.start)+' — '+date(report.end),container);
  text('p',t.recordTotal+': '+report.case_count+' · '+t.missing+': '+report.cases_without_followup+' · '+t.followCount+': '+report.followup_count,container);
  for(const [behavior,count] of Object.entries(report.behavior_counts))text('p',(c[behavior]||behavior)+': '+count,container);
 }
 async function load(api,profile,offset=0){
  await summary(api,profile);
  const data=await api('?pet_id='+encodeURIComponent(profile)+'&offset='+offset);el('journal-list').replaceChildren();next=data.next_offset;
  for(const row of data.items){
   const article=text('article','',el('journal-list'));article.className='journal-entry';
   text('strong',row.pet_name+' · '+(c[row.data.behavior]||row.data.behavior),article);
   text('p',date(row.data.observed_at)+' · '+t.followCount+' '+row.followup_count,article);
   const button=text('button',t.detail,article);button.type='button';button.className='secondary';button.onclick=()=>action(api=>detail(api,row.id));
  }
  say(data.total?t.count+' '+data.total:t.empty);controls();
 }
 async function detail(api,id){
  clearDetail();controls();const row=await api('/'+encodeURIComponent(id));selected=row;
  const data=row.data;el('journal-detail').hidden=false;el('follow-time').value=core.localTime(new Date());
  const context=el('journal-context');text('h3',row.pet_name+' · '+(c[data.behavior]||data.behavior),context);
  text('p',date(data.observed_at)+' / '+t.expiry+' '+date(row.expires),context);
  for(const [key,label] of [['before',c.noteBefore],['during',c.noteDuring],['after',c.noteAfter]])text('p',label+': '+(data[key]||'—'),context);
  for(const [key,label] of [['duration',c.noteDuration],['change',c.noteChange],['dogs',c.noteDogs]])text('p',label+': '+c[data[key]],context);
  if(data.health_concern)text('p',c.healthAdvice,context);
  text('p',t.source,context);
  for(const follow of row.followups){const item=text('article','',el('followup-list'));item.className='journal-entry';text('strong',date(follow.data.observed_at)+' · '+t[follow.data.action],item);text('p',follow.data.what_done,item);text('p',t[follow.data.outcome],item);text('p',follow.data.note,item);}
  controls();
 }
 el('journal-window').onchange=()=>action((api,profile)=>summary(api,profile));
 el('journal-load').onclick=()=>action(async(api,profile)=>{clearDetail();await load(api,profile);});
 el('journal-next').onclick=()=>action(async(api,profile)=>{clearDetail();await load(api,profile,next??0);});
 el('followup-form').onsubmit=event=>{
  event.preventDefault();return action(async(api,profile)=>{
   if(!selected||!el('follow-consent').checked){say(t.needConsent);return;}
   const id=selected.id,data={observed_at:core.utcTime(el('follow-time').value),action:el('follow-action').value,what_done:el('follow-what').value,outcome:el('follow-outcome').value,note:el('follow-note').value};
   if(new Date(data.observed_at)<new Date(selected.data.observed_at)){say(t.tooEarly);return;}
   const body=JSON.stringify(data);if(!pending||pending.body!==body||pending.id!==id)pending={body,id,key:crypto.randomUUID()};
   await api('/'+encodeURIComponent(id)+'/followups',{method:'POST',headers:{'Content-Type':'application/json','X-Journal-Consent':'journal-storage-v1','Idempotency-Key':pending.key},body});
   await load(api,profile);await detail(api,id);say(t.added);
  });
 };
 el('journal-export').onclick=()=>{if(selected)guide.download({version:1,exported_at:new Date().toISOString(),display_timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,case:selected},'petsense-journal-case.json');};
 el('journal-delete').onclick=()=>{if(!selected||!confirm(t.confirmDelete))return;return action(async(api,profile)=>{await api('/'+encodeURIComponent(selected.id),{method:'DELETE',headers:{'X-Delete-Confirm':'delete-case'}});clearDetail();await load(api,profile);say(t.removed);});};
 window.addEventListener('petsense-guide-change',reset);
 window.addEventListener('petsense-case-saved',event=>action(async(api,profile)=>{await load(api,profile);await detail(api,event.detail.id);}));
 window.addEventListener('pagehide',reset);guide.ready.then(controls);controls();
 el('journal-timezone').textContent=t.timeZone+': '+Intl.DateTimeFormat().resolvedOptions().timeZone;
})();
