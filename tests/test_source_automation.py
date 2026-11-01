import json,tempfile,unittest
from pathlib import Path
import httpx
from knowledge.pipeline import open_db
from knowledge.source_automation import AutomationConfig,cycle,import_candidates,status
CH='UCee1MvXr6E8qC_d2WEYTU5g'
XML=f'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015"><yt:channelId>{CH}</yt:channelId><entry><yt:videoId>qPpEpQXTQb4</yt:videoId><yt:channelId>{CH}</yt:channelId><title>Dog observation</title><published>2026-10-01T00:00:00Z</published></entry></feed>'''
class AutomationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.db=open_db(Path(self.tmp.name)/'db');self.addCleanup(self.db.close);self.cfg=AutomationConfig(channels=[CH],interval_seconds=300,daily_feed_requests=2)
 def test_real_feed_protocol_no_key_no_media_no_approval(self):
  calls=[]
  def handler(r):calls.append(str(r.url));return httpx.Response(200,text=XML,headers={'content-type':'application/atom+xml'})
  with httpx.Client(transport=httpx.MockTransport(handler)) as c:r=cycle(self.db,self.cfg,c,{},now=1000)
  self.assertEqual(r['discovered'],1);self.assertEqual(len(calls),1);self.assertIn('/feeds/videos.xml',calls[0]);s=status(self.db,now=1000);self.assertEqual(s['links'][0]['training_ready'],False);self.assertEqual(s['links'][0]['verification'],'official_feed_metadata_only')
 def test_interval_and_budget_persist(self):
  with httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(200,text=XML))) as c:
   cycle(self.db,self.cfg,c,{},now=1000);self.assertEqual(cycle(self.db,self.cfg,c,{},now=1100)['status'],'waiting_interval');cycle(self.db,self.cfg,c,{},now=1300);r=cycle(self.db,self.cfg,c,{},now=1600)
  self.assertEqual(r['feed_errors'],1)
 def test_redirect_entity_channel_mismatch_rejected(self):
  for response in [httpx.Response(302,headers={'location':'http://private.invalid'}),httpx.Response(200,text='<!DOCTYPE x>'+XML),httpx.Response(200,text=XML.replace(CH,'UC'+'x'*22))]:
   with httpx.Client(transport=httpx.MockTransport(lambda _,r=response:r)) as c:r=cycle(self.db,self.cfg,c,{},now=1000,force=True)
   self.assertEqual(r['feed_errors'],1)
 def test_analysis_training_defaults_do_not_execute(self):
  with httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(200,text=XML))) as c:r=cycle(self.db,self.cfg,c,{},now=1000)
  self.assertEqual(r['link_analysis']['status'],'disabled');self.assertEqual(r['local_training']['status'],'disabled')
 def test_search_import_is_not_verified_video_or_training(self):
  n=import_candidates(self.db,[{'video_id':'qPpEpQXTQb4','title':'Index title','query':'dog barking','evidence_url':'https://www.youtube.com/watch?v=qPpEpQXTQb4'}],now=1000)
  self.assertEqual(n,1);self.assertEqual(status(self.db,now=1000)['links'][0]['verification'],'search_index_only')
  self.assertEqual(self.db.execute('SELECT count(*) FROM videos').fetchone()[0],0)

class AutomationIntegrationTests(unittest.TestCase):
 setUp=AutomationTests.setUp
 def test_config_blocks_paid_analysis_before_provider_call(self):
  cfg=AutomationConfig(enable_link_analysis=True)
  with httpx.Client(transport=httpx.MockTransport(lambda _:self.fail('Unexpected network'))) as c:r=cycle(self.db,cfg,c,{},now=1000)
  self.assertEqual(r['link_analysis']['reason'],'external_analysis_budget_approval_missing')
 def test_local_training_connector_preserves_gate(self):
  from unittest.mock import patch
  cfg=AutomationConfig(enable_local_training=True,audio_inbox='private/inbox',training_output='private/output')
  with patch('training.autolearn.scan',return_value=[{'job':'private-dog-name','status':'blocked','reason':'private-path'}]) as scan,httpx.Client() as c:
   r=cycle(self.db,cfg,c,{},now=1000)
  scan.assert_called_once_with('private/inbox','private/output');self.assertNotIn('private',json.dumps(status(self.db,now=1000)))
 def test_conditional_refresh_and_expiry(self):
  responses=iter([httpx.Response(200,text=XML,headers={'content-type':'application/atom+xml','etag':'"feed-1"'}),httpx.Response(304)])
  def handle(r):
   if 'if-none-match' in r.headers:self.assertEqual(r.headers['if-none-match'],'"feed-1"')
   return next(responses)
  with httpx.Client(transport=httpx.MockTransport(handle)) as c:
   cycle(self.db,self.cfg,c,{},now=1000);cycle(self.db,self.cfg,c,{},now=1400)
  self.assertEqual(self.db.execute('SELECT last_seen FROM research_links').fetchone()[0],1400)
  self.assertEqual(status(self.db,now=1400+8*86400)['links'],[])
 def test_invalid_xml_and_channel_fail_independently(self):
  for raw in ['<!DOCTYPE x>'+XML,XML.replace(CH,'UC'+'x'*22)]:
   cfg=AutomationConfig(channels=[CH],daily_feed_requests=20)
   with httpx.Client(transport=httpx.MockTransport(lambda _,body=raw:httpx.Response(200,text=body,headers={'content-type':'application/atom+xml'}))) as c:r=cycle(self.db,cfg,c,{},now=1000,force=True)
   self.assertEqual(r['feed_errors'],1);self.assertEqual(status(self.db,now=1000)['links'],[])
 def test_expired_metadata_requires_full_feed_not_stale_304(self):
  def handler(r):
   self.assertNotIn('if-none-match',r.headers)
   return httpx.Response(200,text=XML,headers={'content-type':'application/atom+xml','etag':'"same"'})
  with httpx.Client(transport=httpx.MockTransport(handler)) as c:
   cycle(self.db,self.cfg,c,{},now=1000);r=cycle(self.db,self.cfg,c,{},now=1000+8*86400)
  self.assertEqual(r['discovered'],1)
