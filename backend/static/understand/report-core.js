'use strict';
(()=>{
 const node=typeof module!=='undefined'&&module.exports;
 const Case=node?require('./case.js'):globalThis.PetSenseCase,Journal=node?require('./journal-core.js'):globalThis.PetSenseJournal;
 const copy={
 ko:{title:'상담 준비 리포트',intro:'보호자가 남긴 관찰과 후속 기록을 정리합니다. 전문가 검수·진단·개의 의도 해석이나 교정 효과 평가가 아닙니다.',period:'포함할 기간',days7:'최근 7일',days30:'최근 30일',days90:'최근 90일',preview:'리포트 미리보기',download:'인쇄용 HTML 내려받기',consent:'선택한 개의 기록을 내 기기에 저장하는 데 동의합니다. 파일을 다른 사람에게 전달할지는 직접 결정하며, 서버에서 삭제해도 내려받은 사본은 남습니다.',created:'리포트 생성 시각',zone:'표시 시간대',window:'관찰 기간',included:'포함한 상황',total:'기간 내 전체 상황',truncated:'최근 100개 상황만 포함했습니다. 빠진 기록이 있으므로 기간을 줄여 다시 확인하세요.',empty:'선택 기간에 보관된 상황 기록이 없습니다.',gaps:'포함 기록에서 아직 확인하지 못한 항목',none:'해당 없음',noContext:'기록하지 않음',followup:'후속 관찰 없음',healthMarked:'보호자가 건강 우려를 표시했습니다. 상담 시 이 우려를 전달하세요.',healthNotMarked:'건강 우려를 표시하지 않았습니다. 건강 상태가 확인되었다는 뜻은 아닙니다.',questions:'상담 전에 준비할 질문',question1:'어떤 상황에서 무엇이 먼저 일어났고, 개는 무엇을 했나요?',question2:'평소와 달라진 점, 관찰 기간, 반복되는 환경을 구분해서 설명할 수 있나요?',question3:'내가 한 행동과 이후 모습을 어떻게 기록했나요? 원인이나 효과로 단정한 부분은 없나요?',checklist:'다음 관찰 체크리스트',check1:'안전한 거리에서 자연스럽게 나타나는 모습을 관찰하고 전·중·후 상황을 기록하세요. 행동을 일부러 유발하지 마세요.',check2:'아직 모르는 항목은 모름으로 남기고, 다음 관찰 시각과 담당자를 정하세요.',check3:'관찰 후 일지에 후속 기록을 남기세요. 이 체크리스트 자체는 일정이나 완료 상태를 저장하지 않습니다.',check4:'갑작스러운 변화나 통증·건강 우려가 있으면 수의사에게 문의하세요. 응급 징후가 있으면 기록보다 진료를 우선하세요.',error:'리포트를 만들지 못했습니다. 로그인·선택한 개·연결을 확인하세요.',ready:'리포트를 확인한 뒤 필요한 경우 기기에 저장하세요.',case:'상황'},
 en:{title:'Consultation preparation report',intro:'A summary of guardian observations and followups. Not expert-reviewed, a diagnosis, an interpretation of intent, or evidence of training efficacy.',period:'Include records from',days7:'Last 7 days',days30:'Last 30 days',days90:'Last 90 days',preview:'Preview report',download:'Download printable HTML',consent:'I consent to saving this dog’s records on my device. I choose whether to send the file to anyone. Deleting server records does not remove downloaded copies.',created:'Report generated',zone:'Display time zone',window:'Observation window',included:'Included cases',total:'All cases in this window',truncated:'Only the latest 100 cases are included. Some records are omitted; choose a shorter window to review them.',empty:'No saved cases in this window.',gaps:'Items not yet recorded in the included cases',none:'None',noContext:'Not recorded',followup:'No followup observation',healthMarked:'The guardian marked a health concern. Bring this concern to the consultation.',healthNotMarked:'No health concern was marked. This does not mean health was assessed.',questions:'Questions to prepare for consultation',question1:'What happened first, in what setting, and what did the dog do?',question2:'Can you distinguish changes from usual behavior, the observation period, and recurring settings?',question3:'How did you record your actions and what happened afterwards? Have you assumed a cause or an effect?',checklist:'Next observation checklist',check1:'Observe naturally occurring behavior from a safe distance and record before, during and after. Do not provoke the behavior.',check2:'Keep unknown details marked unknown. Choose a time and a caregiver for the next observation.',check3:'Add a followup to the journal after observing. This checklist does not save a schedule or completion state.',check4:'Contact a veterinarian for sudden changes, pain or health concerns. For emergency signs, prioritize care over recording.',error:'Could not create the report. Check login, selected dog and connection.',ready:'Review the report before saving it to your device.',case:'Case'}
 };
 function document(report,language,timeZone){
  if(!copy[language])throw new Error('Unsupported language');
  const t=copy[language],c=Case.copy[language],j=Journal.copy[language];
  const date=value=>new Date(typeof value==='number'?value*1000:value).toLocaleString(language==='ko'?'ko-KR':'en',{timeZone});
  const sections=[{title:report.pet.name,lines:[t.intro,t.created+': '+date(report.generated_at),t.zone+': '+timeZone,t.window+': '+date(report.start)+' — '+date(report.end),t.included+': '+report.included+' / '+t.total+': '+report.total]}];
  if(report.truncated)sections[0].lines.push(t.truncated);
  if(!report.cases.length)sections[0].lines.push(t.empty);
  const labels={before:c.noteBefore,during:c.noteDuring,after:c.noteAfter,duration:c.noteDuration,change:c.noteChange,dogs:c.noteDogs,followup:t.followup};
  const gaps=Object.entries(report.missing).filter(([,n])=>n>0).map(([key,n])=>labels[key]+': '+n);
  sections.push({title:t.gaps,lines:gaps.length?gaps:[t.none]});
  for(const [i,row] of report.cases.entries()){
   const d=row.data,lines=[date(d.observed_at)];
   for(const key of ['before','during','after'])lines.push(labels[key]+': '+(d[key].trim()||t.noContext));
   for(const key of ['duration','change','dogs'])lines.push(labels[key]+': '+c[d[key]]);
   lines.push(d.health_concern?t.healthMarked:t.healthNotMarked);
   if(!row.followups.length)lines.push(t.followup);
   for(const f of row.followups)lines.push(j.followups+' · '+date(f.data.observed_at)+' · '+j[f.data.action]+': '+f.data.what_done+' · '+j[f.data.outcome]+(f.data.note?' · '+f.data.note:''));
   sections.push({title:t.case+' '+(i+1)+' · '+c[d.behavior],lines});
  }
  sections.push({title:t.questions,lines:[t.question1,t.question2,t.question3]},{title:t.checklist,lines:[t.check1,t.check2,t.check3,t.check4]});
  return {title:t.title,sections};
 }
 const escape=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
 function html(doc,language){
  if(!copy[language])throw new Error('Unsupported language');
  return '<!doctype html><html lang="'+language+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; connect-src \'none\'; base-uri \'none\'; form-action \'none\'"><title>'+escape(doc.title)+'</title><style>body{max-width:850px;margin:40px auto;padding:0 24px;font:16px/1.7 system-ui;color:#173436;background:#f5faf8}header{border-bottom:4px solid #187568}h1{font-size:30px}h2{font-size:20px;color:#125b52}section{background:white;border:1px solid #cbded7;border-radius:12px;padding:20px;margin:20px 0;break-inside:avoid}p{white-space:pre-wrap;overflow-wrap:anywhere}@media print{body{margin:0;background:white}section{border-radius:0}h2{break-after:avoid}}</style></head><body><header><p>PetSense AI</p><h1>'+escape(doc.title)+'</h1></header>'+doc.sections.map(s=>'<section><h2>'+escape(s.title)+'</h2>'+s.lines.map(line=>'<p>'+escape(line)+'</p>').join('')+'</section>').join('')+'</body></html>';
 }
 const api={copy,document,html};if(node)module.exports=api;else globalThis.PetSenseReport=api;
})();
