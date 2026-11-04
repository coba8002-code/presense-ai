import asyncio
import unittest
import httpx
from backend.app import app
from training.data import approve_dataset


async def request(method, path, **kwargs):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                base_url='http://test') as client:
        return await client.request(method, path, **kwargs)


class FoundationTests(unittest.TestCase):
    def test_health_is_not_model_readiness(self):
        response = asyncio.run(request('GET', '/healthz'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'model_ready': False})

    def test_registry_denies_unknown_rights(self):
        for name in ('barkopedia', 'catmeows', 'meow-net', 'ap-10k', 'animal-kingdom'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                approve_dataset('datasets/registry.json', name)

    def test_incomplete_approval_rejected(self):
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'registry.json'
            path.write_text(json.dumps({'x': {'status': 'approved'}}))
            with self.assertRaises(ValueError):
                approve_dataset(path, 'x')
