import unittest
import numpy as np
from training.dog_pose import decode_simcc,AP10K_NAMES
class DogPoseTests(unittest.TestCase):
 def test_animal_mapping_and_crop_coordinates(self):
  x=np.zeros((17,512));y=np.zeros((17,512));x[:,256]=.8;y[:,128]=.6
  p=decode_simcc(x,y,(-10.,0.,90.,100.),100,100)
  self.assertEqual(set(p),set(AP10K_NAMES));self.assertAlmostEqual(p['neck']['x'],40.);self.assertAlmostEqual(p['tail_root']['y'],25.)
  self.assertAlmostEqual(p['neck']['confidence'],.7)
 def test_outside_crop_is_not_visible(self):
  x=np.zeros((17,512));y=np.zeros((17,512));x[:,0]=1;y[:,0]=1
  p=decode_simcc(x,y,(-20.,-20.,80.,80.),100,100);self.assertEqual(p['nose']['confidence'],0)
 def test_invalid_outputs_and_crop_rejected(self):
  for x in (np.zeros((16,512)),np.full((17,512),np.nan)):
   with self.assertRaises(ValueError):decode_simcc(x,np.zeros((17,512)),(0.,0.,100.,100.),100,100)
