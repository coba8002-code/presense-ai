import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import test_video_media as fixtures
from training.video_review import proposals
from training.youtube_frames import export_frames, extract_frame
from training.small_vlm import load_manifest


class YouTubeFramesTests(unittest.TestCase):
    setUp = fixtures.VideoMediaTests.setUp
    records = fixtures.VideoMediaTests.records
    bindings = fixtures.VideoMediaTests.bindings

    def setup_media(self):
        bindings = self.bindings()
        for i, color in enumerate(['red','green','blue','yellow','white']):
            source = f'clip{i:07d}'
            data = json.loads(self.db.execute('SELECT analysis FROM videos WHERE id=?',(source,)).fetchone()[0])
            for n, entry in enumerate(data['entries']):
                entry.update(text=('standing','sitting')[n],start_seconds=2+n,end_seconds=3+n)
            self.db.execute('UPDATE videos SET analysis=? WHERE id=?',(json.dumps(data),source))
            subprocess.run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i',
                f"color=c={color}:s=32x32:r=10:d=5,drawbox=x=0:y=0:w=10:h=10:color=black:t=fill:enable='gte(t,3)'",
                '-c:v','mpeg4','-threads','1','-y',str(self.root/f'{i}.mp4')],check=True,timeout=15)
            bindings[i]['sha256'] = hashlib.sha256((self.root/f'{i}.mp4').read_bytes()).hexdigest()
        self.db.commit()
        self.reviews=[]
        for row in proposals(self.db,self.cfg,now=1002):
            i=int(row['source_id'][-7:])
            self.reviews.append(dict(proposal_id=row['proposal_id'],decision='approved',label=row['observation']['text'],
                animal_id=f'animal-{i}',recording_group=f'session-{i}',dataset='licensed',
                split='train' if i<3 else 'validation' if i==3 else 'test',reviewer='human',review_evidence='fixture',reviewed_at=1001))
        return bindings

    def run_export(self, bindings, output, reviews=None):
        return export_frames(self.db,self.cfg,self.reviews,self.registry,bindings,self.root,output,reviews,now=1002)

    def reviewed_frames(self, prepared):
        return [dict(candidate_id=r['candidate_id'],label='standing' if r['local_seconds']<3 else 'sitting',
                     household_id='home-'+r['animal_id'],reviewer='frame-human',review_evidence='viewed exact PNG',
                     reviewed_at=1002,frame_inspected=True) for r in prepared['candidates']]

    def test_real_video_to_review_to_trainer_manifest(self):
        bindings=self.setup_media()
        prepared=self.run_export(bindings,self.root/'prepare')
        self.assertEqual(len(prepared['candidates']),10)
        self.assertFalse((self.root/'prepare'/'frames.json').exists())
        self.assertTrue(all(r['label'] is None for r in prepared['candidates']))
        reviews=self.reviewed_frames(prepared)
        final=self.run_export(bindings,self.root/'final',reviews)
        rows,_=load_manifest(self.root/'final'/'frames.json',self.registry)
        self.assertEqual(len(rows),10)
        self.assertFalse(final['training_performed'])
        self.assertTrue(final['manifest_ready'])
        edited=copy.deepcopy(rows);edited[-1]['household_id']=edited[0]['household_id']
        (self.root/'final'/'frames.json').write_text(json.dumps(edited))
        with self.assertRaises(ValueError):load_manifest(self.root/'final'/'frames.json',self.registry)
        changed=copy.deepcopy(reviews);changed[-1]['household_id']=changed[0]['household_id']
        with self.assertRaises(ValueError):self.run_export(bindings,self.root/'leak',changed)
        self.assertFalse((self.root/'leak').exists())
        changed=copy.deepcopy(reviews);changed[0]['candidate_id']='0'*64
        with self.assertRaises(ValueError):self.run_export(bindings,self.root/'stale',changed)
        changed=copy.deepcopy(reviews);changed[0]['frame_inspected']=False
        with self.assertRaises(ValueError):self.run_export(bindings,self.root/'unseen',changed)

    def test_revocation_precedes_extraction(self):
        bindings=self.setup_media();self.policy['training_allowed']=False
        self.registry.write_text(json.dumps({'licensed':self.policy}))
        with patch('training.youtube_frames.extract_frame',side_effect=AssertionError('must not decode')):
            with self.assertRaises(ValueError):self.run_export(bindings,self.root/'revoked')
        self.assertFalse((self.root/'revoked').exists())

    def test_source_change_during_extraction_discards_output(self):
        bindings=self.setup_media(); mutated=False
        def change(source,seconds,target):
            nonlocal mutated
            extract_frame(source,seconds,target)
            if not mutated:
                (self.root/'0.mp4').write_bytes(b'changed')
                mutated=True
        with patch('training.youtube_frames.extract_frame',side_effect=change):
            with self.assertRaises(ValueError):self.run_export(bindings,self.root/'changed')
        self.assertFalse((self.root/'changed').exists())
