import io
import tarfile
import tempfile
import unittest
import wave
import struct
from pathlib import Path
from scripts.research_acquisition import extract_dogs, audio_info


class AcquisitionTests(unittest.TestCase):
    def test_float_source_and_truncation(self):
        raw = struct.pack('<f', .1)*3200
        body = b'WAVEfmt '+struct.pack('<IHHIIHH', 16, 3, 1, 16000, 64000, 4, 32)+b'data'+struct.pack('<I',len(raw))+raw
        b = b'RIFF'+struct.pack('<I',len(body))+body
        self.assertEqual(audio_info(b), (1,16000,3200,'float32'))
        with self.assertRaises(ValueError): audio_info(b[:-1])
        with self.assertRaises(ValueError): audio_info(b[:-4]+struct.pack('<f',float('nan')))

    def archive(self, root, names):
        audio = io.BytesIO()
        with wave.open(audio, 'wb') as w:
            w.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            w.writeframes(b'\0\0' * 3200)
        path = root / 'input.tar.gz'
        with tarfile.open(path, 'w:gz') as t:
            for name in names:
                info = tarfile.TarInfo(name); info.size = len(audio.getvalue())
                t.addfile(info, io.BytesIO(audio.getvalue()))
        return path

    def test_dog_only_and_no_invented_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rows = extract_dogs(self.archive(root, ['barkmeow/dog/dog_1.wav', 'barkmeow/cat/cat_1.wav']), root/'out')
            self.assertEqual(len(rows), 1)
            self.assertIsNone(rows[0]['animal_id'])
            self.assertIsNone(rows[0]['household_id'])
            self.assertFalse(rows[0]['training_approved'])
            self.assertEqual(rows[0]['duration_seconds'], .2)
            self.assertEqual(len(list((root/'out').glob('*.wav'))), 1)

    def test_traversal_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(ValueError):
                extract_dogs(self.archive(root, ['barkmeow/dog/../../escape.wav']), root/'out')
            self.assertFalse((root/'out').exists())

    def test_duplicate_names_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(ValueError):
                extract_dogs(self.archive(root, ['barkmeow/dog/dog_1.wav']*2), root/'out')

    def test_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'out').mkdir()
            with self.assertRaises(FileExistsError):
                extract_dogs(self.archive(root, ['barkmeow/dog/dog_1.wav']), root/'out')
