import test from 'node:test';
import assert from 'node:assert/strict';
import {createClient} from '@supabase/supabase-js';
import {Repository} from '../src/repository.mjs';
function fixture(found){
 const calls=[];
 const client=createClient('https://synthetic.supabase.co','sb_publishable_test_fixture_only',{
  accessToken:async()=>'synthetic',global:{fetch:async(url,options)=>{
   const headers=new Headers(options.headers);calls.push({url:String(url),options});
   const representation=(headers.get('prefer')||'').includes('return=representation');
   const singular=headers.get('accept')==='application/vnd.pgrst.object+json';
   if(representation&&singular&&!found)return new Response(JSON.stringify({code:'PGRST116',message:'No rows'}),{status:406,headers:{'content-type':'application/json'}});
   return new Response(JSON.stringify(representation?(singular?{id:'record'}:[{id:'record'}]):null),{status:200,headers:{'content-type':'application/json'}});
  }}
 });return {repo:new Repository(client),calls};
}
test('single-row mutations reject an absent, expired or inaccessible record instead of reporting success',async()=>{for(const operation of [r=>r.remove('notes','record'),r=>r.cancel('record'),r=>r.complete('record',true)]){const f=fixture(false);await assert.rejects(operation(f.repo));}});
test('single-row mutations request and verify the affected record',async()=>{for(const operation of [r=>r.remove('notes','record'),r=>r.cancel('record'),r=>r.complete('record',true)]){const f=fixture(true);assert.deepEqual(await operation(f.repo),{id:'record'});assert.ok(f.calls[0].url.includes('select=id'));}});
