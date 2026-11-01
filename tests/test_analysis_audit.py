import copy,hashlib,json,unittest
from pathlib import Path
from evaluation.event_evaluation import reference_digest
from evaluation.video_contract import validate_contract
from evaluation.analysis_audit import audit_run, review_explanations, run_digest
class AuditTests(unittest.TestCase):
 def setUp(self):
  self.base=json.loads(Path('docs/examples/video-evaluation/reference.synthetic.json').read_text());self.registry=Path('docs/examples/video-evaluation/registry.synthetic.json')
  self.ref=json.loads(Path('docs/examples/video-evaluation/events.synthetic.json').read_text());self.run=json.loads(Path('docs/examples/video-evaluation/event-runs.synthetic.json').read_text())[0]
 def test_small_group_does_not_invent_confidence_interval(self):
  r=audit_run(self.base,self.registry,self.ref,self.run,repetitions=100)
  self.assertEqual(r['status'],'insufficient_independent_households');self.assertIsNone(r['micro_f1_ci95']);self.assertFalse(r['real_behavior_accuracy_established'])
 def test_failed_windows_and_missing(self):
  self.run['clips']=[];r=audit_run(self.base,self.registry,self.ref,self.run,repetitions=100)
  self.assertEqual(r['failure_cases'][0]['kind'],'missing_or_abstained');self.assertFalse(r['training_eligible'])
 def test_same_seed_reproducible_and_wrong_binding_rejected(self):
  row=next(x for x in self.base['records'] if x['split']=='validation')
  for i in range(5):
   x=copy.deepcopy(row)
   for key in ['clip_id','animal_id','household_id','session_id','source_id']:x[key]+='-'+str(i)
   x['sha256']=hashlib.sha256(str(i).encode()).hexdigest();self.base['records'].append(x)
   rr=copy.deepcopy(self.ref['clips'][0]);rr['clip_id']=x['clip_id'];self.ref['clips'].append(rr)
   pp=copy.deepcopy(self.run['clips'][0]);pp['clip_id']=x['clip_id'];pp['sha256']=x['sha256'];self.run['clips'].append(pp)
  self.ref['parent_sha256']=validate_contract(self.base,self.registry)['contract_sha256'];self.run['reference_sha256']=reference_digest(self.ref)
  a=audit_run(self.base,self.registry,self.ref,self.run,repetitions=100,seed=7);b=audit_run(self.base,self.registry,self.ref,self.run,repetitions=100,seed=7)
  self.assertEqual(a,b);self.assertEqual(a['micro_f1_ci95'],[1.,1.]);self.assertEqual(a['households'],6)
  self.run['reference_sha256']='0'*64
  with self.assertRaises(ValueError):audit_run(self.base,self.registry,self.ref,self.run,repetitions=100)
 def test_review_requires_binding_two_reviewers_and_no_auto_training(self):
  clip=self.run['clips'][0]['clip_id']
  digest=hashlib.sha256(b'fixture explanation').hexdigest()
  reviews=[{'explanation_sha256':digest,'clip_id':clip,'reviewer':name,'model_identity_hidden':True,'grounded':True,'causal_overclaim':False,'emotion_intent_overclaim':False,'useful_question':True} for name in ['a','b']]
  doc={'run_sha256':run_digest(self.run),'synthetic':True,'explanations':[{'clip_id':clip,'text':'fixture explanation'}],'reviews':reviews}
  r=review_explanations(self.run,doc);self.assertEqual(r['double_reviewed_windows'],1);self.assertFalse(r['training_eligible'])
  reviews[1]['causal_overclaim']=True;r=review_explanations(self.run,doc);self.assertEqual(r['needs_adjudication'],1)
  reviews[1]['explanation_sha256']='0'*64
  with self.assertRaises(ValueError):review_explanations(self.run,doc)
  reviews[1]['explanation_sha256']=digest
  reviews[1]['model_identity_hidden']=1
  with self.assertRaises(ValueError):review_explanations(self.run,doc)
  reviews[1]['model_identity_hidden']=True
  reviews[1]['reviewer']='a'
  with self.assertRaises(ValueError):review_explanations(self.run,doc)
 def test_bounds_and_unbound_review_rejected(self):
  for n in [0,99,2001,True]:
   with self.assertRaises(ValueError):audit_run(self.base,self.registry,self.ref,self.run,repetitions=n)
  with self.assertRaises(ValueError):review_explanations(self.run,{'run_sha256':'0'*64,'synthetic':True,'explanations':[],'reviews':[]})
