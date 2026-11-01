import unittest
import numpy as np
from training.audio_timeline import analyze_windows, pet_baseline
class TimelineTests(unittest.TestCase):
 def test_window_times_and_no_hard_events(self):
  calls=[]
  def score(signal,digest):calls.append(len(signal));return {'decision':'abstain','dog_event_scores':[{'label':'Bark','score':.8}]}
  r=analyze_windows(np.zeros(40000),score,offset=1.,video_duration=4.)
  self.assertEqual([w['start'] for w in r['windows']],[1.,1.5,2.,2.5]);self.assertEqual(r['events'],[]);self.assertEqual(calls,[16000]*4)
 def test_reject_bounds_and_nonfinite_before_model(self):
  for kw in ({'offset':-1.},{'video_duration':1.},{'offset':float('nan')}):
   with self.assertRaises(ValueError):analyze_windows(np.zeros(32000),lambda *_:self.fail(),**kw)
 def test_no_silent_trailing_window(self):
  r=analyze_windows(np.zeros(18000),lambda *_:{'decision':'abstain','dog_event_scores':[]})
  self.assertEqual(r['windows'][-1]['end'],1.125)
 def test_baseline_rejects_other_dogs_and_unreviewed_feedback(self):
  history=[{'dog_id':'dog-a','day':f'2026-10-{i+1:02d}','duration':60.,'count':2,'source':'measured','model_revision':'v1'} for i in range(5)]
  history.append({'dog_id':'dog-a','day':'2026-10-06','duration':60.,'count':500,'source':'guardian_feedback','model_revision':'v1'})
  r=pet_baseline(history,dog_id='dog-a',model_revision='v1',current_count=3,current_duration=60.)
  self.assertEqual(r['baseline_per_minute'],2);self.assertEqual(r['delta_per_minute'],1);self.assertFalse(r['training_eligible']);self.assertEqual(r['excluded'],1)
  self.assertTrue(pet_baseline(history[:2],dog_id='dog-a',model_revision='v1',current_count=3,current_duration=60.)['abstained'])
