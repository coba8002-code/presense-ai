import asyncio
import io
import os
import wave
import unittest
from unittest.mock import AsyncMock,MagicMock,patch
from test_foundation import request
from backend.app import app
from backend.realtime import Admission
from backend.audio_process import WorkerError,WorkerTimeout

class ProductAppTests(unittest.TestCase):
    def setUp(self):
        worker=patch('backend.audio_events.run_ast',new_callable=AsyncMock)
        self.runner=worker.start();self.addCleanup(worker.stop)
        self.runner.return_value={'decision':'abstain','production_ready':False,'dog_event_scores':[{'label':'Bark','score':.3}]}
        app.state.audio_admission=Admission();app.state.ast_lock=asyncio.Lock()
        self.env=patch.dict(os.environ,{'PETSENSE_ENABLE_AST':'true','PETSENSE_API_TOKEN':'test'});self.env.start();self.addCleanup(self.env.stop)
    def wav(self):
        b=io.BytesIO()
        with wave.open(b,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*16000)
        return b.getvalue()
    def headers(self):return {'Authorization':'Bearer test','Content-Type':'audio/wav','X-Audio-Consent':'true','X-Audio-Species':'dog'}
    def call(self,**kwargs):return asyncio.run(request('POST','/v1/audio/events',headers=kwargs.pop('headers',self.headers()),content=kwargs.pop('content',self.wav()),**kwargs))
    def test_app_assets_restrict_unlisted_files(self):
        for path in ['/app','/app/app.js','/app/app.css','/app/audio.js','/app/notes.js']:
            r=asyncio.run(request('GET',path));self.assertEqual(r.status_code,200);self.assertIn("connect-src 'self'",r.headers['content-security-policy'])
        self.assertEqual(asyncio.run(request('GET','/app/secrets.json')).status_code,404)
    def test_disabled_and_auth_consent_species_gates(self):
        with patch.dict(os.environ,{'PETSENSE_ENABLE_AST':'false'}):self.assertEqual(self.call().status_code,503)
        for field,value,code in [('Authorization','wrong',401),('X-Audio-Consent','false',403),('X-Audio-Species','cat',422)]:
            headers=self.headers();headers[field]=value;self.assertEqual(self.call(headers=headers).status_code,code)
        self.runner.assert_not_called()
    def test_invalid_file_rejected_before_worker(self):
        self.assertEqual(self.call(content=b'not a wav').status_code,422);self.runner.assert_not_called();self.assertEqual(app.state.audio_admission.active,0)
    def test_success_returns_abstaining_scores(self):
        r=self.call();self.assertEqual(r.status_code,200);self.assertEqual(r.json()['decision'],'abstain');self.assertEqual(app.state.audio_admission.active,0)
    def test_missing_model_is_clear_service_error(self):
        self.runner.side_effect=WorkerError('private detail');r=self.call();self.assertEqual(r.status_code,503);self.assertNotIn('private detail',r.text)
    def test_busy_request_returns_retry_after(self):
        lock=MagicMock();lock.locked.return_value=True
        with patch.object(app.state,'ast_lock',lock):
            r=self.call();self.assertEqual(r.status_code,429);self.assertEqual(r.headers['retry-after'],'1')
        self.assertEqual(app.state.audio_admission.active,0)
    def test_inference_deadline_releases_request_slot(self):
        self.runner.side_effect=WorkerTimeout();r=self.call();self.assertEqual(r.status_code,504);self.assertEqual(app.state.audio_admission.active,0);self.assertFalse(app.state.ast_lock.locked())
    def test_slow_upload_deadline_before_worker(self):
        from starlette.requests import Request
        from fastapi import HTTPException
        from backend.audio_events import audio_events
        async def receive():await asyncio.sleep(1);return {'type':'http.request','body':b'','more_body':False}
        scope={'type':'http','method':'POST','path':'/v1/audio/events','app':app,'headers':[(k.lower().encode(),v.encode()) for k,v in self.headers().items()]}
        with patch('backend.audio_events.UPLOAD_TIMEOUT',.005),self.assertRaises(HTTPException) as caught:asyncio.run(audio_events(Request(scope,receive)))
        self.assertEqual(caught.exception.status_code,408);self.runner.assert_not_called();self.assertEqual(app.state.audio_admission.active,0)
    def test_validated_bytes_and_deadline_pass_to_worker(self):
        raw=self.wav();self.assertEqual(self.call(content=raw).status_code,200);self.runner.assert_awaited_once_with(raw,timeout=60)

    def test_disconnect_cancels_running_worker(self):
        from starlette.requests import Request
        from fastapi import HTTPException
        from backend.audio_events import audio_events
        cancelled=[]
        async def scenario():
            started=asyncio.Event();raw=self.wav();sent=False
            async def worker(*args,**kwargs):
                started.set()
                try:await asyncio.sleep(5)
                finally:cancelled.append(True)
            async def receive():
                nonlocal sent
                if not sent:sent=True;return {'type':'http.request','body':raw,'more_body':False}
                await started.wait();return {'type':'http.disconnect'}
            scope={'type':'http','method':'POST','path':'/v1/audio/events','app':app,'headers':[(k.lower().encode(),v.encode()) for k,v in self.headers().items()]}
            self.runner.side_effect=worker
            with self.assertRaises(HTTPException) as caught:await audio_events(Request(scope,receive))
            self.assertEqual(caught.exception.status_code,499)
        asyncio.run(scenario());self.assertEqual(cancelled,[True]);self.assertEqual(app.state.audio_admission.active,0)
