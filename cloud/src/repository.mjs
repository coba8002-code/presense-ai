import {POLICY_VERSION} from './core.mjs';
export class Repository{
 constructor(client){this.client=client;}
 async run(query){const {data,error}=await query;if(error)throw new Error(this.message(error));return data;}
 message(error){
  if(error.code==='23503')return '본인 계정의 반려견을 먼저 등록하거나 선택하세요.';
  if(error.code==='42501'||error.status===401)return '로그인 세션을 확인하고 다시 로그인하세요.';
  if(error.message?.includes('quota'))return '테스트 운영의 기록·요청 한도에 도달했습니다.';
  return '저장 요청을 처리하지 못했습니다. 연결과 입력값을 확인해 주세요.';
 }
 async account(){return this.run(this.client.from('ps_accounts').select('id,created_at,terms_version,privacy_version').maybeSingle());}
 async accept(){return this.run(this.client.from('ps_accounts').insert({accept_terms:true,accept_privacy:true,terms_version:POLICY_VERSION,privacy_version:POLICY_VERSION}));}
 async load(){const [dogs,notes,requests,plans]=await Promise.all(['dogs','notes','requests','plans'].map(name=>this.run(this.client.from('ps_'+name).select('*').order('created_at',{ascending:false}).limit(500))));return {dogs,notes,requests,plans};}
 async insert(table,row){return this.run(this.client.from('ps_'+table).insert(row).select().single());}
 async remove(table,id){return this.run(this.client.from('ps_'+table).delete().eq('id',id));}
 async cancel(id){return this.run(this.client.from('ps_requests').update({status:'cancelled'}).eq('id',id));}
 async complete(id,value){return this.run(this.client.from('ps_plans').update({completed:value}).eq('id',id));}
 async eraseRecords(){for(const name of ['notes','requests','plans','dogs'])await this.run(this.client.from('ps_'+name).delete().neq('id','00000000-0000-0000-0000-000000000000'));}
}
