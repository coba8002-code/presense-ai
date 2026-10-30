import asyncio
import io
import os
import wave
import unittest
from unittest.mock import patch
from test_foundation import request
from backend.app import app
from backend.realtime import Admission

class ProductAppTests(unittest.TestCase):
    def setUp(self):
        async def inline(fn,*args): return fn(*args)
        worker=patch("backend.audio_events.asyncio.to_thread",side_effect=inline)
        worker.start();self.addCleanup(worker.stop)
        app.state.audio_admission=Admission()
        app.state.ast_lock=asyncio.Lock()
    def wav(self):
        b=io.BytesIO()
        with wave.open(b,'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*16000)
        return b.getvalue()
    def headers(self):return {'Authorization':'Bearer test','Content-Type':'audio/wav','X-Audio-Consent':'true','X-Audio-Species':'dog'}
    def test_app_assets_restrict_unlisted_files(self):
        for p in ['/app','/app/app.js','/app/app.css','/app/audio.js','/app/notes.js']:
            r=asyncio.run(request('GET',p));self.assertEqual(r.status_code,200)
            self.assertIn("connect-src 'self'",r.headers['content-security-policy'])
        self.assertEqual(asyncio.run(request('GET','/app/secrets.json')).status_code,404)
    def test_disabled_and_auth_consent_species_gates(self):
        with patch.dict(os.environ,{'PETSENSE_ENABLE_AST':'false'}):
            self.assertEqual(asyncio.run(request('POST','/v1/audio/events')).status_code,503)
        with patch.dict(os.environ,{'PETSENSE_ENABLE_AST':'true','PETSENSE_API_TOKEN':'test'}),patch('backend.audio_events.get_model') as model:
            for field,value,code in [('Authorization','wrong',401),('X-Audio-Consent','false',403),('X-Audio-Species','cat',422)]:
                h=self.headers();h[field]=value
                self.assertEqual(asyncio.run(request('POST','/v1/audio/events',headers=h,content=self.wav())).status_code,code)
            model.assert_not_called()
    def test_invalid_file_rejected_before_model(self):
        with patch.dict(os.environ,{'PETSENSE_ENABLE_AST':'true','PETSENSE_API_TOKEN':'test'}),patch('backend.audio_events.get_model') as model:
            r=asyncio.run(request('POST','/v1/audio/events',headers=self.headers(),content=b'not a wav'))
            self.assertEqual(r.status_code,422);model.assert_not_called();self.assertEqual(app.state.audio_admission.active,0)
    def test_success_returns_abstaining_model_scores(self):
        with patch.dict(os.environ,{'PETSENSE_ENABLE_AST':'true','PETSENSE_API_TOKEN':'test'}),patch('backend.audio_events.get_model') as model:
            model.return_value.analyze.return_value={'decision':'abstain','production_ready':False,'dog_event_scores':[{'label':'Bark','score':0.3}]}
            r=asyncio.run(request('POST','/v1/audio/events',headers=self.headers(),content=self.wav()))
            self.assertEqual(r.status_code,200);self.assertEqual(r.json()['decision'],'abstain');self.assertEqual(app.state.audio_admission.active,0)
    def test_missing_model_is_clear_service_error(self):
        with patch.dict(os.environ,{'PETSENSE_ENABLE_AST':'true','PETSENSE_API_TOKEN':'test'}),patch('backend.audio_events.get_model',side_effect=RuntimeError('private detail')):
            r=asyncio.run(request('POST','/v1/audio/events',headers=self.headers(),content=self.wav()))
            self.assertEqual(r.status_code,503);self.assertNotIn('private detail',r.text)

    def test_busy_worker_returns_retry_after(self):
        from backend.audio_events import InferenceBusy
        with patch.dict(os.environ,{'PETSENSE_ENABLE_AST':'true','PETSENSE_API_TOKEN':'test'}),patch('backend.audio_events.infer',side_effect=InferenceBusy()):
            r=asyncio.run(request('POST','/v1/audio/events',headers=self.headers(),content=self.wav()))
            self.assertEqual(r.status_code,429);self.assertEqual(r.headers['retry-after'],'1')
            self.assertEqual(app.state.audio_admission.active,0)

    def test_inference_deadline_releases_request_slot(self):
        async def stalled(*args):await asyncio.sleep(1)
        with patch.dict(os.environ,{'PETSENSE_ENABLE_AST':'true','PETSENSE_API_TOKEN':'test'}),patch('backend.audio_events.INFERENCE_TIMEOUT',.005),patch('backend.audio_events.asyncio.to_thread',side_effect=stalled):
            r=asyncio.run(request('POST','/v1/audio/events',headers=self.headers(),content=self.wav()))
            self.assertEqual(r.status_code,504);self.assertEqual(app.state.audio_admission.active,0)
            self.assertFalse(app.state.ast_lock.locked())

    def test_slow_upload_deadline_before_model(self):
        from starlette.requests import Request
        from fastapi import HTTPException
        from backend.audio_events import audio_events
        async def receive():
            await asyncio.sleep(1)
            return {'type':'http.request','body':b'','more_body':False}
        scope={'type':'http','method':'POST','path':'/v1/audio/events','app':app,'headers':[(k.lower().encode(),v.encode()) for k,v in self.headers().items()]}
        with patch.dict(os.environ,{'PETSENSE_ENABLE_AST':'true','PETSENSE_API_TOKEN':'test'}),patch('backend.audio_events.UPLOAD_TIMEOUT',.005),patch('backend.audio_events.get_model') as model:
            with self.assertRaises(HTTPException) as caught:asyncio.run(audio_events(Request(scope,receive)))
            self.assertEqual(caught.exception.status_code,408);model.assert_not_called()
            self.assertEqual(app.state.audio_admission.active,0)

    def test_thread_lock_remains_busy_after_request_timeout(self):
        from backend.audio_events import infer,InferenceBusy,_worker_lock
        _worker_lock.acquire()
        try:
            with self.assertRaises(InferenceBusy):infer(None,None)
        finally:_worker_lock.release()
