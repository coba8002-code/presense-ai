'use strict';
(()=>{
 const guide=PetSenseGuide,el=id=>document.getElementById(id),ko=guide.language==='ko',panel=el('plans');
 const t=ko?{title:'이 상황의 돌봄·관찰 계획',intro:'관찰 목표와 예정 시각을 정하세요. 알림은 발송되지 않습니다. 완료는 후속 기록을 연결한 보호자의 확인이며 효과가 검증되었다는 뜻은 아닙니다.',goal:'다음에 무엇을 관찰할까요? · 최대200자',due:'예정 시각 · 내 기기 시간',consent:'목표·예정 시각·완료 상태를 최대30일, 이 상황의 만료일 이내로 보관하는 데 동의합니다.',create:'계획 보관',load:'계획 새로고침',empty:'보관된 계획이 없습니다.',choose:'완료 확인에 연결할 후속 기록 선택',planned:'예정',completed:'완료 · 보호자 확인',cancelled:'취소',overdue:'예정 시각 지남',complete:'후속 기록으로 완료 확인',cancel:'계획 취소',remove:'계획 삭제',completeConfirm:'선택한 후속 기록과 연결하여 이 계획을 완료했다고 확인할까요?',cancelConfirm:'이 계획을 취소할까요?',deleteConfirm:'이 계획을 삭제할까요? 상황과 후속 기록은 유지됩니다.',needFollow:'계획을 만든 뒤 후속 관찰을 저장하고, 상황을 다시 열어 연결하세요.',error:'처리하지 못했습니다. 기한·동의·후속 기록·로그인을 확인하세요. 저장 여부가 불명확하면 먼저 새로고침하세요.',expiry:'보관 만료',done:'계획을 반영했습니다.'}:{title:'Care and observation plans for this case',intro:'Choose an observation goal and time. No reminders are sent. Completion is a guardian confirmation linked to a followup, not evidence of efficacy.',goal:'What will you observe next? · up to 200 characters',due:'Planned time · my device time',consent:'I consent to storing this goal, time and status for up to 30 days, no later than this case’s expiry.',create:'Save plan',load:'Refresh plans',empty:'No saved plans.',choose:'Choose a followup to support completion',planned:'Planned',completed:'Completed · guardian confirmation',cancelled:'Cancelled',overdue:'Past planned time',complete:'Confirm completion with followup',cancel:'Cancel plan',remove:'Delete plan',completeConfirm:'Confirm you completed this plan and link the selected followup?',cancelConfirm:'Cancel this plan?',deleteConfirm:'Delete this plan? The case and followups will remain.',needFollow:'Save a followup after creating the plan, then reopen this case to connect it.',error:'Could not complete the request. Check date, consent, followup and login. If saving is uncertain, refresh first.',expiry:'Stored until',done:'Plan updated.'};
 for(const node of panel.querySelectorAll('[data-plan]'))node.textContent=t[node.dataset.plan];
 let row=null,epoch=0,active=null,pending=null;
 const text=(tag,value,parent)=>{const n=document.createElement(tag);n.textContent=value;parent.append(n);return n;};
 const date=n=>new Date(n*1000).toLocaleString(ko?'ko-KR':'en');
 function controls(){panel.hidden=!row;for(const n of panel.querySelectorAll('button,input,select,textarea'))n.disabled=Boolean(active)||!row||!guide.identity();}
 function reset(next=null){epoch++;active?.abort();active=null;row=next;pending=null;el('plan-form').reset();el('plan-list').replaceChildren();el('plan-status').textContent='';if(row)el('plan-due').value=PetSenseJournal.localTime(Date.now()+86400000);controls();}
 async function action(fn){
  if(active||!row||!guide.identity())return;const mine=epoch,identity=guide.identity(),id=row.id,controller=new AbortController();active=controller;controls();
  const current=()=>mine===epoch&&identity===guide.identity()&&row?.id===id;
  async function api(path='',options={}){const result=await guide.api('/v1/me/care-plans'+path,{...options,signal:controller.signal});if(!current())throw new Error();return result;}
  try{await fn(api,id);}catch(error){if(current())el('plan-status').textContent=t.error;}finally{if(active===controller){active=null;controls();}}
 }
 function button(label,parent,fn){const n=text('button',label,parent);n.type='button';n.className='secondary';n.onclick=fn;return n;}
 async function load(api,id){
  const data=await api('?case_id='+id),container=el('plan-list');container.replaceChildren();
  if(!data.items.length)text('p',t.empty,container);
  for(const plan of data.items){
   const article=text('article','',container);article.className='journal-entry';article.dataset.planId=plan.id;
   text('strong',plan.goal,article);text('p',t[plan.status]+' · '+date(plan.due)+(plan.status==='planned'&&plan.due*1000<Date.now()?' · '+t.overdue:''),article);text('p',t.expiry+': '+date(plan.expires),article);
   if(plan.status==='planned'){
    const label=text('label',t.choose,article),select=text('select','',label);select.setAttribute('aria-label',t.choose);
    const blank=text('option','—',select);blank.value='';
    for(const f of row.followups.filter(f=>f.created>=plan.created&&new Date(f.data.observed_at).getTime()<=Date.now())){const option=text('option',new Date(f.data.observed_at).toLocaleString(ko?'ko-KR':'en')+' · '+f.data.what_done,select);option.value=f.id;}
    text('p',t.needFollow,article);
    const change=(status,followup_id=null)=>action(async api=>{await api('/'+plan.id,{method:'PATCH',headers:{'Content-Type':'application/json','X-Journal-Consent':'care-plan-storage-v1'},body:JSON.stringify({status,followup_id})});await load(api,id);el('plan-status').textContent=t.done;});
    button(t.complete,article,()=>{if(select.value&&confirm(t.completeConfirm))change('completed',select.value);});
    button(t.cancel,article,()=>{if(confirm(t.cancelConfirm))change('cancelled');});
   }
   button(t.remove,article,()=>{if(confirm(t.deleteConfirm))action(async api=>{await api('/'+plan.id,{method:'DELETE',headers:{'X-Delete-Confirm':'delete-plan'}});await load(api,id);});});
  }
 }
 el('plan-load').onclick=()=>action(load);
 el('plan-form').onsubmit=event=>{event.preventDefault();action(async(api,id)=>{
  if(!el('plan-consent').checked)throw new Error();const body=JSON.stringify({case_id:id,goal:el('plan-goal').value,due_at:PetSenseJournal.utcTime(el('plan-due').value)});
  if(!pending||pending.body!==body)pending={body,key:crypto.randomUUID()};
  await api('',{method:'POST',headers:{'Content-Type':'application/json','X-Journal-Consent':'care-plan-storage-v1','Idempotency-Key':pending.key},body});el('plan-consent').checked=false;await load(api,id);el('plan-status').textContent=t.done;
 });};
 for(const id of ['plan-goal','plan-due'])el(id).addEventListener('input',()=>{el('plan-consent').checked=false;});
 window.addEventListener('petsense-journal-selected',event=>{reset(event.detail);if(row)action(load);});
 window.addEventListener('petsense-guide-change',()=>reset());window.addEventListener('pagehide',()=>reset());controls();
})();
