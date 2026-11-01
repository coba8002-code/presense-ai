import unittest
from training.track_pose import adapt
class TrackPoseTests(unittest.TestCase):
 def doc(self,frames):return {'source_sha256':'0'*64,'source_kind':'synthetic_fixture','model':'fixture-detector','revision':'v1','width':100,'height':100,'frames':frames}
 def det(self,box=[0.,0.,20.,20.],points=None):return {'box':box,'score':.9,'keypoints':points or {}}
 def test_unique_candidate_and_pose_not_identity(self):
  p={'neck':{'x':10.,'y':10.,'confidence':.9},'tail_root':{'x':2.,'y':10.,'confidence':.9}}
  r=adapt(self.doc([{'seconds':0.,'detections':[self.det(points=p)]},{'seconds':.2,'detections':[self.det([1.,0.,21.,20.],p)]}]))
  a,b=r['frames'];self.assertEqual(a['detections'][0]['track_candidate_id'],b['detections'][0]['track_candidate_id'])
  self.assertEqual(a['detections'][0]['torso_angle_degrees'],0);self.assertFalse(r['identity_verified']);self.assertEqual(r['speaker'],'unconfirmed')
 def test_ambiguous_crossing_and_gap_do_not_preserve_identity(self):
  r=adapt(self.doc([{'seconds':0.,'detections':[self.det(),self.det()]},{'seconds':.2,'detections':[self.det()]},{'seconds':2.,'detections':[self.det()]}]))
  tracks=[f['detections'][0]['track_candidate_id'] for f in r['frames']]
  self.assertEqual(len(set(tracks)),3)
 def test_occluded_pose_and_invalid_clock_bounds(self):
  r=adapt(self.doc([{'seconds':0.,'detections':[self.det()]}]));self.assertIsNone(r['frames'][0]['detections'][0]['torso_angle_degrees'])
  for frames in ([{'seconds':0.,'detections':[self.det([0.,0.,101.,20.])]}],[{'seconds':float('nan'),'detections':[]}],[{'seconds':1.,'detections':[]},{'seconds':0.,'detections':[]}]):
   with self.assertRaises(ValueError):adapt(self.doc(frames))
