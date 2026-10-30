'use strict';
(()=>{
 const el=id=>document.getElementById(id),state={pet:'보리',context:'',audio:false,records:[],saved:false};
 const copy={signup:['01','가입의 첫 순간','필수 동의와 개인정보 안내를 분리합니다. 이 화면은 계정 생성 전 제품 동선을 검토하기 위한 디자인입니다.','회원가입 · 실제 회원가입은 연결되지 않았습니다.'],profile:['02','이름이 아닌 고유한 프로필','같은 이름의 개도 서로 다른 프로필로 관리합니다. 현재 개발 범위에 맞춰 이름부터 등록하고 추가 정보는 수집하지 않습니다.','반려견 등록 · 이름과 별도 보관 동의'],home:['03','기록을 쌓는 홈','한 번의 점수보다 보호자가 남긴 상황과 관찰 기록을 모읍니다. 기록 수를 실제 짖음 빈도로 표시하지 않습니다.','홈 · 이 시안의 메모리 기록'],request:['04','선택한 구간만 전송','녹음·파일에서 최대 10초를 선택하고 당시 상황을 남깁니다. 분석과 작업용 임시 보관 동의를 나눕니다.','분석 요청 · 실제 마이크·파일·서버 전송 없음'],processing:['05','접수와 계산을 분리','작업을 접수한 뒤 상태를 조회하고 취소할 수 있습니다. 확정되지 않은 처리 시간이나 가짜 진행률을 표시하지 않습니다.','처리 상태 · 예시 결과 확인으로 다음 화면 이동'],result:['06','관찰과 해석의 경계','소리 사건 점수는 감정의 확률이 아닙니다. 불확실한 원인과 감정 판단을 보류하고 상황 기록과 함께 보관합니다.','결과 · 표시된 점수는 시연용 예시']};
 function show(name){if(!copy[name])return;for(const screen of document.querySelectorAll('.screen'))screen.hidden=screen.id!=='screen-'+name;for(const button of document.querySelectorAll('.steps button')){if(button.dataset.screen===name)button.setAttribute('aria-current','step');else button.removeAttribute('aria-current');}el('detail-number').textContent=copy[name][0];el('detail-title').textContent=copy[name][1];el('detail-copy').textContent=copy[name][2];el('design-live').textContent=copy[name][0]+' / '+copy[name][3];location.hash=name;}
 for(const button of document.querySelectorAll('[data-screen]'))button.addEventListener('click',()=>show(button.dataset.screen));
 function signup(){el('design-signup').disabled=!(el('design-terms').checked&&el('design-privacy').checked);}
 for(const id of ['design-terms','design-privacy'])el(id).addEventListener('change',signup);
 el('design-signup').onclick=()=>show('profile');
 function profile(){el('design-register').disabled=!(el('design-pet-name').value.trim()&&el('design-profile-consent').checked);}
 el('design-pet-name').addEventListener('input',profile);el('design-profile-consent').addEventListener('change',profile);
 el('design-register').onclick=()=>{state.pet=el('design-pet-name').value.trim().slice(0,40);for(const node of document.querySelectorAll('[data-pet-name]'))node.textContent=state.pet;show('home');};
 function request(){el('design-request').disabled=!(state.audio&&el('design-analysis-consent').checked&&el('design-storage-consent').checked);}
 for(const id of ['design-record','design-file'])el(id).onclick=()=>{state.audio=true;for(const button of document.querySelectorAll('.segments button'))button.classList.toggle('selected',button.id===id);document.querySelector('.wave').classList.add('ready');el('design-audio-status').textContent='예시 소리 선택 · 7초 / 최대 10초';request();};
 for(const id of ['design-analysis-consent','design-storage-consent'])el(id).addEventListener('change',request);
 el('design-request').onclick=()=>{state.context=el('design-context').value;state.saved=false;el('design-save').disabled=false;el('design-save').textContent='시안에 관찰 기록 남기기 ＋';el('design-result-context').textContent=state.context||'상황 메모 없음';show('processing');};
 el('design-show-result').onclick=()=>show('result');el('design-cancel').onclick=()=>{show('request');el('design-live').textContent='요청 취소 시연 · 실제 서버 작업은 없습니다.';};
 el('design-save').onclick=()=>{if(state.saved)return;state.saved=true;state.records.push({pet:state.pet,context:state.context});el('design-save').disabled=true;el('design-save').textContent='시안 메모리에 기록했습니다';el('design-count').textContent=String(state.records.length);el('design-records').replaceChildren();for(const row of state.records.slice().reverse()){const card=document.createElement('article');card.className='design-record';const title=document.createElement('strong');title.textContent=row.pet+' · 소리 관찰';const note=document.createElement('p');note.textContent=row.context||'상황 메모 없음';const tag=document.createElement('p');tag.textContent='시연용 예시 · 감정·원인 판단 보류';card.append(title,note,tag);el('design-records').append(card);}};
 window.addEventListener('hashchange',()=>show(location.hash.slice(1)||'signup'));
 show(location.hash.slice(1)||'signup');signup();profile();request();
})();
