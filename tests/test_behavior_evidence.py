import unittest
import numpy as np
from backend.behavior_evidence import Frame, summarize, audio_quality
from backend.vlm import VisionResult


def frame(t=0.0, **kw):
    d=dict(species='dog',posture='crouching',ears='back',tail='tucked',visibility='clear',hypotheses=['possible_avoidance'],confidence=.8,abstained=False)
    d.update(kw)
    return Frame(seconds=t, observation=VisionResult(**d))

class EvidenceTests(unittest.TestCase):
    def test_needs_identity_and_temporal_evidence(self):
        self.assertTrue(summarize([frame()],same_dog_confirmed=True)['abstained'])
        self.assertTrue(summarize([frame(),frame(1.0)],same_dog_confirmed=False)['abstained'])
    def test_candidate_is_not_emotion_or_probability(self):
        r=summarize([frame(),frame(1.0)],same_dog_confirmed=True)
        self.assertEqual(r['candidates'][0]['label'],'possible_avoidance')
        self.assertEqual(r['candidates'][0]['support_seconds'],[0.0,1.0])
        self.assertIsNone(r['emotion']);self.assertIsNone(r['intent'])
        self.assertFalse(r['validated_behavior_accuracy'])
    def test_upstream_hypothesis_alone_cannot_support(self):
        r=summarize([frame(posture='standing',tail='raised',ears='forward'),frame(1.0,posture='standing',tail='raised',ears='forward')],same_dog_confirmed=True)
        self.assertEqual(r['candidates'],[])
    def test_partial_non_dog_abstained_and_conflicting_frames(self):
        for change in ({'visibility':'partial'},{'species':'cat'},{'abstained':True},{'confidence':.4}):
            r=summarize([frame(),frame(1.0,**change)],same_dog_confirmed=True)
            self.assertTrue(r['abstained'])
        r=summarize([frame(),frame(1.0,posture='standing',ears='forward',tail='raised')],same_dog_confirmed=True)
        self.assertEqual(r['candidates'],[])
    def test_order_and_window_rejected(self):
        for frames in ([frame(),frame()],[frame(1.0),frame()]):
            with self.assertRaises(ValueError):summarize(frames,same_dog_confirmed=True)
        with self.assertRaises(ValueError):frame(31.0)
    def test_silence_clipping_and_invalid_signal(self):
        self.assertIn('near_silence',audio_quality(np.zeros(16000))['warnings'])
        self.assertIn('clipping',audio_quality(np.ones(16000))['warnings'])
        for s in (np.array([np.nan]*1600),np.zeros((1600,2)),np.zeros(100)):
            with self.assertRaises(ValueError):audio_quality(s)
    def test_quality_is_not_sound_classification(self):
        r=audio_quality(np.sin(np.arange(16000)*.1)*.1)
        self.assertEqual(r['warnings'],[])
        self.assertFalse(r['species_verified']);self.assertFalse(r['thresholds_validated'])
