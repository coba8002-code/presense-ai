import tempfile
import unittest
from pathlib import Path
import hashlib
import wave
import numpy as np
from evaluation.audio_duplicates import windows, compare, decode


class DuplicateTests(unittest.TestCase):
    def signal(self):
        rng=np.random.default_rng(4)
        return rng.normal(0,.1,48000)*(1+.5*np.sin(np.arange(48000)/900))

    def item(self,name,signal,dataset='barkmeow'):
        raw=(np.clip(signal,-1,1)*32767).astype('<i2').tobytes()
        return dict(id=name,dataset=dataset,raw_sha256=name,canonical_sha256=hashlib.sha256(raw).hexdigest(),signal=np.frombuffer(raw,dtype='<i2')/32768)

    def test_exact_gain_crop_and_negative(self):
        x=self.signal()
        rows=[self.item('a',x),self.item('b',x,'esc10'),self.item('c',x[4000:36000]*.5),
              self.item('d',np.random.default_rng(8).normal(0,.1,len(x)))]
        result=compare(rows)
        self.assertIn(['a','b'],result['canonical_equal_pairs'])
        pairs={tuple(r['ids']) for r in result['similarity_candidates']}
        self.assertIn(('a','c'),pairs)
        self.assertFalse(any('d' in p for p in pairs))
        self.assertFalse(result['independence_proven'])

    def test_silence_not_similarity_evidence(self):
        self.assertEqual(len(windows(np.zeros(32000))[0]),0)
        self.assertEqual(compare([self.item('a',np.zeros(32000)),self.item('b',np.zeros(32000))])['similarity_candidates'],[])

    def test_local_decode_resample_and_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.wav'
            x=(np.sin(np.arange(44100)*.1)*10000).astype('<i2')
            with wave.open(str(p),'wb') as w:
                w.setparams((1,2,44100,0,'NONE','not compressed'));w.writeframes(x.tobytes())
            row=decode(p,hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertEqual(len(row['signal']),16000)
            with self.assertRaises(ValueError):decode(p,'0'*64)
