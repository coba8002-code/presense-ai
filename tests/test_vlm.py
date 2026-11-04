import asyncio
import base64
import json
import os
import unittest
from unittest.mock import patch
import httpx
from pydantic import ValidationError
from backend.vlm import VisionInput, VisionResult, observe, VLMError
from test_foundation import request

IMAGE = base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'test-only').decode()
RESULT = dict(species='dog', posture='sitting', ears='unknown', tail='unknown',
              visibility='clear', hypotheses=['insufficient_context'], confidence=.4,
              abstained=True)


class VLMTests(unittest.TestCase):
    def test_rejects_bad_image_and_emotion_as_observation(self):
        with self.assertRaises(ValidationError):
            VisionInput(image_base64='not image', consent=True)
        with self.assertRaises(ValidationError):
            VisionResult(**{**RESULT, 'posture': 'happy'})
        with self.assertRaises(ValidationError):
            VisionResult(**{**RESULT, 'diagnosis': 'disease'})

    def test_disabled_and_unauthenticated_never_call_cloud(self):
        with patch.dict(os.environ, {}, clear=True):
            response = asyncio.run(request('POST', '/v1/vision/observe', json={'image_base64': IMAGE, 'consent': True}))
            self.assertEqual(response.status_code, 503)
        with patch.dict(os.environ, {'PETSENSE_ENABLE_CLOUD': 'true', 'PETSENSE_API_TOKEN': 'local-test-token'}):
            response = asyncio.run(request('POST', '/v1/vision/observe', json={}))
            self.assertEqual(response.status_code, 401)

    def test_consent_required_before_transport(self):
        def handler(req):
            self.fail('Cloud called without consent')
        async def scenario():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                with self.assertRaises(VLMError):
                    await observe(VisionInput(image_base64=IMAGE, consent=False), client, 'test', 'model')
        asyncio.run(scenario())

    def test_payload_and_low_confidence_abstention(self):
        def handler(req):
            self.assertEqual(str(req.url), 'https://api.openai.com/v1/chat/completions')
            payload = json.loads(req.content)
            self.assertEqual(payload['response_format']['type'], 'json_schema')
            self.assertFalse(payload['store'])
            return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({**RESULT, 'abstained': False})}}]})
        async def scenario():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                result = await observe(VisionInput(image_base64=IMAGE, consent=True), client, 'test', 'model')
                self.assertTrue(result.abstained)
        asyncio.run(scenario())

    def test_provider_failures_are_generic(self):
        for status, body in [(429, {'secret': 'do-not-leak'}), (200, {}),
                             (200, {'choices': [{'message': {'content': 'not json'}}]})]:
            async def scenario():
                async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(status, json=body))) as client:
                    with self.assertRaises(VLMError) as caught:
                        await observe(VisionInput(image_base64=IMAGE, consent=True), client, 'test', 'model')
                    self.assertNotIn('do-not-leak', str(caught.exception))
            asyncio.run(scenario())

    def test_authorized_request_rejects_oversized_body(self):
        env = {'PETSENSE_ENABLE_CLOUD': 'true', 'PETSENSE_API_TOKEN': 'local-test-token',
               'OPENAI_API_KEY': 'test-only', 'PETSENSE_VLM_MODEL': 'test-only'}
        with patch.dict(os.environ, env):
            response = asyncio.run(request('POST', '/v1/vision/observe', content=b'x' * 750001,
                                           headers={'Authorization': 'Bearer local-test-token'}))
            self.assertEqual(response.status_code, 413)

    def test_timeout_refusal_and_oversized_provider_response(self):
        def timeout(req):
            raise httpx.ReadTimeout('internal detail', request=req)
        handlers = [timeout,
                    lambda req: httpx.Response(200, content=b'x' * 64001),
                    lambda req: httpx.Response(200, json={'choices': [{'message': {'refusal': 'no'}}]})]
        for handler in handlers:
            async def scenario():
                async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                    with self.assertRaises(VLMError):
                        await observe(VisionInput(image_base64=IMAGE, consent=True), client, 'test', 'model')
            asyncio.run(scenario())

    def test_route_validates_without_echoing_image_and_returns_result(self):
        from unittest.mock import AsyncMock
        env = {'PETSENSE_ENABLE_CLOUD': 'true', 'PETSENSE_API_TOKEN': 'local-test-token',
               'OPENAI_API_KEY': 'test-only', 'PETSENSE_VLM_MODEL': 'test-only'}
        headers = {'Authorization': 'Bearer local-test-token'}
        with patch.dict(os.environ, env):
            response = asyncio.run(request('POST', '/v1/vision/observe', json={'image_base64': 'private-image'}, headers=headers))
            self.assertEqual(response.status_code, 422)
            self.assertNotIn('private-image', response.text)
            response = asyncio.run(request('POST', '/v1/vision/observe', json={'image_base64': IMAGE, 'consent': False}, headers=headers))
            self.assertEqual(response.status_code, 403)
            with patch('backend.vlm.observe', new=AsyncMock(return_value=VisionResult(**RESULT))):
                response = asyncio.run(request('POST', '/v1/vision/observe', json={'image_base64': IMAGE, 'consent': True}, headers=headers))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()['observation']['abstained'])
