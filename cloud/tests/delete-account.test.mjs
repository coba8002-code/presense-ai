import test from 'node:test';
import assert from 'node:assert/strict';
import {deleteAccountHandler} from '../../supabase/functions/petsense-delete-account/handler.mjs';
const origin='https://beta.example.test',id='10000000-0000-4000-8000-000000000001';
function fixture(responses){const calls=[];return {calls,handler:deleteAccountHandler({url:'https://test.supabase.co',anonKey:'public-test',serviceKey:'server-test',origins:[origin],fetcher:async(url,options)=>{calls.push({url,options});return responses.shift();}})};}
function request(extra={}){return new Request('https://test.supabase.co/functions/v1/petsense-delete-account',{method:'POST',headers:{Origin:origin,Authorization:'Bearer synthetic-session','X-Delete-Confirm':'delete-account'},body:JSON.stringify({confirmation:'delete-account',id:'attacker-supplied-id'}),...extra});}
const response=(data,status=200)=>new Response(JSON.stringify(data),{status});
test('deletion verifies live session, revokes it then deletes only the authenticated user',async()=>{const {handler,calls}=fixture([response({id}),response(true),response({}),response({})]);const result=await handler(request());assert.equal(result.status,200);assert.equal(calls.length,4);assert.equal(calls[2].url.endsWith('logout?scope=global'),true);assert.equal(calls[3].url.endsWith('/users/'+id),true);assert.equal(calls[0].options.headers.apikey,'public-test');assert.equal(calls[3].options.headers.apikey,'server-test');assert.equal((await result.text()).includes('server-test'),false);});
test('untrusted origins and unconfirmed/revoked sessions cannot invoke admin deletion',async()=>{const f=fixture([]);assert.equal((await f.handler(request({headers:{Origin:'https://attacker.test'}}))).status,403);assert.equal(f.calls.length,0);const r=fixture([response({id}),response(false)]);assert.equal((await r.handler(request())).status,401);assert.equal(r.calls.length,2);});
test('failed global revocation stops deletion and failed deletion never returns success',async()=>{for(const results of [[response({id}),response(true),response({},500)],[response({id}),response(true),response({}),response({},500)]]){const f=fixture(results);assert.equal((await f.handler(request())).status,502);assert.ok(f.calls.length>=3);}});
test('oversized streamed bodies are cancelled before any authentication or admin call',async()=>{
 let cancelled=false;
 const body=new ReadableStream({start(controller){controller.enqueue(new Uint8Array(129));},cancel(){cancelled=true;}});
 const f=fixture([]);
 const response=await f.handler(request({body,duplex:'half'}));
 assert.equal(response.status,413);assert.equal(cancelled,true);assert.equal(f.calls.length,0);
});
test('malformed JSON is a client error and never reaches Auth',async()=>{
 const f=fixture([]);assert.equal((await f.handler(request({body:'{invalid'}))).status,400);assert.equal(f.calls.length,0);
});
