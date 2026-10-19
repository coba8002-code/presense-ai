import copy
import json
import tempfile
import unittest
from pathlib import Path
from test_knowledge import config, FakeProviders, VIDEO, CHANNEL
from knowledge.pipeline import open_db, cycle
from training.video_review import proposals, validate_reviews


class VideoReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.db=open_db(self.root/'db')
        self.addCleanup(self.db.close)
        self.cfg=config()
        cycle(self.db,self.cfg,FakeProviders(),now=1000)
        self.policy=dict(status='approved',training_allowed=True,commercial_allowed=True,
            video_channels=[CHANNEL],source='contract',version='1',license='owned',rights_evidence='agreement',
            consent='recorded',reviewer='owner',reviewed_at='2026-10-17')
        self.registry=self.root/'registry.json'
        self.registry.write_text(json.dumps({'licensed':self.policy}))

    def records(self):
        # Five animals with two observed actions each, independent source sessions.
        base=dict(self.db.execute('SELECT * FROM videos').fetchone())
        self.db.execute('DELETE FROM videos')
        for i in range(5):
            data=json.loads(base['analysis'])
            data['entries']=[dict(data['entries'][0],text=label) for label in ('walking','sitting')]
            self.db.execute('INSERT INTO videos(id,channel_id,title,duration,verified,created,analysis,analyzed,model) VALUES(?,?,?,?,?,?,?,?,?)',
                (f'clip{i:07d}',CHANNEL,'fixture',20,1000,1000,json.dumps(data),1000,base['model']))
        self.db.commit()
        rows=proposals(self.db,self.cfg,now=1001)
        reviews=[]
        for row in rows:
            i=int(row['source_id'][-7:])
            reviews.append(dict(proposal_id=row['proposal_id'],decision='approved',
                label=row['observation']['text'],animal_id=f'animal-{i}',recording_group=f'session-{i}',
                dataset='licensed',split=('train' if i<3 else 'validation' if i==3 else 'test'),
                reviewer='expert-1',review_evidence='review-log-1',reviewed_at=1001))
        return reviews

    def test_export_only_observations_and_no_automatic_label(self):
        row=proposals(self.db,self.cfg,now=1001)[0]
        self.assertIn('&t=2s',row['citation'])
        self.assertIsNone(row['suggested_label'])
        self.assertFalse(row['training_ready'])
        self.cfg.policies.clear()
        self.assertEqual(proposals(self.db,self.cfg,now=1001),[])

    def test_valid_export_is_annotation_only(self):
        reviews=self.records()
        result=validate_reviews(self.db,self.cfg,reviews,self.registry,now=1002)
        self.assertEqual(result['counts'],dict(train=6,validation=2,test=2))
        self.assertFalse(result['training_ready'])
        self.assertEqual(result['status'],'annotations_validated_media_pending')

    def test_hypotheses_and_expired_analysis_not_exported(self):
        data=json.loads(self.db.execute('SELECT analysis FROM videos').fetchone()[0])
        data['entries'][0]['kind']='hypothesis'
        self.db.execute('UPDATE videos SET analysis=?',(json.dumps(data),))
        self.assertEqual(proposals(self.db,self.cfg,now=1001),[])
        self.assertEqual(proposals(self.db,self.cfg,now=90000),[])

    def test_stale_proposal_rejected(self):
        reviews=self.records()
        self.db.execute('UPDATE videos SET model=?',('new-model',))
        with self.assertRaises(ValueError):
            validate_reviews(self.db,self.cfg,reviews,self.registry,now=1002)

    def test_unreviewed_or_emotion_label_rejected(self):
        reviews=self.records()
        for key,value in [('decision','pending'),('label','angry'),('animal_id','unknown'),('reviewer',' '),('reviewed_at',99999)]:
            changed=copy.deepcopy(reviews);changed[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_reviews(self.db,self.cfg,changed,self.registry,now=1002)

    def test_rights_revocation_and_duplicate_review_rejected(self):
        reviews=self.records()
        with self.assertRaises(ValueError):
            validate_reviews(self.db,self.cfg,reviews+[reviews[0]],self.registry,now=1002)
        self.policy['training_allowed']=False
        self.registry.write_text(json.dumps({'licensed':self.policy}))
        with self.assertRaises(ValueError):
            validate_reviews(self.db,self.cfg,reviews,self.registry,now=1002)

    def test_animal_session_and_source_leakage_rejected(self):
        reviews=self.records()
        for key in ['animal_id','recording_group']:
            changed=copy.deepcopy(reviews)
            changed[-1][key]=changed[0][key]
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_reviews(self.db,self.cfg,changed,self.registry,now=1002)
        reviews[0]['split']='test'
        with self.assertRaises(ValueError):
            validate_reviews(self.db,self.cfg,reviews,self.registry,now=1002)

    def test_channel_scope_required(self):
        reviews=self.records()
        self.policy['video_channels']='prefix'+CHANNEL+'suffix'
        self.registry.write_text(json.dumps({'licensed':self.policy}))
        with self.assertRaises(ValueError):
            validate_reviews(self.db,self.cfg,reviews,self.registry,now=1002)

    def test_changed_analysis_invalidates_review(self):
        reviews=self.records()
        self.db.execute('UPDATE videos SET analyzed=1001')
        with self.assertRaises(ValueError):
            validate_reviews(self.db,self.cfg,reviews,self.registry,now=1002)

    def test_cli_exports_without_credentials_and_rejects_invalid_review(self):
        import subprocess
        import sys
        import time
        cfgpath=self.root/'config.json';cfgpath.write_text(self.cfg.model_dump_json())
        now=time.time()
        self.db.execute('UPDATE videos SET analyzed=?,verified=?',(now,now));self.db.commit()
        command=[sys.executable,'-m','training.video_review','--db',str(self.root/'db'),'--config',str(cfgpath)]
        proc=subprocess.run(command,capture_output=True,text=True,timeout=10)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(len(json.loads(proc.stdout)),1)
        path=self.root/'bad.json';path.write_text('[{"secret":"do not echo"}]')
        proc=subprocess.run(command+['--reviews',str(path)],capture_output=True,text=True,timeout=10)
        self.assertEqual(proc.returncode,2)
        self.assertNotIn('secret',proc.stderr)
