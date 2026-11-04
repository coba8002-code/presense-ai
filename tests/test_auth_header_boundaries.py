"""Malformed wire credentials must be rejected, never cause a server error."""
import asyncio
import os
import unittest
from unittest.mock import patch
import httpx
from starlette.requests import Request
from fastapi import HTTPException
from backend.app import app
from backend.web_security import session_token, COOKIE


class HeaderBoundaryTests(unittest.TestCase):
    def test_non_ascii_bearer_rejected_across_api_boundaries(self):
        async def scenario():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),base_url='http://test') as client:
                for method,path in [('POST','/v1/vision/observe'),('POST','/v1/audio/chunks'),('POST','/v1/audio/events'),('GET','/v1/knowledge/search?q=dog')]:
                    for raw in [b'Bearer \xff', b'Bearer \xc3\xa9']:
                        with self.subTest(path=path,raw=raw):
                            response=await client.request(method,path,headers=[(b'authorization',raw)])
                            self.assertEqual(response.status_code,401)
        with patch.dict(os.environ,{'PETSENSE_API_TOKEN':'qa-test-only','PETSENSE_ENABLE_CLOUD':'true','PETSENSE_ENABLE_AUDIO':'true','PETSENSE_ENABLE_AST':'true','PETSENSE_ENABLE_WEB_AUTH':'false','PETSENSE_REQUIRE_ACCOUNT':'false'}):
            asyncio.run(scenario())

    def test_non_ascii_csrf_and_conflicting_session_are_rejected(self):
        env={'PETSENSE_ENABLE_WEB_AUTH':'true','PETSENSE_PUBLIC_ORIGIN':'https://test','PETSENSE_OPERATOR_NAME':'QA','PETSENSE_PRIVACY_CONTACT':'qa@example.invalid','PETSENSE_TERMS_VERSION':'v1','PETSENSE_PRIVACY_VERSION':'v1'}
        for header,status in [(b'x-petsense-csrf',403),(b'x-petsense-session',401)]:
            request=Request({'type':'http','method':'POST','path':'/','scheme':'https','server':('test',443),'query_string':b'','headers':[(b'host',b'test'),(b'origin',b'https://test'),(b'cookie',(COOKIE+'='+'a'*43).encode()),(header,b'\xff')]})
            with self.subTest(header=header),patch.dict(os.environ,env):
                with self.assertRaises(HTTPException) as error:session_token(request)
                self.assertEqual(error.exception.status_code,status)
