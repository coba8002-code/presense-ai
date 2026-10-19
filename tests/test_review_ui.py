import asyncio
import unittest
from test_foundation import request


class ReviewUITests(unittest.TestCase):
    def test_local_review_page_and_restricted_assets(self):
        response=asyncio.run(request('GET','/review'))
        self.assertEqual(response.status_code,200)
        self.assertIn('개 영상 검수',response.text)
        self.assertIn("connect-src 'none'",response.headers['content-security-policy'])
        self.assertIn('no-store',response.headers['cache-control'])
        for name in ['review.js','review.css']:
            self.assertEqual(asyncio.run(request('GET','/review/'+name)).status_code,200)
        self.assertEqual(asyncio.run(request('GET','/review/secret.json')).status_code,404)
