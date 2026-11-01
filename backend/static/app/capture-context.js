'use strict';
(()=>{
 const $=id=>document.getElementById(id),fields=['setting','dogs','speaker','noise','distance','visibility'];let revision=0;
 function changed(){revision++;window.dispatchEvent(new Event('petsense-capture-context-change'));}
 function reset(){for(const id of fields)$('capture-'+id).selectedIndex=0;$('capture-device').value='';$('capture-consent').checked=false;changed();}
 function capture(){
  if(!$('capture-consent').checked)return null;
  const result=Object.fromEntries(fields.map(k=>[k,$('capture-'+k).value]));result.device_id=$('capture-device').value.trim()||null;
  if(result.device_id&&!/^[A-Za-z0-9_-]{1,40}$/.test(result.device_id))throw new Error('기기 별명은 개인정보 없이 영문·숫자·_·-로 입력하세요.');
  return result;
 }
 function describe(snapshot){
  const d=snapshot.profile?.details,c=snapshot.context,lines=['보호자 입력 참고 · 미검증 · 모델 점수에 미반영 · 자동 학습 없음'];
  if(d)lines.push('견종: '+(d.breed_name||(d.breed_kind==='mixed'?'믹스':'모름'))+' · 입력 당시 '+(d.age_months===null?'나이 모름':d.age_months+'개월')+' / '+(d.weight_kg===null?'체중 모름':d.weight_kg+'kg'));
  const settings={unknown:'모름',alone:'혼자 있음',play:'놀이',walk:'산책',meal:'식사',rest:'휴식',unfamiliar_person:'낯선 사람 등장',unfamiliar_dog:'낯선 개 등장'};
  lines.push('보호자가 보고한 상황: '+(settings[c.setting]||'모름'));
  const limits={speaker_unconfirmed:'발성 개체 미확인 · 개체별 해석 보류',multiple_dogs_attribution_unverified:'여러 마리 환경 · 소리와 특정 개의 연결 미검증',visual_cues_unavailable_or_unverified:'영상의 몸 가시성 미확인 또는 부족 · 귀·꼬리 해석 보류',tail_cue_not_applicable_reported:'꼬리 없음으로 입력됨 · 꼬리 신호 해석 제외',individual_neutral_tail_reference_needed:'짧거나 말린 꼬리로 입력됨 · 평소 중립 모양의 비교 자료 필요',ear_base_visibility_check_needed:'처진 귀로 입력됨 · 귀 밑부분이 보이는지 확인 필요',coat_occlusion_check_needed:'긴 털로 입력됨 · 눈·귀·몸 가림 여부 확인 필요'};
  for(const reason of snapshot.interpretation_limits||[])if(limits[reason])lines.push(limits[reason]);
  return lines;
 }
 for(const id of [...fields,'consent'])$('capture-'+id).addEventListener('change',changed);
 $('capture-device').addEventListener('input',changed);
 for(const event of ['petsense-session-change','petsense-profile-change'])window.addEventListener(event,reset);
 globalThis.PetSenseCaptureContext={capture,version:()=>revision,describe,reset};
})();
