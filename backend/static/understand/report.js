'use strict';
(()=>{
 const guide=PetSenseGuide,core=PetSenseReport,t=core.copy[guide.language],el=id=>document.getElementById(id),panel=el('consultation');
 let epoch=0,active=null;
 for(const node of panel.querySelectorAll('[data-report]'))node.textContent=t[node.dataset.report];
 function controls(){for(const node of panel.querySelectorAll('button,input,select'))node.disabled=Boolean(active)||!guide.identity()||!guide.selectedId();el('report-download').disabled=Boolean(active)||!guide.identity()||!guide.selectedId()||!el('report-consent').checked;}
 function reset(){epoch++;active?.abort();active=null;el('report-preview').replaceChildren();el('report-status').textContent='';el('report-consent').checked=false;controls();}
 function render(doc){const target=el('report-preview');target.replaceChildren();for(const section of doc.sections){const article=document.createElement('article');article.className='journal-entry';const heading=document.createElement('h3');heading.textContent=section.title;article.append(heading);for(const line of section.lines){const p=document.createElement('p');p.textContent=line;article.append(p);}target.append(article);}}
 async function run(download){
  if(active||!guide.identity()||!guide.selectedId()||(download&&!el('report-consent').checked))return;
  const mine=epoch,identity=guide.identity(),pet=guide.selectedId(),days=el('report-days').value,controller=new AbortController();active=controller;el('report-preview').replaceChildren();el('report-status').textContent='';controls();
  const current=()=>mine===epoch&&guide.identity()===identity&&guide.selectedId()===pet&&el('report-days').value===days;
  try{
   const data=await guide.api('/v1/me/journal/report?pet_id='+encodeURIComponent(pet)+'&days='+days,{signal:controller.signal});
   if(!current())return;
   const doc=core.document(data,guide.language,Intl.DateTimeFormat().resolvedOptions().timeZone);render(doc);
   if(download){const url=URL.createObjectURL(new Blob([core.html(doc,guide.language)],{type:'text/html;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download='petsense-consultation-'+guide.language+'.html';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);el('report-consent').checked=false;}
   el('report-status').textContent=t.ready;
  }catch(error){if(current())el('report-status').textContent=t.error;}finally{if(active===controller){active=null;controls();}}
 }
 el('report-load').onclick=()=>run(false);el('report-download').onclick=()=>run(true);
 el('report-days').onchange=reset;el('report-consent').onchange=controls;
 window.addEventListener('petsense-guide-change',reset);window.addEventListener('petsense-case-saved',reset);window.addEventListener('pagehide',reset);
 // A successful journal mutation invalidates any existing consultation snapshot.
 window.addEventListener('petsense-journal-mutated',reset);
 guide.ready.then(controls);controls();
})();
