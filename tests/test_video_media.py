import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import test_video_review as fixtures
from training.video_media import validate_media, inspect_video


class VideoMediaTests(unittest.TestCase):
    setUp=fixtures.VideoReviewTests.setUp
    records=fixtures.VideoReviewTests.records

    def bindings(self):
        self.reviews=self.records()
        self.policy.update(media_acquisition_allowed=True)
        self.registry.write_text(json.dumps({'licensed':self.policy}))
        rows=[]
        for i,color in enumerate(['red','green','blue','yellow','white']):
            path=self.root/f'{i}.mp4'
            subprocess.run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i',
                f'color=c={color}:s=32x32:r=5:d=5','-c:v','mpeg4','-threads','1','-y',str(path)],
                check=True,timeout=15,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            rows.append(dict(source_id=f'clip{i:07d}',path=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_start_seconds=0.,
                acquisition_evidence='owned-fixture',alignment_reviewer='expert',alignment_evidence='source checked',
                alignment_reviewed_at=1001))
        return rows

    def validate(self,rows):
        return validate_media(self.db,self.cfg,self.reviews,self.registry,rows,self.root,now=1002)

    def test_real_decode_and_annotation_alignment(self):
        rows=self.bindings();result=self.validate(rows)
        self.assertEqual(result['status'],'media_validated_model_pending')
        self.assertEqual(len(result['media']),5)
        self.assertEqual(result['records'][0]['local_start_seconds'],2)
        self.assertEqual(result['records'][0]['local_end_seconds'],4)
        self.assertFalse(result['training_ready'])
        self.assertGreater(result['media'][0]['decoded_frames'],0)

    def test_trimmed_media_offsets(self):
        rows=self.bindings()
        for row in rows: row['source_start_seconds']=2.
        result=self.validate(rows)
        self.assertEqual(result['records'][0]['local_start_seconds'],0)
        self.assertEqual(result['records'][0]['local_end_seconds'],2)

    def test_out_of_range_offset_and_nonfinite_rejected(self):
        rows=self.bindings()
        for offset in [3.,float('nan'),float('inf')]:
            changed=copy.deepcopy(rows);changed[0]['source_start_seconds']=offset
            with self.subTest(offset=offset),self.assertRaises(ValueError):self.validate(changed)

    def test_tampered_media_rejected(self):
        rows=self.bindings();(self.root/'0.mp4').write_bytes(b'changed')
        with self.assertRaises(ValueError):self.validate(rows)

    def test_duplicate_content_across_sources_rejected(self):
        rows=self.bindings();rows[-1]['path']=rows[0]['path'];rows[-1]['sha256']=rows[0]['sha256']
        with self.assertRaises(ValueError):self.validate(rows)

    def test_paths_and_missing_binding_rejected(self):
        rows=self.bindings()
        for path in ['../outside.mp4','https://example.com/video.mp4','/tmp/outside.mp4']:
            changed=copy.deepcopy(rows);changed[0]['path']=path
            with self.subTest(path=path),self.assertRaises(ValueError):self.validate(changed)
        with self.assertRaises(ValueError):self.validate(rows[:-1])
        with self.assertRaises(ValueError):self.validate(rows+[rows[0]])

    def test_rights_checked_before_media_decode(self):
        rows=self.bindings();self.policy['media_acquisition_allowed']=False
        self.registry.write_text(json.dumps({'licensed':self.policy}))
        with patch('training.video_media.inspect_video',side_effect=AssertionError('decode')):
            with self.assertRaises(ValueError):self.validate(rows)

    def test_malformed_video_rejected(self):
        path=self.root/'broken.mp4';path.write_bytes(b'not a video')
        with self.assertRaises(ValueError):inspect_video(path)

    def test_symlink_escape_and_source_duration_rejected(self):
        rows=self.bindings()
        with self.tmp.__class__() as outside:
            target=Path(outside)/'external.mp4';target.write_bytes((self.root/'0.mp4').read_bytes())
            (self.root/'link.mp4').symlink_to(target)
            changed=copy.deepcopy(rows);changed[0]['path']='link.mp4'
            with self.assertRaises(ValueError):self.validate(changed)
        self.db.execute('UPDATE videos SET duration=4')
        with self.assertRaises(ValueError):self.validate(rows)

    def test_decode_timeout_and_mutation_fail_closed(self):
        rows=self.bindings()
        with patch('training.video_media.subprocess.run',side_effect=subprocess.TimeoutExpired('ffprobe',15)):
            with self.assertRaises(ValueError):inspect_video(self.root/'0.mp4')
        original=inspect_video
        def mutate(path):
            result=original(path)
            (self.root/'0.mp4').write_bytes(b'changed while decoding')
            return result
        with patch('training.video_media.inspect_video',side_effect=mutate):
            with self.assertRaises(ValueError):self.validate(rows)

    def test_cli_receipt_with_real_decode(self):
        import sys
        import time
        rows=self.bindings();now=int(time.time())
        self.db.execute('UPDATE videos SET analyzed=?,verified=?',(now-2,now-2));self.db.commit()
        from training.video_review import proposals
        current=proposals(self.db,self.cfg,now=now)
        index={(p['source_id'],p['observation']['text']):p['proposal_id'] for p in current}
        for review in self.reviews:
            source='clip'+review['animal_id'].split('-')[-1].zfill(7)
            review['proposal_id']=index[source,review['label']];review['reviewed_at']=now-1
        for row in rows:row['alignment_reviewed_at']=now-1
        for name,value in [('reviews',self.reviews),('bindings',rows),('config',self.cfg.model_dump())]:
            (self.root/f'{name}.json').write_text(json.dumps(value))
        proc=subprocess.run([sys.executable,'-m','training.video_media','--db',str(self.root/'db'),
            '--config',str(self.root/'config.json'),'--reviews',str(self.root/'reviews.json'),
            '--registry',str(self.registry),'--bindings',str(self.root/'bindings.json'),'--media-root',str(self.root)],
            capture_output=True,text=True,timeout=30)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['counts']['test'],2)
