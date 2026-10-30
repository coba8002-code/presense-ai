import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evaluation.video_contract import validate_contract

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'docs/examples/video-evaluation'


class VideoContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = self.root / 'registry.json'
        self.registry.write_text((EXAMPLES/'registry.synthetic.json').read_text())
        self.document = json.loads((EXAMPLES/'reference.synthetic.json').read_text())

    def validate(self, document=None, **kwargs):
        return validate_contract(self.document if document is None else document, self.registry, now=2000, **kwargs)

    def test_lock_digest_and_honest_scope(self):
        a=self.validate();b=self.validate(copy.deepcopy(self.document))
        self.assertEqual(a,b);self.assertFalse(a['evaluation_ready']);self.assertTrue(a['synthetic'])
        self.assertFalse(a['local_hashes_verified']);self.assertEqual(a['double_reviewed'],2)
        self.assertEqual(a['adjudicated'],1)
        changed=copy.deepcopy(self.document);changed['records'][0]['subject_reference']='different target'
        self.assertNotEqual(a['contract_sha256'],self.validate(changed)['contract_sha256'])

    def test_each_cross_split_identity_leak_is_rejected(self):
        for key in ['animal_id','household_id','session_id','source_id','sha256']:
            with self.subTest(key=key):
                changed=copy.deepcopy(self.document)
                changed['records'][3][key]=changed['records'][0][key]
                with self.assertRaises(ValueError):self.validate(changed)

    def test_temporal_and_duplicate_boundaries(self):
        for field,value in [('start_seconds',float('nan')),('end_seconds',11.),('end_seconds',0.),('duration_seconds',float('inf')),('path','../private.mp4'),('path','C:\\private.mp4'),('species','cat'),('household_id','unknown')]:
            with self.subTest(field=field,value=value):
                changed=copy.deepcopy(self.document);changed['records'][0][field]=value
                with self.assertRaises(ValueError):self.validate(changed)
        row=copy.deepcopy(self.document['records'][0]);row['clip_id']='different-interval'
        self.document['records'].append(row)
        with self.assertRaisesRegex(ValueError,'Overlapping'):self.validate()
        row['start_seconds']=1.;row['end_seconds']=2.
        self.validate()  # Adjacent half-open intervals are permitted.
        row['clip_id']=self.document['records'][0]['clip_id']
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.validate()

    def test_blind_reviews_lock_and_adjudication(self):
        changes=[lambda d:d['records'][0]['reviews'][0].update(model_output_seen=True),
            lambda d:d['records'][0]['reviews'][0].update(model_output_seen=0),
            lambda d:d.update(locked_at=3000),
            lambda d:d['records'][0]['reviews'][0].update(reviewed_at=1001),
            lambda d:d['records'][1].update(adjudication=None),
            lambda d:d['records'][0]['reviews'][1].update(reviewer=d['records'][0]['reviews'][0]['reviewer']),
            lambda d:d['records'][4].update(unknown_reason=None),
            lambda d:d['records'][0].update(unknown_reason='occluded'),
            lambda d:d['records'][0].update(prediction='standing')]
        for mutate in changes:
            with self.subTest(change=mutate):
                changed=copy.deepcopy(self.document);mutate(changed)
                with self.assertRaises(ValueError):self.validate(changed)

    def test_policy_and_provenance_cannot_be_bypassed(self):
        policy=json.loads(self.registry.read_text())
        for key,value in [('commercial_allowed',False),('media_acquisition_allowed',False),('synthetic',False),('status','unknown')]:
            with self.subTest(key=key):
                changed=copy.deepcopy(policy);changed['synthetic-contract-example'][key]=value
                self.registry.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):self.validate()

    def test_optional_hash_verification_does_not_claim_decoding(self):
        for row in self.document['records']:
            path=self.root/row['path'];path.parent.mkdir(exist_ok=True)
            path.write_bytes(row['clip_id'].encode());row['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        result=self.validate(media_root=self.root)
        self.assertTrue(result['local_hashes_verified']);self.assertFalse(result['evaluation_ready'])
        (self.root/self.document['records'][0]['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.validate(media_root=self.root)

    def test_cli_creates_summary_without_revealing_reference_records(self):
        output=self.root/'summary.json'
        cmd=[sys.executable,'-m','evaluation.video_contract','--manifest',str(EXAMPLES/'reference.synthetic.json'),'--registry',str(self.registry),'--output',str(output)]
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertEqual(r.returncode,0,r.stderr);self.assertNotIn('records',json.loads(output.read_text()))
        self.assertNotEqual(subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=10).returncode,0)
        private=self.root/'private.json';changed=copy.deepcopy(self.document)
        changed['records'][0]['prediction']='private-marker-should-not-appear'
        private.write_text(json.dumps(changed));cmd[4]=str(private);cmd[-1]=str(self.root/'new-summary.json')
        failed=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertEqual(failed.returncode,2);self.assertNotIn('private-marker',failed.stderr)


if __name__=='__main__':unittest.main()
