import tempfile,unittest
from pathlib import Path
from knowledge.models import Config
from knowledge.pipeline import open_db,cycle
from test_knowledge import FakeProviders,VIDEO,CHANNEL
class TargetedSourcesTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.db=open_db(Path(self.tmp.name)/'db');self.addCleanup(self.db.close)
 def cfg(self,**kw):return Config.model_validate({'queries':['unused'],'video_ids':[VIDEO],'targeted_only':True,**kw})
 def test_targeted_source_metadata_checked_without_search_or_rights_bypass(self):
  cfg=self.cfg();p=FakeProviders();p.discover=lambda _:self.fail('Targeted intake must not run search');r=cycle(self.db,cfg,p,now=1000)
  self.assertEqual(r['discovered'],1);self.assertEqual(p.analyzed,0);self.assertEqual(r['blocked'],1)
 def test_targeted_approved_analysis_still_unreviewed(self):
  cfg=self.cfg(policies={CHANNEL:{'analysis_allowed':True,'knowledge_allowed':True,'evidence':'synthetic-policy','expires_at':2000}})
  p=FakeProviders();p.discover=lambda _:self.fail('Unexpected search');r=cycle(self.db,cfg,p,now=1000)
  self.assertEqual(r['analyzed'],1);self.assertIn('No model weights trained',r['notice'])
 def test_bounds_identity_and_empty_target_mode(self):
  for kw in ({'video_ids':[]},{'video_ids':[VIDEO,VIDEO]},{'video_ids':['https://private.invalid']},{'video_ids':[VIDEO]*21}):
   with self.subTest(kw=kw),self.assertRaises(ValueError):self.cfg(**kw)
 def test_targeted_mode_does_not_analyze_saved_non_target(self):
  self.db.execute('INSERT INTO videos(id,channel_id,title,duration,verified,created) VALUES(?,?,?,?,?,?)',('othervideo1',CHANNEL,'other fixture',10,1,1));self.db.commit()
  p=FakeProviders();seen=[];original=p.video
  def video(vid):seen.append(vid);return original(vid)
  p.video=video;p.discover=lambda _:self.fail('No search in targeted mode')
  cycle(self.db,self.cfg(),p,now=100000)
  self.assertEqual(seen,[VIDEO])
