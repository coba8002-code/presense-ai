import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave
import sys
from concurrent.futures import ThreadPoolExecutor

from backend.accounts import Store
from backend.job_store import JobStore, Conflict, Capacity
from training.pretrained_audio import MODEL,REVISION,DOG_LABELS
from test_foundation import request


def wav():
    stream=io.BytesIO()
    with wave.open(stream,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(bytes(32000))
    return stream.getvalue()

def result(raw):
    return dict(model=MODEL,revision=REVISION,input_sha256=hashlib.sha256(raw).hexdigest(),decision='abstain',
        production_ready=False,species_verified=False,dog_event_scores=[{'label':name,'score':.1} for name in DOG_LABELS])


class AudioJobTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'accounts.sqlite3';self.now=[1000]
        self.store=JobStore(self.path,clock=lambda:self.now[0]);self.owner,self.token=self.store.issue(ttl=604800)
        _,self.other=self.store.issue(ttl=604800);self.pet=self.store.pet_create(self.token,'dog')['id'];self.raw=wav()

    def enqueue(self,key='same-idempotency-key',**kw):
        return self.store.enqueue(self.token,self.pet,key,kw.get('raw',self.raw))

    def test_idempotent_retry_and_conflict_do_not_duplicate_or_charge_twice(self):
        first=self.enqueue();again=self.enqueue()
        self.assertEqual(first['id'],again['id']);self.assertTrue(again['reused'])
        changed=bytearray(self.raw);changed[-1]=1
        with self.assertRaises(Conflict):self.enqueue(raw=bytes(changed))
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count FROM audio_usage').fetchone()[0],1)

    def test_owner_and_pet_scope_and_response_never_contains_media_or_credentials(self):
        job=self.enqueue()
        with self.assertRaises(KeyError):self.store.get(self.other,job['id'])
        with self.assertRaises(KeyError):self.store.cancel(self.other,job['id'])
        with self.assertRaises(KeyError):self.store.enqueue(self.other,self.pet,'other-idempotency-key',self.raw)
        text=json.dumps(job);self.assertNotIn(self.token,text);self.assertNotIn('media',job);self.assertNotIn('session_hash',job)

    def test_single_global_claim_completion_and_raw_removal(self):
        job=self.enqueue();claim=self.store.claim();self.assertEqual(claim['id'],job['id'])
        self.assertIsNone(self.store.claim())
        self.assertTrue(self.store.finish(claim,result(self.raw)))
        self.assertEqual(self.store.get(self.token,job['id'])['status'],'succeeded')
        with self.store.connect() as db:self.assertIsNone(db.execute('SELECT media FROM audio_jobs').fetchone()[0])
        self.assertFalse(self.store.finish(claim,result(self.raw)))

    def test_cancel_and_lease_expiry_prevent_late_result(self):
        first=self.enqueue();claim=self.store.claim();self.store.cancel(self.token,first['id'])
        self.assertFalse(self.store.finish(claim,result(self.raw)))
        second=self.enqueue('second-idempotency-key');lease=self.store.claim();self.now[0]+=91
        self.store.claim()
        self.assertEqual(self.store.get(self.token,second['id'])['error'],'worker_lost')
        self.assertFalse(self.store.finish(lease,result(self.raw)))

    def test_raw_expiry_and_profile_or_account_deletion_remove_jobs(self):
        job=self.enqueue();self.now[0]+=901
        self.assertEqual(self.store.get(self.token,job['id'])['status'],'expired')
        self.store.pet_delete(self.token,self.pet)
        with self.assertRaises(KeyError):self.store.get(self.token,job['id'])
        self.pet=self.store.pet_create(self.token,'dog')['id'];self.enqueue('second-idempotency-key')
        self.store.delete_account(self.owner)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM audio_jobs').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM audio_usage').fetchone()[0],0)

    def test_pending_and_daily_limits_and_persistent_state(self):
        self.enqueue();self.enqueue('second-idempotency-key')
        with self.assertRaises(Capacity):self.enqueue('third-idempotency-key')
        self.assertEqual(len(JobStore(self.path,clock=lambda:self.now[0]).list_jobs(self.token)),2)
        for row in self.store.list_jobs(self.token):self.store.cancel(self.token,row['id'])
        for i in range(18):
            job=self.enqueue('another-idempotency-key-'+str(i));self.store.cancel(self.token,job['id'])
        with self.assertRaises(Capacity):self.enqueue('quota-exceeded-idempotency')

    def test_session_revocation_and_forged_worker_result_fail_closed(self):
        job=self.enqueue();claim=self.store.claim()
        bad=result(self.raw);bad['input_sha256']='wrong'
        with self.assertRaises(ValueError):self.store.finish(claim,bad)
        with self.store.connect() as db:db.execute('DELETE FROM sessions WHERE owner=?',(self.owner,))
        self.assertFalse(self.store.keep_running(claim));self.assertFalse(self.store.finish(claim,result(self.raw)))
        with self.store.connect() as db:self.assertIsNone(db.execute('SELECT media FROM audio_jobs WHERE id=?',(job['id'],)).fetchone()[0])

    def test_worker_completes_or_cancels_without_exposing_result(self):
        from backend.job_worker import once
        import asyncio
        async def score(raw,timeout):return result(raw)
        job=self.enqueue()
        with patch('backend.job_worker.run_ast',score):self.assertTrue(asyncio.run(once(self.store)))
        self.assertEqual(self.store.get(self.token,job['id'])['status'],'succeeded')
        second=self.enqueue('second-idempotency-key');cancelled=[]
        async def blocked(raw,timeout):
            self.store.cancel(self.token,second['id'])
            try:await asyncio.sleep(5)
            finally:cancelled.append(True)
        with patch('backend.job_worker.run_ast',blocked):asyncio.run(once(self.store))
        self.assertTrue(cancelled);self.assertIsNone(self.store.get(self.token,second['id'])['result'])

    def test_worker_loss_is_visible_without_another_worker_claim(self):
        job=self.enqueue();self.store.claim();self.now[0]+=91
        self.assertEqual(self.store.get(self.token,job['id'])['status'],'failed')

    def test_concurrent_duplicate_submissions_have_one_identity(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=list(pool.map(lambda _:self.enqueue(),range(2)))
        self.assertEqual(jobs[0]['id'],jobs[1]['id'])
        self.assertEqual(len(self.store.list_jobs(self.token)),1)

    def test_global_pending_cap_across_owners(self):
        for i in range(4):
            _,token=self.store.issue();pet=self.store.pet_create(token,'dog')['id']
            for j in range(2):self.store.enqueue(token,pet,f'global-quota-key-{i}-{j}',self.raw)
        with self.assertRaises(Capacity):self.enqueue()

    def test_persisted_cancellation_kills_actual_model_child(self):
        from backend.job_worker import once
        job=self.enqueue();pidfile=Path(self.temp.name)/'worker-pid'
        code=f'import os,sys,time;from pathlib import Path;sys.stdin.buffer.read();Path({str(pidfile)!r}).write_text(str(os.getpid()));time.sleep(30)'
        async def scenario():
            task=asyncio.create_task(once(self.store))
            try:
                for _ in range(200):
                    if pidfile.exists():break
                    await asyncio.sleep(.005)
                self.assertTrue(pidfile.exists());self.store.cancel(self.token,job['id'])
                await asyncio.wait_for(task,3)
            finally:
                if not task.done():task.cancel();await asyncio.gather(task,return_exceptions=True)
        with patch('backend.audio_process.worker_command',return_value=[sys.executable,'-c',code]):asyncio.run(scenario())
        self.assertEqual(self.store.get(self.token,job['id'])['status'],'cancelled')
        if os.name=='posix':
            with self.assertRaises(ProcessLookupError):os.kill(int(pidfile.read_text()),0)


class AudioJobApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'jobs.sqlite3';self.store=JobStore(self.path)
        _,self.token=self.store.issue();_,self.other=self.store.issue();self.pet=self.store.pet_create(self.token,'dog')['id']
        env=patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':str(self.path),'PETSENSE_ENABLE_AST_JOBS':'true'})
        env.start();self.addCleanup(env.stop)

    def headers(self):return {'X-PetSense-Session':self.token,'X-PetSense-Pet-ID':self.pet,'Content-Type':'audio/wav',
        'X-Audio-Consent':'true','X-Audio-Species':'dog','X-Job-Storage-Consent':'true','Idempotency-Key':'unique-api-request-key'}

    def call(self,method='POST',path='/v1/me/audio-jobs',headers=None,content=None):
        return asyncio.run(request(method,path,headers=headers or self.headers(),content=wav() if content is None and method=='POST' else content))

    def test_submit_poll_cancel_and_other_owner_denial(self):
        response=self.call();self.assertEqual(response.status_code,202,response.text);job=response.json()
        self.assertEqual(self.call().json()['id'],job['id'])
        foreign={**self.headers(),'X-PetSense-Session':self.other}
        self.assertEqual(self.call('GET','/v1/me/audio-jobs/'+job['id'],foreign).status_code,404)
        polled=self.call('GET','/v1/me/audio-jobs/'+job['id']);self.assertEqual(polled.headers['cache-control'],'no-store')
        self.assertEqual(polled.json()['status'],'queued')
        cancelled=self.call('DELETE','/v1/me/audio-jobs/'+job['id'],{**self.headers(),'X-Delete-Confirm':'cancel-job'})
        self.assertEqual(cancelled.status_code,200);self.assertEqual(cancelled.json()['status'],'cancelled')

    def test_gate_input_consent_species_key_and_bounded_audio(self):
        for field,value,code in [('X-PetSense-Session','bad',401),('X-Job-Storage-Consent','false',403),('X-Audio-Consent','false',403),('X-Audio-Species','cat',422),('Content-Type','audio/mpeg',415),('Idempotency-Key','bad',422)]:
            with self.subTest(field=field):self.assertEqual(self.call(headers={**self.headers(),field:value}).status_code,code)
        self.assertEqual(self.call(content=b'bad-wav').status_code,422)
        self.assertEqual(self.call(content=b'x'*2000001).status_code,413)
        with patch.dict(os.environ,{'PETSENSE_ENABLE_AST_JOBS':'false'}):self.assertEqual(self.call().status_code,503)


if __name__=='__main__':unittest.main()
