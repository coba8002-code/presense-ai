import asyncio,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from backend.accounts import Store
from knowledge.pipeline import open_db
from knowledge.source_automation import import_candidates
from test_foundation import request
class ResearchStatusTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.path=self.root/'knowledge.db'
  self.env=patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':str(self.root/'accounts.db'),'PETSENSE_KNOWLEDGE_DB':str(self.path)});self.env.start();self.addCleanup(self.env.stop)
  _,self.token=Store(self.root/'accounts.db').issue()
 def call(self,token=None):return asyncio.run(request('GET','/v1/me/research-status',headers={'X-PetSense-Session':token or self.token}))
 def test_requires_auth_before_status_and_does_not_create_missing_db(self):
  self.assertEqual(self.call('invalid').status_code,401);self.assertEqual(self.call().status_code,503);self.assertFalse(self.path.exists())
 def test_read_only_metadata_no_paths_or_providers(self):
  with open_db(self.path) as db:import_candidates(db,[{'video_id':'qPpEpQXTQb4','title':'<script>bad</script>','query':'dog','evidence_url':'https://example.org/source'}])
  before=self.path.read_bytes();r=self.call();self.assertEqual(r.status_code,200);self.assertEqual(r.headers['cache-control'],'no-store');self.assertFalse(r.json()['training_ready']);self.assertEqual(self.path.read_bytes(),before);self.assertNotIn(str(self.root),r.text)
 def test_unconfigured_explicit_and_asset_allowlist(self):
  with patch.dict(os.environ,{'PETSENSE_KNOWLEDGE_DB':''}):self.assertEqual(self.call().json()['status'],'not_configured')
  self.assertEqual(asyncio.run(request('GET','/app/research.js')).status_code,200)
 def test_current_policy_controls_display_without_exposing_analysis_or_policy_evidence(self):
  from test_knowledge import VIDEO,CHANNEL,FakeProviders,config
  from knowledge.pipeline import cycle
  cfg=config();path=self.root/'policy.json';path.write_text(cfg.model_dump_json())
  with open_db(self.path) as db:
   import_candidates(db,[{'video_id':VIDEO,'title':'source','query':'dog','evidence_url':'https://example.org/source'}]);cycle(db,cfg,FakeProviders())
  with patch.dict(os.environ,{'PETSENSE_KNOWLEDGE_CONFIG':str(path)}):
   r=self.call();self.assertEqual(r.json()['links'][0]['analysis_status'],'machine_extracted_unreviewed');self.assertNotIn('contract-123',r.text);self.assertNotIn('Dog moves away',r.text)
   cfg.policies.clear();path.write_text(cfg.model_dump_json());self.assertEqual(self.call().json()['links'][0]['analysis_status'],'permission_required')
