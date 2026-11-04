import unittest
import numpy as np
from training.dog2vec_adapter import extract,readiness
class Dog2vecTests(unittest.TestCase):
 def test_feature_contract_does_not_create_labels(self):
  r=extract(np.zeros(16000),lambda s:np.ones((50,768)),{'synthetic':True,'checkpoint_sha256':'0'*64})
  self.assertEqual(r['feature_dimension'],768);self.assertIsNone(r['task_prediction']);self.assertFalse(r['production_ready'])
 def test_permissions_before_feature_execution(self):
  with self.assertRaises(ValueError):extract(np.zeros(16000),lambda _:self.fail('unapproved extraction'),{'synthetic':False,'checkpoint_sha256':'0'*64})
  self.assertFalse(readiness()['automatic_checkpoint_loading']);self.assertFalse(readiness()['code_license_verified'])
 def test_bad_dimensions_and_nonfinite_rejected(self):
  for f in (np.zeros((5,10)),np.full((5,768),np.nan)):
   with self.assertRaises(ValueError):extract(np.zeros(16000),lambda s:f,{'synthetic':True,'checkpoint_sha256':'0'*64})
