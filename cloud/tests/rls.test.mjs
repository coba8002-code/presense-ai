import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {PGlite} from '@electric-sql/pglite';
const sql=await readFile(new URL('../../supabase/migrations/20261104030815_petsense_cloud_beta.sql',import.meta.url),'utf8');
const A='10000000-0000-4000-8000-000000000001',B='10000000-0000-4000-8000-000000000002',SA='20000000-0000-4000-8000-000000000001',SB='20000000-0000-4000-8000-000000000002';
async function setup(){const db=new PGlite();await db.exec(`create role anon;create role authenticated;create schema auth;
create table auth.users(id uuid primary key);create table auth.sessions(id uuid primary key,user_id uuid references auth.users(id) on delete cascade,not_after timestamptz);
create function auth.jwt() returns jsonb language sql stable as $$ select coalesce(nullif(current_setting('request.jwt.claims',true),''),'{}')::jsonb $$;
create function auth.uid() returns uuid language sql stable as $$ select nullif(auth.jwt()->>'sub','')::uuid $$;
grant usage on schema auth to authenticated,anon;grant execute on all functions in schema auth to authenticated,anon;
insert into auth.users values('${A}'),('${B}');insert into auth.sessions values('${SA}','${A}',null),('${SB}','${B}',null);`);await db.exec(sql);return db;}
async function asUser(db,owner=A,session=SA,anonymous=false){await db.exec('reset role');await db.query(`select set_config('request.jwt.claims',$1,false)`,[JSON.stringify({sub:owner,session_id:session,is_anonymous:anonymous})]);await db.exec('set role authenticated');}
async function account(db){await db.exec(`insert into public.ps_accounts(accept_terms,accept_privacy,terms_version,privacy_version) values(true,true,'2026-11-04','2026-11-04')`);}
test('two real Postgres roles isolate rows, references, owner changes and fabricated model status',async()=>{const db=await setup();try{
await asUser(db);await account(db);const dog=(await db.query(`insert into ps_dogs(name) values('보리') returning id`)).rows[0].id;
await db.query(`insert into ps_notes(pet_id,observation) values($1,'현관 앞에서 짖었다')`,[dog]);
const request=(await db.query(`insert into ps_requests(pet_id,context,consent_version) values($1,'산책 직전','2026-11-04') returning id,status`,[dog])).rows[0];assert.equal(request.status,'awaiting_model');
await assert.rejects(db.query(`update ps_requests set status='succeeded' where id=$1`,[request.id]));
await asUser(db,B,SB);await account(db);assert.equal((await db.query('select * from ps_dogs')).rows.length,0);
await assert.rejects(db.query(`insert into ps_notes(pet_id,observation) values($1,'foreign')`,[dog]));assert.equal((await db.query(`delete from ps_dogs where id=$1 returning id`,[dog])).rows.length,0);
await asUser(db);await assert.rejects(db.query(`update ps_dogs set owner=$1 where id=$2`,[B,dog]));await db.query(`update ps_requests set status='cancelled' where id=$1`,[request.id]);await db.query(`delete from ps_dogs where id=$1`,[dog]);assert.equal((await db.query('select * from ps_notes')).rows.length,0);assert.equal((await db.query('select * from ps_requests')).rows.length,0);
}finally{await db.close();}});
test('anonymous and revoked sessions cannot use records even with the same subject',async()=>{const db=await setup();try{
await asUser(db,A,SA,true);await assert.rejects(account(db));await asUser(db);await account(db);await db.query(`insert into ps_dogs(name) values('dog')`);
await db.exec(`reset role;delete from auth.sessions where id='${SA}'`);await asUser(db);assert.equal((await db.query('select * from ps_dogs')).rows.length,0);await assert.rejects(db.query(`insert into ps_dogs(name) values('bad')`));await db.exec('set role anon');await assert.rejects(db.query('select * from ps_dogs'));
}finally{await db.close();}});
test('server quotas, dog-only constraints and immutable retention apply to API-equivalent writes',async()=>{const db=await setup();try{
await asUser(db);await account(db);await assert.rejects(db.query(`insert into ps_dogs(name,species) values('cat','cat')`));for(let i=0;i<20;i++)await db.query('insert into ps_dogs(name) values($1)',[`dog-${i}`]);await assert.rejects(db.query(`insert into ps_dogs(name) values('overflow')`));await assert.rejects(db.query(`update ps_dogs set expires_at=now()+interval '100 days'`));await db.exec(`reset role;delete from auth.users where id='${A}'`);assert.equal((await db.query('select * from ps_dogs')).rows.length,0);
}finally{await db.close();}});
