'use strict';
(()=>{
 const session=globalThis.PetSenseSession,$=id=>document.getElementById(id);
 let active=null,epoch=0;
 function clear(){epoch++;active?.abort();active=null;$('research-list').replaceChildren();$('research-status').textContent='';$('research-load').disabled=!session.identity();}
 function text(tag,value,parent){const node=document.createElement(tag);node.textContent=value;parent.append(node);return node;}
 $('research-load').onclick=async()=>{
  const who=session.identity(),version=++epoch;if(!who)return;
  active?.abort();const controller=new AbortController();active=controller;$('research-load').disabled=true;
  const current=()=>version===epoch&&who===session.identity();
  try{
   const r=await fetch('/v1/me/research-status',{credentials:'same-origin',headers:session.headers(),signal:controller.signal});
   if(!r.ok)throw new Error();const data=await r.json();if(!current())return;
   $('research-list').replaceChildren();
   const last=data.last_cycle;
   $('research-status').textContent=!data.configured?'자료 수집 DB 미연결':
    `${data.links.length}개 후보 · 마지막 수집 ${data.last_cycle_at?new Date(data.last_cycle_at*1000).toLocaleString():'미실행'} · 피드 오류 ${last?.feed_errors??0} · 링크 분석 ${last?.link_analysis?.status??'미실행'} (이번 실행 ${last?.link_analysis?.counts?.analyzed??0}건) · 로컬 학습 ${last?.local_training?.status??'미실행'}`;
   for(const row of data.links){
    if(!/^[A-Za-z0-9_-]{11}$/.test(row.video_id))continue;
    const box=text('article','',$('research-list'));text('h3',row.title,box);
    text('p',row.verification==='official_feed_metadata_only'?'공식 피드 메타데이터 · 내용·이용권 검증 전':'검색 색인 후보 · 공식 출처 재확인 필요',box);
    const stages={metadata_missing:'공식 영상 정보 확인 전',metadata_stale:'영상 정보 재확인 필요',policy_unavailable:'현재 이용 조건 미연결',permission_required:'이용 범위 확인 필요',awaiting_analysis:'영상 분석 대기',model_changed:'모델 변경 · 재분석 필요',analysis_stale:'분석 갱신 필요',evidence_invalid:'분석 근거 검증 실패',unsupported_species:'개 관찰 자료 아님',machine_extracted_unreviewed:'AI 관찰 추출됨 · 독립 검수 전'};
    text('p',(stages[row.analysis_status]||'분석 상태 확인 전')+' · 학습 사용 불가',box);
    const a=text('a','원본 YouTube 링크',box);a.href='https://www.youtube.com/watch?v='+row.video_id;a.target='_blank';a.rel='noopener noreferrer';
   }
  }catch(e){if(current()&&e.name!=='AbortError')$('research-status').textContent='로그인 및 수집 서비스 설정을 확인하세요.';}
  finally{if(active===controller){active=null;$('research-load').disabled=!session.identity();}}
 };
 window.addEventListener('petsense-session-change',clear);$('notes-session').addEventListener('input',clear);session.ready.then(clear);
})();
