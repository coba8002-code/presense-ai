import copy,json,unittest
from pathlib import Path
from evaluation.video_contract import validate_contract
from evaluation.video_predictions import score

class PredictionTests(unittest.TestCase):
    def setUp(self):
        self.doc=json.loads(Path('docs/examples/video-evaluation/reference.synthetic.json').read_text())
        self.registry=Path('docs/examples/video-evaluation/registry.synthetic.json')
        check=validate_contract(self.doc,self.registry)
        self.run={'contract_sha256':check['contract_sha256'],'synthetic':True,'split':'validation','model':'synthetic-fixture','revision':'fixture-v1','records':[]}
        for row in self.doc['records']:
            if row['split']=='validation':self.run['records'].append({k:row[k] for k in ('clip_id','sha256','start_seconds','end_seconds')}|{'label':row['label'] if row['label']!='unknown' else None,'latency_seconds':1.0})
    def test_exact_predictions_and_missing_abstentions(self):
        good=score(self.doc,self.registry,self.run)
        self.assertEqual(good['accuracy_including_abstention'],1.0);self.assertEqual(good['known_coverage'],1.0)
        self.assertFalse(good['real_behavior_accuracy_established'])
        missing=score(self.doc,self.registry,{**self.run,'records':[]})
        self.assertEqual(missing['known_coverage'],0);self.assertEqual(missing['missing_predictions'],missing['count'])
        self.assertIsNone(missing['selective_known_accuracy']);self.assertIsNone(missing['latency_p95_seconds'])
    def test_duplicate_hash_time_and_contract_mismatch(self):
        for key,value in [('sha256','0'*64),('start_seconds',0.01),('clip_id','unknown'),('latency_seconds',float('nan'))]:
            bad=copy.deepcopy(self.run);bad['records'][0][key]=value
            with self.assertRaises(ValueError):score(self.doc,self.registry,bad)
        for key,value in [('contract_sha256','0'*64),('synthetic',False)]:
            with self.assertRaises(ValueError):score(self.doc,self.registry,{**self.run,key:value})
        bad=copy.deepcopy(self.run);bad['records'].append(bad['records'][0])
        with self.assertRaises(ValueError):score(self.doc,self.registry,bad)

    def test_unknown_is_separate_and_wrong_known_label_is_not_correct(self):
        wrong=copy.deepcopy(self.run);wrong['records'][0]['label']='lying'
        result=score(self.doc,self.registry,wrong)
        self.assertEqual(result['accuracy_including_abstention'],0)
        self.assertEqual(result['confusion_matrix'][3][2],1)
        unknown=score(self.doc,self.registry,{**self.run,'split':'test','records':[]})
        self.assertEqual(unknown['unknown_count'],1)
        self.assertIsNone(unknown['accuracy_including_abstention'])
        self.assertEqual(unknown['unknown_abstention_rate'],1)
