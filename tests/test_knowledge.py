import json
import tempfile
import unittest
from pathlib import Path
import httpx
from knowledge.models import Config, Analysis
from knowledge.pipeline import cycle, search, open_db
from knowledge.providers import Providers

VIDEO = 'abcdefghijk'
CHANNEL = 'UC' + 'a' * 22


def config():
    return Config.model_validate(dict(queries=['dog behaviour'], daily_requests=30,
        policies={CHANNEL: dict(analysis_allowed=True, knowledge_allowed=True,
            notebook_allowed=True, evidence='contract-123', expires_at=2000000000)}))


def analysis():
    return dict(species='dog', entries=[dict(start_seconds=2, end_seconds=4,
        kind='observation', text='Dog moves away from the door.', confidence=.8)])


class FakeProviders:
    def __init__(self):
        self.analyzed = 0
        self.synced = 0
        self.deleted = 0
        self.public = True
        self.fail_sync = False

    def discover(self, query):
        return [VIDEO]

    def video(self, video_id):
        if not self.public:
            return None
        return dict(id=video_id, channel_id=CHANNEL, title='Dog at a door', duration=20)

    def analyze(self, video_id):
        self.analyzed += 1
        return Analysis.model_validate(analysis())

    def notebook_add(self, video_id):
        self.synced += 1
        if self.fail_sync:
            raise ValueError('provider unavailable')
        return 'source-123'

    def notebook_delete(self, source_id):
        self.deleted += 1


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = open_db(Path(self.tmp.name) / 'knowledge.db')
        self.addCleanup(self.db.close)
        self.provider = FakeProviders()
        self.cfg = config()

    def test_discovery_analysis_retrieval_and_dedup(self):
        cycle(self.db, self.cfg, self.provider, now=1000)
        hits = search(self.db, self.cfg, 'door', now=1001)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['citation'], f'https://www.youtube.com/watch?v={VIDEO}&t=2s')
        self.assertEqual(hits[0]['verification'], 'machine_extracted_unreviewed')
        cycle(self.db, self.cfg, self.provider, now=1002)
        self.assertEqual(self.provider.analyzed, 1)

    def test_unknown_and_revoked_rights_block_analysis_and_search(self):
        empty = self.cfg.model_copy(update={'policies': {}})
        cycle(self.db, empty, self.provider, now=1000)
        self.assertEqual(self.provider.analyzed, 0)
        cycle(self.db, self.cfg, self.provider, now=1001)
        self.assertEqual(search(self.db, empty, 'door', now=1002), [])

    def test_expiry_and_private_video_remove_local_knowledge(self):
        cycle(self.db, self.cfg, self.provider, now=1000)
        self.assertEqual(search(self.db, self.cfg, 'door', now=1000+31*86400), [])
        self.provider.public = False
        cycle(self.db, self.cfg, self.provider, now=1000+86401)
        self.assertEqual(search(self.db, self.cfg, 'door', now=1000+86402), [])

    def test_daily_budget_persists_and_blocks_calls(self):
        cfg = self.cfg.model_copy(update={'daily_requests': 1})
        cycle(self.db, cfg, self.provider, now=1000)
        cycle(self.db, cfg, self.provider, now=1001)
        self.assertEqual(self.provider.analyzed, 0)
        self.assertEqual(self.db.execute('select sum(count) from usage').fetchone()[0], 1)

    def test_notebook_sync_once_and_revocation_delete(self):
        cfg = self.cfg.model_copy(update={'notebook': 'projects/123/locations/global/notebooks/abc'})
        cycle(self.db, cfg, self.provider, now=1000)
        cycle(self.db, cfg, self.provider, now=1001)
        self.assertEqual(self.provider.synced, 1)
        cycle(self.db, cfg.model_copy(update={'policies': {}}), self.provider, now=1002)
        self.assertEqual(self.provider.deleted, 1)

    def test_uncertain_notebook_write_is_not_blindly_retried(self):
        cfg = self.cfg.model_copy(update={'notebook': 'projects/123/locations/global/notebooks/abc'})
        self.provider.fail_sync = True
        cycle(self.db, cfg, self.provider, now=1000)
        cycle(self.db, cfg, self.provider, now=1001)
        self.assertEqual(self.provider.synced, 1)

    def test_bad_timestamps_are_not_indexed(self):
        self.provider.analyze = lambda _: Analysis.model_validate({**analysis(), 'entries': [
            {**analysis()['entries'][0], 'end_seconds': 9999}]})
        cycle(self.db, self.cfg, self.provider, now=1000)
        self.assertEqual(search(self.db, self.cfg, 'door', now=1001), [])

    def test_unknown_configuration_fields_and_hosts_rejected(self):
        for patch in ({'endpoint':'http://localhost'}, {'gemini_model':'../../secret'},
                      {'notebook':'http://evil'}, {'policies':{'fake':{}}}):
            with self.assertRaises(ValueError):
                Config.model_validate({**self.cfg.model_dump(), **patch})

    def test_analysis_schema_rejects_commands_and_nonfinite_confidence(self):
        with self.assertRaises(ValueError):
            Analysis.model_validate({**analysis(), 'command': 'download everything'})
        with self.assertRaises(ValueError):
            Analysis.model_validate({**analysis(), 'entries':[{
                **analysis()['entries'][0], 'confidence':float('nan')}]})


class ProviderTests(unittest.TestCase):
    def test_disabled_provider_never_uses_transport(self):
        def fail(request):
            self.fail('unexpected HTTP call')
        p = Providers(config(), httpx.Client(transport=httpx.MockTransport(fail)), {})
        with self.assertRaises(ValueError):
            p.discover('dog')

    def test_gemini_fixed_host_url_input_and_schema(self):
        def handle(request):
            self.assertEqual(request.url.host, 'generativelanguage.googleapis.com')
            body = json.loads(request.content)
            self.assertIn(VIDEO, body['contents'][0]['parts'][0]['file_data']['file_uri'])
            self.assertNotIn('tools', body)
            return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':json.dumps(analysis())}]}}]})
        p = Providers(config(), httpx.Client(transport=httpx.MockTransport(handle)),
                      {'PETSENSE_ENABLE_KNOWLEDGE':'true','GEMINI_API_KEY':'test'})
        self.assertEqual(p.analyze(VIDEO).species, 'dog')
        with self.assertRaises(ValueError):
            p.analyze('../bad')

    def test_provider_error_does_not_expose_key_or_response(self):
        p = Providers(config(), httpx.Client(transport=httpx.MockTransport(
            lambda r: httpx.Response(403,text='secret-key'))),
            {'PETSENSE_ENABLE_KNOWLEDGE':'true','YOUTUBE_API_KEY':'secret-key'})
        with self.assertRaisesRegex(ValueError, '^Provider unavailable$'):
            p.discover('dog')

    def test_official_search_video_and_notebook_contracts(self):
        cfg = config().model_copy(update={'notebook':'projects/123/locations/global/notebooks/abc'})
        seen = []
        def handle(request):
            seen.append(request)
            if request.url.path.endswith('/search'):
                return httpx.Response(200,json={'items':[{'id':{'videoId':VIDEO}},{'id':{'videoId':'../bad'}}]})
            if request.url.path.endswith('/videos'):
                return httpx.Response(200,json={'items':[{'id':VIDEO,'snippet':{'channelId':CHANNEL,'title':'dog'},
                    'status':{'privacyStatus':'public'},'contentDetails':{'duration':'PT1M20S'}}]})
            self.assertEqual(request.url.host,'global-discoveryengine.googleapis.com')
            body = json.loads(request.content)
            if request.url.path.endswith(':batchCreate'):
                self.assertEqual(body,{'userContents':[{'videoContent':{'youtubeUrl':f'https://www.youtube.com/watch?v={VIDEO}'}}]})
                return httpx.Response(200,json={'sources':[{'sourceId':{'id':'source-123'}}]})
            self.assertEqual(body,{'names':['projects/123/locations/global/notebooks/abc/sources/source-123']})
            return httpx.Response(200,json={})
        p = Providers(cfg,httpx.Client(transport=httpx.MockTransport(handle)),{
            'PETSENSE_ENABLE_KNOWLEDGE':'true','YOUTUBE_API_KEY':'yt-test','GOOGLE_ACCESS_TOKEN':'cloud-test'})
        self.assertEqual(p.discover('dog'),[VIDEO])
        self.assertEqual(p.video(VIDEO)['duration'],80)
        self.assertEqual(p.notebook_add(VIDEO),'source-123')
        p.notebook_delete('source-123')
        self.assertEqual(len(seen),4)

    def test_redirect_and_oversized_responses_rejected(self):
        for response in (httpx.Response(302,headers={'location':'http://127.0.0.1/'}),
                         httpx.Response(200,content=b'x'*256001)):
            p = Providers(config(),httpx.Client(transport=httpx.MockTransport(lambda r: response)),{
                'PETSENSE_ENABLE_KNOWLEDGE':'true','YOUTUBE_API_KEY':'test'})
            with self.assertRaises(ValueError):
                p.discover('dog')


class RetrievalRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_auth_and_local_only_cited_search(self):
        import os
        import time
        from unittest.mock import patch
        from backend.app import app
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            cfg = config()
            (path/'config.json').write_text(cfg.model_dump_json())
            db = open_db(path/'index.db')
            cycle(db,cfg,FakeProviders(),now=time.time())
            db.close()
            with patch.dict(os.environ,{'PETSENSE_API_TOKEN':'test-token',
                    'PETSENSE_KNOWLEDGE_CONFIG':str(path/'config.json'),
                    'PETSENSE_KNOWLEDGE_DB':str(path/'index.db')},clear=True):
                client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test")
                self.assertEqual((await client.get('/v1/knowledge/search?q=door')).status_code,401)
                headers={'Authorization':'Bearer test-token'}
                response=await client.get('/v1/knowledge/search?q=door',headers=headers)
                self.assertEqual(response.status_code,200)
                self.assertFalse(response.json()['abstained'])
                self.assertIn(VIDEO,response.json()['matches'][0]['citation'])
                cfg.policies.clear()
                (path/'config.json').write_text(cfg.model_dump_json())
                self.assertTrue((await client.get('/v1/knowledge/search?q=door',headers=headers)).json()['abstained'])
                await client.aclose()

    def test_cli_missing_credentials_exits_without_network(self):
        import os
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            (path/'config.json').write_text(config().model_dump_json())
            env = {k:v for k,v in os.environ.items() if k not in (
                'PETSENSE_ENABLE_KNOWLEDGE','YOUTUBE_API_KEY','GEMINI_API_KEY')}
            proc=subprocess.run([sys.executable,'-m','knowledge.worker','--config',str(path/'config.json'),
                '--db',str(path/'index.db')],capture_output=True,text=True,env=env)
            self.assertEqual(proc.returncode,2)
            self.assertIn('blocked',proc.stderr)

class CandidateTests(unittest.TestCase):
    setUp = KnowledgeTests.setUp
    def test_discovery_only_never_analyzes_or_syncs(self):
        cycle(self.db,self.cfg,self.provider,now=1000,discovery_only=True)
        self.assertEqual(self.provider.analyzed,0)
        self.assertEqual(self.provider.synced,0)
        from knowledge.candidates import candidates
        rows=candidates(self.db,self.cfg,now=1001)
        self.assertEqual(rows[0]['status'],'awaiting_analysis')
        self.assertFalse(rows[0]['training_ready'])
        self.cfg.policies.clear()
        self.assertEqual(candidates(self.db,self.cfg,now=1001)[0]['status'],'rights_review_required')

    def test_candidate_analysis_is_not_training_approval(self):
        from knowledge.candidates import candidates
        cycle(self.db,self.cfg,self.provider,now=1000)
        row=candidates(self.db,self.cfg,now=1001)[0]
        self.assertEqual(row['status'],'independent_review_required')
        self.assertFalse(row['training_ready'])
        self.assertNotIn('entries',row)
        self.assertEqual(candidates(self.db,self.cfg,now=90000)[0]['status'],'metadata_refresh_required')
