import asyncio
import unittest
from test_foundation import request


class ServiceDesignTests(unittest.TestCase):
    def test_prototype_has_no_provider_connections_and_is_identified_as_design(self):
        response=asyncio.run(request('GET','/design'))
        self.assertEqual(response.status_code,200)
        self.assertIn('디자인 시안',response.text)
        self.assertIn("connect-src 'none'",response.headers['content-security-policy'])
        self.assertEqual(response.headers['cache-control'],'no-store')

    def test_only_public_design_assets_are_served(self):
        for path in ['/design/design.css','/design/design.js']:
            self.assertEqual(asyncio.run(request('GET',path)).status_code,200)
        self.assertEqual(asyncio.run(request('GET','/design/accounts.sqlite3')).status_code,404)


if __name__=='__main__':unittest.main()
