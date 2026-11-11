export function deleteAccountHandler({url,anonKey,serviceKey,origins,fetcher=fetch}){
 return async request=>{
  const origin=request.headers.get('Origin');
  const headers={'Content-Type':'application/json','Cache-Control':'no-store','Vary':'Origin'};
  const reply=(status,error)=>new Response(JSON.stringify(error?{error}:{deleted:true}),{status,headers});
  if(!origins.includes(origin))return reply(403,'Origin not allowed');
  headers['Access-Control-Allow-Origin']=origin;
  headers['Access-Control-Allow-Headers']='authorization, apikey, content-type, x-client-info, x-delete-confirm';
  headers['Access-Control-Allow-Methods']='POST, OPTIONS';
  if(request.method==='OPTIONS')return new Response(null,{status:204,headers});
  if(request.method!=='POST')return reply(405,'POST required');
  if(!url||!anonKey||!serviceKey)return reply(503,'Account deletion unavailable');
  const bearer=request.headers.get('Authorization')||'';
  if(!/^Bearer [^\s]+$/.test(bearer))return reply(401,'Authentication required');
  if(request.headers.get('X-Delete-Confirm')!=='delete-account')return reply(400,'Confirmation required');
  try{
   const reader=request.body?.getReader();
   if(!reader)return reply(400,'Confirmation required');
   const chunks=[];let bytes=0;
   try{while(true){const {done,value}=await reader.read();if(done)break;bytes+=value.byteLength;
    if(bytes>128){await reader.cancel();return reply(413,'Body too large');}chunks.push(value);
   }}finally{reader.releaseLock();}
   const buffer=new Uint8Array(bytes);let offset=0;
   for(const chunk of chunks){buffer.set(chunk,offset);offset+=chunk.byteLength;}
   let body;
   try{body=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(buffer));}
   catch{return reply(400,'Invalid request body');}
   if(body?.confirmation!=='delete-account')return reply(400,'Confirmation required');
   const authHeaders={apikey:anonKey,Authorization:bearer};
   const call=(path,options)=>fetcher(url+path,{...options,redirect:'error',signal:AbortSignal.timeout(10000)});
   const userResponse=await call('/auth/v1/user',{headers:authHeaders});
   if(!userResponse.ok)return reply(401,'Authentication required');
   const user=await userResponse.json();
   if(!/^[a-f0-9-]{36}$/i.test(user.id||''))return reply(401,'Authentication required');
   const active=await call('/rest/v1/rpc/ps_session_active',{method:'POST',headers:{...authHeaders,'Content-Type':'application/json'},body:'{}'});
   if(!active.ok||await active.json()!==true)return reply(401,'Session inactive');
   const signedOut=await call('/auth/v1/logout?scope=global',{method:'POST',headers:authHeaders});
   if(!signedOut.ok)return reply(502,'Session revocation failed; deletion not completed');
   const removed=await call('/auth/v1/admin/users/'+user.id,{method:'DELETE',headers:{apikey:serviceKey,Authorization:'Bearer '+serviceKey}});
   if(!removed.ok)return reply(502,'Deletion not completed; sign in to retry');
   return reply(200);
  }catch{return reply(502,'Deletion not completed');}
 };
}
