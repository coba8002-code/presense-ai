import unittest
import numpy as np
from training.esc10_experiment import partition,experiment
class EscExperimentTests(unittest.TestCase):
 def rows(self):return [{'fold':str(f),'source_group':f'g{f}-{c}','sha256':f'{f*10+c:064x}','category':'dog' if c else 'rain','animal_id':None} for f in range(1,6) for c in range(2)]
 def test_source_and_content_leakage_rejected(self):
  rows=self.rows();rows[-1]['source_group']=rows[0]['source_group']
  with self.assertRaises(ValueError):partition(rows)
  rows=self.rows();rows[-1]['sha256']=rows[0]['sha256']
  with self.assertRaises(ValueError):partition(rows)
 def test_real_unknown_id_is_never_fabricated_or_promoted(self):
  rows=self.rows();x=np.array([[0.,0.] if r['category']!='dog' else [4.,2.] for r in rows]);r,m=experiment(rows,x)
  self.assertFalse(r['production_ready']);self.assertFalse(r['animal_disjoint_verified']);self.assertFalse(r['behavior_accuracy_verified']);self.assertEqual(m['format'],'esc10-research-only-v1');self.assertNotIn('format_version',m)
 def test_test_data_does_not_change_fit_or_hyperparameter_choice(self):
  rows=self.rows();x=np.array([[float(i%2),float(i%2)] for i in range(10)])
  a,m=experiment(rows,x);x[-2:]+=100000;b,n=experiment(rows,x)
  self.assertEqual(m,n);self.assertEqual(a['selected_penalty'],b['selected_penalty'])
 def test_partition_requires_class_coverage_and_finite_features(self):
  rows=self.rows();rows[-1]['category']='rain'
  with self.assertRaises(ValueError):partition(rows)
  with self.assertRaises(ValueError):experiment(self.rows(),np.full((10,2),float('nan')))
