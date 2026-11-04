"""Seeded generative invariants; synthetic fixtures, not accuracy evaluation."""
import random
import unittest
import numpy as np
from training.grouping import animal_groups
from training.audio import pcm_features
from training.event_candidates import candidates


class QAProperties(unittest.TestCase):
    def test_connected_groups_match_independent_graph_reachability(self):
        rng=random.Random(20261103)
        fields=('household_id','recording_group','source_id','duplicate_group')
        for case in range(250):
            rows=[{'animal_id':f'dog-{i}'} for i in range(rng.randint(1,24))]
            for row in rows:
                for field in fields:
                    if rng.random()<.4:row[field]=str(rng.randrange(8))
            actual=animal_groups(rows)
            for row in rows:
                reachable={row['animal_id']}
                while True:
                    more={b['animal_id'] for a in rows if a['animal_id'] in reachable for b in rows if any(f in a and f in b and a[f]==b[f] for f in fields)}
                    if more<=reachable:break
                    reachable|=more
                self.assertEqual({key for key,group in actual.items() if group==actual[row['animal_id']]},reachable,case)
            rng.shuffle(rows)
            self.assertEqual(actual,animal_groups(rows),case)
            self.assertEqual(actual,animal_groups(rows+rows[:3]),case)

    def test_pcm_domain_has_finite_features_and_polarity_symmetry(self):
        rng=np.random.default_rng(20261103)
        for size in [1600,16000]+list(rng.integers(1600,16001,100)):
            samples=rng.integers(-32767,32768,int(size),dtype=np.int16)
            a=pcm_features(samples.astype('<i2').tobytes())
            b=pcm_features((-samples).astype('<i2').tobytes())
            self.assertEqual(a.shape,(34,));self.assertTrue(np.isfinite(a).all())
            np.testing.assert_allclose(a[:33],b[:33],atol=1e-12)
        for size in [0,1,3198,3199,3201,32001,32002]:
            with self.assertRaises(ValueError):pcm_features(bytes(size))

    def test_event_missing_label_does_not_bridge_observation_gap(self):
        windows=[{'start':0,'end':1,'dog_event_scores':[{'label':'Bark','score':.9}]},
                 {'start':.5,'end':1.5,'dog_event_scores':[]}]
        result=candidates(windows,exit=0)
        self.assertEqual(len(result['candidates']),1)
        self.assertEqual(result['candidates'][0]['end'],1)
        # A measured zero is different from a missing measurement.
        windows[1]['dog_event_scores']=[{'label':'Bark','score':0}]
        self.assertEqual(candidates(windows,exit=0)['candidates'][0]['end'],1.5)

    def test_event_envelopes_preserve_time_translation_and_abstention(self):
        rng=random.Random(20261103)
        for _ in range(250):
            windows=[{'start':i*.5,'end':i*.5+1,'dog_event_scores':[{'label':'Bark','score':rng.random()}]} for i in range(rng.randint(1,40))]
            original=candidates(windows)
            shifted=candidates([{**w,'start':w['start']+2,'end':w['end']+2} for w in windows])
            self.assertFalse(original['validated']);self.assertEqual(original['decision'],'abstain')
            self.assertEqual(len(original['candidates']),len(shifted['candidates']))
            for a,b in zip(original['candidates'],shifted['candidates']):
                self.assertEqual(a['peak_score'],b['peak_score'])
                self.assertEqual(a['start']+2,b['start']);self.assertEqual(a['end']+2,b['end'])
                self.assertLessEqual(a['start'],a['onset_interval'][1]);self.assertLessEqual(a['offset_interval'][0],a['end'])
