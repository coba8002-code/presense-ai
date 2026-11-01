import copy,json,unittest
from pathlib import Path
from evaluation.video_contract import validate_contract
from evaluation.event_evaluation import evaluate, compare, reference_digest

class EventEvaluationTests(unittest.TestCase):
 def setUp(self):
  self.base=json.loads(Path('docs/examples/video-evaluation/reference.synthetic.json').read_text());self.registry=Path('docs/examples/video-evaluation/registry.synthetic.json')
  self.row=next(r for r in self.base['records'] if r['split']=='validation')
  self.ref={'parent_sha256':validate_contract(self.base,self.registry)['contract_sha256'],'synthetic':True,'locked_at':self.base['locked_at'],'split':'validation','clips':[{'clip_id':self.row['clip_id'],'known':True,'reviewers':['blind-human-a'],'events':[{'label':'Bark','start':self.row['start_seconds'],'end':self.row['end_seconds'],'animal_id':None}]}]}
  self.run={'reference_sha256':reference_digest(self.ref),'synthetic':True,'mode':'audio','model':'fixture','revision':'test','clips':[{'clip_id':self.row['clip_id'],'sha256':self.row['sha256'],'abstained':False,'events':copy.deepcopy(self.ref['clips'][0]['events']),'latency_seconds':1.0}]}
 def ev(self,run=None):return evaluate(self.base,self.registry,self.ref,run or self.run)
 def test_perfect_is_not_real_accuracy(self):
  r=self.ev();self.assertEqual(r['per_class']['Bark']['f1'],1);self.assertFalse(r['real_behavior_accuracy_established']);self.assertEqual(r['speaker_identity_verified'],0)
 def test_missing_is_abstention_and_false_negatives(self):
  r=self.ev({**self.run,'clips':[]});self.assertEqual(r['coverage'],0);self.assertEqual(r['per_class']['Bark']['fn'],1)
 def test_wrong_label_and_duplicates_are_false_positives(self):
  r=copy.deepcopy(self.run);r['clips'][0]['events'].append(copy.deepcopy(r['clips'][0]['events'][0]));self.assertEqual(self.ev(r)['per_class']['Bark']['fp'],1)
  r['clips'][0]['events'][0]['label']='Howl';self.assertGreater(self.ev(r)['false_positives_per_hour'],0)
 def test_bounds_and_binding(self):
  for mutate in (lambda r:r.update(reference_sha256='0'*64),lambda r:r.update(synthetic=False),lambda r:r['clips'][0].update(sha256='0'*64),lambda r:r['clips'][0]['events'][0].update(end=999.),lambda r:r['clips'][0].update(abstained=True)):
   r=copy.deepcopy(self.run);mutate(r)
   with self.assertRaises(ValueError):self.ev(r)
 def test_compare_same_reference_three_modes(self):
  runs=[{**self.run,'mode':m} for m in ['audio','video','fused']];self.assertEqual(set(compare(self.base,self.registry,self.ref,runs)),{'audio','video','fused'})
  with self.assertRaises(ValueError):compare(self.base,self.registry,self.ref,runs[:2])
 def test_reference_mutation_and_unknown(self):
  self.ref['clips'][0]['known']=False
  self.ref['clips'][0]['events']=[]
  with self.assertRaises(ValueError):self.ev()
  self.run['reference_sha256']=reference_digest(self.ref)
  r=self.ev();self.assertIsNone(r['false_positives_per_hour']);self.assertEqual(r['unknown_windows'],1)

 def test_presence_calibration_and_identity_errors(self):
  from training.pretrained_audio import DOG_LABELS
  self.run['clips'][0]['presence_probabilities']={l:float(l=='Bark') for l in DOG_LABELS}
  self.assertEqual(self.ev()['presence_brier_score'],0)
  self.ref['clips'][0]['events'][0]['animal_id']=self.row['animal_id']
  self.run['reference_sha256']=reference_digest(self.ref)
  self.run['clips'][0]['events'][0]['animal_id']='wrong-dog'
  self.assertEqual(self.ev()['speaker_identity_errors'],1)
  self.run['clips'][0]['presence_probabilities']['Bark']=float('nan')
  with self.assertRaises(ValueError):self.ev()

 def test_event_matching_uses_maximum_pairs_not_greedy(self):
  from evaluation.event_evaluation import Event,matching
  make=lambda a,b:Event(label='Bark',start=float(a),end=float(b))
  self.assertEqual(len(matching([make(0,2),make(1,3)],[make(.5,2.5),make(0,1.5)])),2)
