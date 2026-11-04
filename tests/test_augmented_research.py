import unittest
import numpy as np
from training.augmented_research import experiment

class AugmentedResearchTests(unittest.TestCase):
    def rows(self):return [{'fold':str(f),'source_group':f'{f}-{c}','sha256':f'h{f}-{c}','category':c} for f in range(1,6) for c in ('dog','rain')]
    def test_test_data_cannot_change_fitted_weights(self):
        rows=self.rows();x=np.arange(40,dtype=float).reshape(10,4);extra=x[:6]*.8
        _,a=experiment(rows,x,extra);x[-2:]+=1000;_,b=experiment(rows,x,extra)
        np.testing.assert_array_equal(a['weights'],b['weights']);self.assertFalse(a['production_ready'])
    def test_rejects_extra_heldout_rows(self):
        with self.assertRaises(ValueError):experiment(self.rows(),np.ones((10,4)),np.ones((10,4)))
    def test_known_source_overlap_rejected(self):
        rows=self.rows();rows[-1]['source_group']=rows[0]['source_group']
        with self.assertRaises(ValueError):experiment(rows,np.ones((10,4)),np.ones((6,4)))
