import asyncio,json,unittest
import httpx
from backend.local_vlm import LocalConfig,observe_local
from backend.vlm import VisionInput,VLMError
from test_vlm import IMAGE,RESULT

class LocalVLMTests(unittest.TestCase):
    def config(self):return LocalConfig('http://127.0.0.1:11434/v1','synthetic-vision','local-test-key')
    def test_config_consent_and_no_unapproved_transport(self):
        for endpoint in ['http://company.example/v1','http://user:pass@localhost/v1','https://company.example/v1?key=x','https://company.example/other','http://localhost:99999/v1']:
            with self.assertRaises(ValueError):LocalConfig(endpoint,'model')
        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:self.fail('No consent transport'))) as client:
                with self.assertRaises(VLMError):await observe_local(VisionInput(image_base64=IMAGE,consent=False),client,self.config())
        asyncio.run(run())
    def test_payload_dog_only_and_single_attempt_errors(self):
        async def run():
            calls=[]
            def handler(req):
                calls.append(req);self.assertEqual(str(req.url),'http://127.0.0.1:11434/v1/chat/completions')
                self.assertEqual(req.headers['authorization'],'Bearer local-test-key')
                body=json.loads(req.content);self.assertFalse(body['stream']);self.assertEqual(body['model'],'synthetic-vision')
                return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({**RESULT,'species':'cat','abstained':False,'confidence':.9})}}]})
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                result=await observe_local(VisionInput(image_base64=IMAGE,consent=True),client,self.config())
                self.assertTrue(result.abstained);self.assertEqual(result.posture,'unknown');self.assertEqual(len(calls),1)
            for status,content in [(302,b'private-provider-text'),(429,b'private-provider-text'),(200,b'x'*64001),(200,b'{}'),(200,json.dumps({'choices':[{'message':[]}]}).encode())]:
                count=0
                def failure(req):
                    nonlocal count;count+=1
                    return httpx.Response(status,content=content,headers={'Location':'https://unrelated.example/'})
                async with httpx.AsyncClient(transport=httpx.MockTransport(failure)) as client:
                    with self.assertRaises(VLMError) as caught:await observe_local(VisionInput(image_base64=IMAGE,consent=True),client,self.config())
                    self.assertNotIn('private-provider-text',str(caught.exception));self.assertEqual(count,1)
        asyncio.run(run())
    def test_absolute_deadline_and_cancellation_propagate(self):
        async def run():
            stopped=asyncio.Event()
            async def handler(req):
                try:await asyncio.sleep(60)
                finally:stopped.set()
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                with self.assertRaises(VLMError):await observe_local(VisionInput(image_base64=IMAGE,consent=True),client,self.config(),deadline=.01)
                self.assertTrue(stopped.is_set());stopped.clear()
                task=asyncio.create_task(observe_local(VisionInput(image_base64=IMAGE,consent=True),client,self.config()))
                await asyncio.sleep(.01);task.cancel()
                with self.assertRaises(asyncio.CancelledError):await task
                self.assertTrue(stopped.is_set())
        asyncio.run(run())

class LocalVisionRouteTests(unittest.TestCase):
    def test_owner_consent_body_bounds_busy_and_revoked_session(self):
        import os,tempfile
        from unittest.mock import patch,AsyncMock
        from backend.accounts import Store
        from backend.app import app
        from backend.vlm import VisionResult
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':td+'/db','PETSENSE_ENABLE_WEB_AUTH':'false','PETSENSE_ENABLE_LOCAL_VLM':'true','PETSENSE_LOCAL_VLM_BASE_URL':'http://127.0.0.1:11434/v1','PETSENSE_LOCAL_VLM_MODEL':'test-vision'}):
            store=Store(td+'/db');owner,token=store.issue();headers={'X-PetSense-Session':token};payload={'image_base64':IMAGE,'consent':True}
            async def run():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as c:
                    url='/v1/me/vision/local-observe'
                    with patch('backend.local_vision.until_disconnect',new=AsyncMock(return_value=VisionResult(**RESULT))) as invoke:
                        self.assertEqual((await c.post(url,json=payload)).status_code,401)
                        self.assertEqual((await c.post(url,headers=headers,json={**payload,'consent':False})).status_code,403)
                        self.assertEqual((await c.post(url,headers=headers,json={**payload,'endpoint':'https://unrelated.example'})).status_code,422)
                        self.assertEqual((await c.post(url,headers={**headers,'Content-Type':'application/json'},content=b'x'*750001)).status_code,413)
                        invoke.assert_not_called()
                        async with app.state.local_vision_lock:self.assertEqual((await c.post(url,headers=headers,json=payload)).status_code,429)
                        good=await c.post(url,headers=headers,json=payload);self.assertEqual(good.status_code,200);self.assertEqual(good.headers['cache-control'],'no-store')
                    async def revoked(*args):
                        store.delete_account(owner)
                        return VisionResult(**RESULT)
                    with patch('backend.local_vision.until_disconnect',side_effect=revoked):
                        self.assertEqual((await c.post(url,headers=headers,json=payload)).status_code,401)
                    self.assertFalse(app.state.local_vision_lock.locked())
            asyncio.run(run())
    def test_disconnect_cancels_and_reaps_transport(self):
        from unittest.mock import patch
        from fastapi import HTTPException
        from backend.local_vision import until_disconnect
        async def run():
            stopped=asyncio.Event();started=asyncio.Event()
            class Request:
                async def receive(self):
                    await started.wait();return {'type':'http.disconnect'}
            async def inference(*args):
                started.set()
                try:await asyncio.sleep(60)
                finally:stopped.set()
            with patch('backend.local_vision.observe_local',side_effect=inference):
                with self.assertRaises(HTTPException) as caught:await until_disconnect(Request(),VisionInput(image_base64=IMAGE,consent=True),LocalConfig('http://localhost:11434/v1','test'))
            self.assertEqual(caught.exception.status_code,499);self.assertTrue(stopped.is_set())
        asyncio.run(run())
    def test_https_cookie_csrf_before_any_local_transport(self):
        import os,tempfile
        from unittest.mock import patch,AsyncMock
        from backend.accounts import Store
        from backend.app import app
        from backend.web_security import COOKIE,csrf_value
        from backend.vlm import VisionResult
        env={'PETSENSE_ENABLE_WEB_AUTH':'true','PETSENSE_PUBLIC_ORIGIN':'https://test','PETSENSE_OPERATOR_NAME':'test','PETSENSE_PRIVACY_CONTACT':'test@example.invalid','PETSENSE_TERMS_VERSION':'v1','PETSENSE_PRIVACY_VERSION':'v1','PETSENSE_ENABLE_LOCAL_VLM':'true','PETSENSE_LOCAL_VLM_BASE_URL':'http://localhost:11434/v1','PETSENSE_LOCAL_VLM_MODEL':'test'}
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{**env,'PETSENSE_ACCOUNT_DB':td+'/db'}):
            _,token=Store(td+'/db').issue()
            async def run():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as c:
                    c.cookies.set(COOKIE,token)
                    with patch('backend.local_vision.until_disconnect',new=AsyncMock(return_value=VisionResult(**RESULT))) as invoke:
                        url='/v1/me/vision/local-observe';body={'image_base64':IMAGE,'consent':True}
                        self.assertEqual((await c.post(url,json=body)).status_code,403);invoke.assert_not_called()
                        self.assertEqual((await c.post(url,headers={'Origin':'https://test','X-PetSense-CSRF':csrf_value(token)},json=body)).status_code,200)
            asyncio.run(run())
