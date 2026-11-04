import test from 'node:test';import assert from 'node:assert/strict';
import {validatePublicConfig,dogInput,requestInput,exportRecords} from '../src/core.mjs';
const jwt=role=>`header.${btoa(JSON.stringify({role})).replace(/=/g,'')}.signature`;
test('only public keys on explicit hosted HTTPS project URLs can enter client configuration',()=>{
 assert.equal(validatePublicConfig('https://example.supabase.co',jwt('anon')),true);
 for(const [u,k] of [['https://example.supabase.co',jwt('service_role')],['http://example.supabase.co',jwt('anon')],['https://example.supabase.co.evil.test',jwt('anon')],['https://user:password@example.supabase.co',jwt('anon')],['https://example.supabase.co?next=evil',jwt('anon')]])assert.equal(validatePublicConfig(u,k),false);
});
test('consent and bounds apply while ownership and output fields cannot be injected',()=>{
 assert.deepEqual(dogInput({name:' 보리 ',breed:'',age_months:'12',owner:'foreign',species:'cat'}),{name:'보리',species:'dog',breed:null,age_months:12});
 assert.throws(()=>dogInput({name:'x',age_months:900}));assert.throws(()=>requestInput({context:'test',consent:false}));
 const row=requestInput({id:'id',pet_id:'pet',context:'산책 준비',consent:true,status:'succeeded',result:'fake'});assert.equal('status' in row,false);assert.equal('result' in row,false);
});
test('exports exclude tokens and authentication payloads',()=>{
 const out=exportRecords({dogs:[],notes:[],requests:[],plans:[],session:{access_token:'secret'}});assert.equal(out.includes('secret'),false);assert.equal(out.includes('session'),false);
});
