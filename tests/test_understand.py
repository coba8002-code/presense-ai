import asyncio
import unittest
import httpx
from backend.app import app


class UnderstandRoutesTests(unittest.TestCase):
    def test_public_bilingual_assets_are_bounded_and_do_not_enable_devices(self):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='https://test') as client:
                for path, content_type in [('/understand','text/html'),('/understand/case.js','text/javascript'),('/understand/guide.js','text/javascript'),('/understand/guide.css','text/css')]:
                    response=await client.get(path)
                    self.assertEqual(response.status_code,200)
                    self.assertIn(content_type,response.headers['content-type'])
                    self.assertEqual(response.headers['cache-control'],'no-store')
                    self.assertIn('microphone=()',response.headers['permissions-policy'])
                    self.assertIn("frame-ancestors 'none'",response.headers['content-security-policy'])
                self.assertEqual((await client.get('/understand/not-allowed.js')).status_code,404)
        asyncio.run(run())
