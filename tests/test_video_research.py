import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from knowledge.case_cards import case_cards
from knowledge.pipeline import cycle, open_db
from knowledge.research_plan import prepare, select_batch, advance_batch
from test_knowledge import config, FakeProviders

ROOT=Path(__file__).resolve().parents[1]


class VideoResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.cfg=config()
        self.db=open_db(self.root/'research.sqlite3');self.addCleanup(self.db.close)
        cycle(self.db,self.cfg,FakeProviders(),now=1000)

    def test_plan_is_diverse_but_never_claims_videos_or_grants_permissions(self):
        doc=json.loads((ROOT/'config/dog-video-sources.json').read_text())
        configs,report=prepare(doc)
        self.assertEqual(report['sources'],12);self.assertEqual(len(report['searches']),24)
        self.assertEqual(len(configs),6);self.assertEqual(report['external_calls'],0)
        self.assertEqual({r['language'] for r in report['searches']},{'ko','en'})
        for _,cfg in configs:
            self.assertFalse(cfg['policies']);self.assertIsNone(cfg['notebook']);self.assertLessEqual(len(cfg['queries']),4)
        for row in report['searches']:
            self.assertFalse(row['video_found']);self.assertFalse(row['training_ready'])
            self.assertTrue(row['search_url'].startswith('https://www.youtube.com/results?'))

    def test_plan_rejects_duplicate_and_hidden_authorization(self):
        doc=json.loads((ROOT/'config/dog-video-sources.json').read_text())
        for mutate in [lambda d:d['sources'].append(copy.deepcopy(d['sources'][0])),
            lambda d:d['sources'][0].update(verification='official_verified'),
            lambda d:d['sources'][0].update(policies={'any':'approved'}),
            lambda d:d['sources'][0].update(queries=[' '])]:
            changed=copy.deepcopy(doc);mutate(changed)
            with self.assertRaises(ValueError):prepare(changed)

    def test_case_keeps_speaker_statement_and_hypothesis_out_of_observation(self):
        data=json.loads(self.db.execute('SELECT analysis FROM videos').fetchone()[0])
        base=data['entries'][0]
        data['entries'] += [{**base,'kind':'speaker_statement','text':'Speaker offers an interpretation.'},
            {**base,'kind':'hypothesis','text':'Unverified causal hypothesis.'}]
        self.db.execute('UPDATE videos SET analysis=?',(json.dumps(data),))
        card=case_cards(self.db,self.cfg,now=1001)[0]
        self.assertEqual(len(card['entries']['observation']),1)
        self.assertEqual(len(card['entries']['speaker_statement']),1)
        self.assertEqual(len(card['entries']['hypothesis']),1)
        self.assertFalse(card['ground_truth']);self.assertFalse(card['training_ready'])
        self.assertFalse(card['speaker_identity_verified']);self.assertIsNone(card['followup_outcome'])
        self.assertIsNone(card['animal_id']);self.assertEqual(card['audio_confounds']['music'],'unknown')

    def test_revoked_stale_changed_model_and_non_dog_cards_are_withdrawn(self):
        self.assertEqual(len(case_cards(self.db,self.cfg,now=1001)),1)
        self.assertFalse(case_cards(self.db,self.cfg.model_copy(update={'policies':{}}),now=1001))
        self.assertFalse(case_cards(self.db,self.cfg,now=90000))
        self.assertFalse(case_cards(self.db,self.cfg,now=999))
        self.db.execute("UPDATE videos SET model='changed'")
        self.assertFalse(case_cards(self.db,self.cfg,now=1001))
        self.db.execute('UPDATE videos SET model=?',(self.cfg.gemini_model,))
        data=json.loads(self.db.execute('SELECT analysis FROM videos').fetchone()[0]);data['species']='cat'
        self.db.execute('UPDATE videos SET analysis=?',(json.dumps(data),))
        self.assertFalse(case_cards(self.db,self.cfg,now=1001))

    def test_invalid_timing_has_no_observation_and_analysis_changes_invalidate_case(self):
        old=case_cards(self.db,self.cfg,now=1001)[0]['case_id']
        data=json.loads(self.db.execute('SELECT analysis FROM videos').fetchone()[0])
        data['entries'][0]['text']='Changed directly observed action.'
        self.db.execute('UPDATE videos SET analysis=?',(json.dumps(data),))
        self.assertNotEqual(old,case_cards(self.db,self.cfg,now=1001)[0]['case_id'])
        data['entries'][0]['end_seconds']=30
        self.db.execute('UPDATE videos SET analysis=?',(json.dumps(data),))
        self.assertFalse(case_cards(self.db,self.cfg,now=1001))

    def test_prepare_cli_never_replaces_operator_configuration(self):
        out=self.root/'plan';command=[sys.executable,'-m','knowledge.research_plan','--output-dir',str(out)]
        r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('No videos fetched',r.stdout)
        marker=out/'operator.txt';marker.write_text('preserve')
        self.assertEqual(subprocess.run(command,cwd=ROOT,capture_output=True,timeout=10).returncode,2)
        self.assertEqual(marker.read_text(),'preserve')

    def test_rotation_preserves_permissions_and_quota_does_not_skip_batches(self):
        doc=json.loads((ROOT/'config/dog-video-sources.json').read_text())
        selected,first=select_batch(self.db,self.cfg,doc)
        self.assertEqual(selected.policies,self.cfg.policies)
        self.assertEqual(selected.daily_requests,self.cfg.daily_requests)
        self.assertEqual(selected.gemini_model,self.cfg.gemini_model)
        advance_batch(self.db,first,0)
        self.assertEqual(select_batch(self.db,self.cfg,doc)[1]['name'],first['name'])
        names=[]
        for _ in range(6):
            _,batch=select_batch(self.db,self.cfg,doc);names.append(batch['name']);advance_batch(self.db,batch,1)
        self.assertEqual(len(set(names)),6)
        self.assertEqual(select_batch(self.db,self.cfg,doc)[1]['name'],first['name'])

    def test_research_cannot_implicitly_enable_external_analysis(self):
        r=subprocess.run([sys.executable,'-m','knowledge.worker','--config',str(ROOT/'config/knowledge.example.json'),
            '--research-catalog',str(ROOT/'config/dog-video-sources.json')],cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertEqual(r.returncode,2);self.assertIn('requires --discover-only',r.stderr)

    def test_case_card_cli_uses_local_db_without_provider_credentials(self):
        now=time.time()
        self.db.execute('UPDATE videos SET verified=?,analyzed=?',(now,now));self.db.commit()
        cfgpath=self.root/'config.json';cfgpath.write_text(self.cfg.model_dump_json())
        r=subprocess.run([sys.executable,'-m','knowledge.worker','--config',str(cfgpath),
            '--db',str(self.root/'research.sqlite3'),'--case-cards'],cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertEqual(r.returncode,0,r.stderr)
        cards=json.loads(r.stdout);self.assertEqual(len(cards),1);self.assertFalse(cards[0]['training_ready'])


if __name__=='__main__':unittest.main()
