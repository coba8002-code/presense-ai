import tempfile
from pathlib import Path
import unittest
import wave
import numpy as np
from training.pretrained_audio import read_wav, dog_scores, DOG_LABELS


class PretrainedAudioTests(unittest.TestCase):
    def test_pcm_stereo_downmix_and_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'test.wav'
            with wave.open(str(p), 'wb') as w:
                w.setnchannels(2); w.setsampwidth(2); w.setframerate(16000)
                w.writeframes(np.tile(np.array([1000, -1000], dtype='<i2'), 16000).tobytes())
            signal, digest = read_wav(p)
            self.assertEqual(signal.shape, (16000,))
            self.assertTrue(np.all(signal == 0))
            self.assertEqual(len(digest), 64)
            p.write_bytes(p.read_bytes()[:-5])
            with self.assertRaises(ValueError): read_wav(p)

    def test_wrong_rate_and_invalid_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'test.wav'
            p.write_bytes(b'invalid')
            with self.assertRaises(ValueError): read_wav(p)
            with wave.open(str(p), 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
                w.writeframes(b'\0'*16000)
            with self.assertRaises(ValueError): read_wav(p)

    def test_mapping_uses_names_and_preserves_multilabel_scores(self):
        labels = {i: v for i, v in enumerate(reversed(DOG_LABELS))}
        labels[len(labels)] = 'Whimper'  # Human whimper is not dog whimper.
        logits = np.full(len(labels), 2.)
        result = dog_scores(logits, labels)
        self.assertEqual(set(x['label'] for x in result), set(DOG_LABELS))
        self.assertTrue(all(x['score'] > .8 for x in result))
        self.assertGreater(sum(x['score'] for x in result), 1.)

    def test_missing_or_nonfinite_model_output_rejected(self):
        with self.assertRaises(ValueError): dog_scores(np.zeros(1), {0:'Bark'})
        with self.assertRaises(ValueError): dog_scores(np.full(7, np.nan), dict(enumerate(DOG_LABELS)))


class AudioIsolationTests(unittest.TestCase):
    def test_quality_does_not_import_web_or_schema_dependencies(self):
        import subprocess, sys
        code = """
import builtins
original=builtins.__import__
def isolated(name,*args,**kwargs):
    if name.split('.')[0] in {'backend','pydantic','httpx','fastapi'}:
        raise ImportError('Forbidden audio dependency: '+name)
    return original(name,*args,**kwargs)
builtins.__import__=isolated
from training.audio_quality import audio_quality
import numpy as np
assert audio_quality(np.zeros(16000))['warnings']==['near_silence']
"""
        subprocess.run([sys.executable,'-c',code],check=True,capture_output=True)
