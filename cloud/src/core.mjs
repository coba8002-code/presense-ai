export const POLICY_VERSION='2026-11-04';
export function validatePublicConfig(url,key){
 try{
  const u=new URL(url);
  if(u.protocol!=='https:'||!u.hostname.endsWith('.supabase.co')||u.pathname!=='/'||u.search||u.hash||u.username||u.password)return false;
  if(key.startsWith('sb_publishable_')&&key.length>25)return true;
  const parts=key.split('.');if(parts.length!==3)return false;
  const payload=JSON.parse(atob(parts[1].replace(/-/g,'+').replace(/_/g,'/')));
  return payload.role==='anon';
 }catch{return false;}
}
export function text(value,max,required=true){
 const result=String(value??'').trim();
 if((required&&!result)||result.length>max)throw new Error(`입력 길이를 확인하세요. 최대 ${max}자입니다.`);
 return result;
}
export function dogInput(data){
 const name=text(data.name,40);const breed=text(data.breed,80,false);const age=data.age_months===''||data.age_months==null?null:Number(data.age_months);
 if(age!==null&&(!Number.isInteger(age)||age<0||age>360))throw new Error('나이는 0~360개월로 입력하세요.');
 return {name,species:'dog',breed:breed||null,age_months:age};
}
export function consent(value){if(value!==true)throw new Error('기록 보관 동의가 필요합니다.');}
export function requestInput(data){consent(data.consent);return {id:data.id,pet_id:data.pet_id,context:text(data.context,2000),consent_version:POLICY_VERSION};}
export function displayStatus(status){return status==='cancelled'?'취소됨':'모델 연결 대기';}
export function exportRecords(data){return JSON.stringify({format:'petsense-cloud-export-v1',exported_at:new Date().toISOString(),dogs:data.dogs,notes:data.notes,requests:data.requests,plans:data.plans,notice:'보호자 기록입니다. 모델 판단이나 전문가 정답이 아닙니다.'},null,2);}
