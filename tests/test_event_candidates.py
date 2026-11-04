import unittest
from training.event_candidates import candidates
class CandidateTests(unittest.TestCase):
 def windows(self,scores):return [{'start':i*.5,'end':i*.5+1.,'dog_event_scores':[{'label':'Bark','score':v}],'audio_quality':{'warnings':[]}} for i,v in enumerate(scores)]
 def test_hysteresis_and_uncertain_boundaries(self):
  r=candidates(self.windows([.7,.5,.3,.8]))
  self.assertEqual(len(r['candidates']),2);self.assertEqual(r['candidates'][0]['onset_interval'],[0.,1.])
  self.assertFalse(r['validated']);self.assertEqual(r['decision'],'abstain')
 def test_low_quality_flag_is_not_noise_diagnosis(self):
  w=self.windows([.8]);w[0]['audio_quality']['warnings']=['clipping'];r=candidates(w)
  self.assertEqual(r['candidates'][0]['quality_flags'],['clipping']);self.assertEqual(r['candidates'][0]['speaker'],'unconfirmed')
 def test_invalid_scores_clock_and_policy(self):
  for w in ([{'start':2.,'end':1.,'dog_event_scores':[]}],self.windows([float('nan')]),self.windows([1.2])):
   with self.assertRaises(ValueError):candidates(w)
  with self.assertRaises(ValueError):candidates(self.windows([.9]),enter=.2,exit=.4)
 def test_empty_and_no_threshold_crossing(self):
  self.assertEqual(candidates([])['candidates'],[]);self.assertEqual(candidates(self.windows([.1,.2]))['candidates'],[])
