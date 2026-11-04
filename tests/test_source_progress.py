import json,tempfile,unittest
from pathlib import Path
from knowledge.pipeline import open_db,cycle
from knowledge.source_automation import import_candidates,status
from knowledge.source_progress import progress,packet
from test_knowledge import VIDEO,CHANNEL,FakeProviders,config
class ProgressTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.db=open_db(Path(self.tmp.name)/'db');self.addCleanup(self.db.close);self.cfg=config()
  import_candidates(self.db,[{'video_id':VIDEO,'title':'index only','query':'dog','evidence_url':'https://example.org/source'}],now=1000)
 def test_title_never_becomes_behavior_truth(self):
  r=progress(self.db,None,now=1000)[VIDEO];self.assertEqual(r['analysis_status'],'metadata_missing');self.assertFalse(r['training_ready']);self.assertEqual(r['proposal_count'],0)
 def test_actual_analysis_and_revocation_change_display_without_db_mutation(self):
  cycle(self.db,self.cfg,FakeProviders(),now=1000)
  r=progress(self.db,self.cfg,now=1001)[VIDEO];self.assertEqual(r['analysis_status'],'machine_extracted_unreviewed');self.assertEqual(r['proposal_count'],1)
  self.cfg.policies.clear();self.assertEqual(progress(self.db,self.cfg,now=1002)[VIDEO]['analysis_status'],'permission_required')
  self.assertFalse(progress(self.db,None,now=1001)[VIDEO]['training_ready'])
 def test_stale_model_and_invalid_observation_are_never_ready(self):
  cycle(self.db,self.cfg,FakeProviders(),now=1000)
  self.assertEqual(progress(self.db,self.cfg,now=90000)[VIDEO]['analysis_status'],'metadata_stale')
  self.db.execute('UPDATE videos SET model=?',('other',));self.assertEqual(progress(self.db,self.cfg,now=1001)[VIDEO]['analysis_status'],'model_changed')
  self.db.execute('UPDATE videos SET model=?,analysis=?',(self.cfg.gemini_model,'{"species":"dog"}'));self.assertEqual(progress(self.db,self.cfg,now=1001)[VIDEO]['analysis_status'],'evidence_invalid')
 def test_review_packet_has_no_fabricated_identity_or_label(self):
  cycle(self.db,self.cfg,FakeProviders(),now=1000);p=packet(self.db,self.cfg,now=1001)
  self.assertFalse(p['training_ready']);self.assertEqual(len(p['proposals']),1);self.assertIsNone(p['review_template']['animal_id']);self.assertIsNone(p['review_template']['label'])
  self.cfg.policies.clear();self.assertEqual(packet(self.db,self.cfg,now=1001)['proposals'],[])
 def test_status_uses_current_progress_not_hardcoded_not_analyzed(self):
  cycle(self.db,self.cfg,FakeProviders(),now=1000)
  self.assertEqual(status(self.db,now=1001,config=self.cfg)['links'][0]['analysis_status'],'machine_extracted_unreviewed')
