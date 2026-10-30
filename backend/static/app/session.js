'use strict';
(()=>{
 const el=id=>document.getElementById(id);let cfg=null,member=null,failed=false;
 const controls=['notes-session','notes-load','notes-save','notes-next','notes-delete-account','profile-load','profile-create','profile-update','profile-select','job-submit','jobs-refresh','submit'];
 const identity=()=>cfg?.enabled?member?.csrf_token||'':failed||cfg===null?'':el('notes-session').value;
 function render(){const on=Boolean(cfg?.enabled||failed);if(el('web-account'))el('web-account').hidden=!on;
  if(el('web-session-status'))el('web-session-status').textContent=failed?'계정 설정·HTTPS 연결을 확인하세요.':member?member.email+' · 로그인됨':'회원가입·로그인 후 계정 기록을 사용할 수 있습니다.';
  if(el('web-auth-link')){el('web-auth-link').href=member?'/auth#account':'/auth';el('web-auth-link').textContent=member?'계정 설정':'회원가입·로그인';}
  if(el('web-logout'))el('web-logout').hidden=!member;
  if(el('development-session'))el('development-session').hidden=on;
  if(el('development-analysis'))el('development-analysis').hidden=on;
  if(el('analysis-storage-notice')&&on&&cfg?.audio_jobs_enabled)el('analysis-storage-notice').textContent='로그인한 계정의 분석 작업을 사용합니다. 아래 분석 작업 영역에서 별도의 소리 임시 보관 동의를 확인하고 등록하세요.';
  if(el('notes-intro')&&on)el('notes-intro').textContent='로그인한 계정의 반려견 프로필과 상황 메모를 관리합니다. 프로필·메모는 별도 동의 후 30일 보관하며, 소리는 분석 작업 영역에서 별도로 등록합니다.';
  if(el('notes-delete-account')&&on)el('notes-delete-account').textContent='회원탈퇴·서버 자료 삭제';
  for(const id of controls)if(el(id))el(id).disabled=on&&!member;
  if(el('auth-mode')&&on){el('auth-mode').value='account';el('auth-mode').disabled=true;}
  if(el('submit')&&on&&cfg?.audio_jobs_enabled)el('submit').hidden=true;
  if(el('history'))el('history').hidden=on;
 }
 function notify(){window.dispatchEvent(new Event('petsense-session-change'));}
 function invalidate(){member=null;render();notify();}
 function headers(){return cfg?.enabled?member?{'X-PetSense-CSRF':member.csrf_token,'X-PetSense-Request':'web'}:{}:{'X-PetSense-Session':el('notes-session').value};}
 for(const id of controls)if(el(id))el(id).disabled=true;
 const ready=(async()=>{try{const response=await fetch('/v1/auth/config');if(!response.ok)throw new Error();cfg=await response.json();if(cfg.enabled){const session=await fetch('/v1/auth/session',{credentials:'same-origin'});if(session.ok)member=await session.json();else if(session.status!==401)throw new Error();el('notes-session').value='';}render();notify();}catch(error){failed=true;member=null;render();notify();}})();
 if(el('web-logout'))el('web-logout').onclick=async()=>{try{const response=await fetch('/v1/auth/logout',{method:'POST',headers:headers(),credentials:'same-origin'});if(!response.ok&&response.status!==401)throw new Error();invalidate();}catch(error){el('web-session-status').textContent='연결을 확인하고 로그아웃을 다시 시도하세요.';}};
 globalThis.PetSenseSession={ready,identity,headers,enabled:()=>Boolean(cfg?.enabled||failed||cfg===null),invalidate};
})();
