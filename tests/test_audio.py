import json
from pathlib import Path
import tempfile
import unittest
import wave
import numpy as np
from training.audio import features
from training.data import load_records, split_records
from training.run import run
from evaluation.metrics import classification_metrics
from evaluation.evaluate import evaluate


def fixture(root, species='dog'):
    policy = dict(status='approved', training_allowed=True, commercial_allowed=True,
                  source='generated sine waves', version='1', license='CC0-1.0',
                  rights_evidence='generated in test', consent='no personal data',
                  reviewer='test fixture', reviewed_at='2026-10-17', synthetic=True)
    (root / 'registry.json').write_text(json.dumps({'synthetic': policy}))
    records = []
    for animal in range(9):
        for label, frequency in [('low', 250), ('high', 2000)]:
            filename = f'{animal}-{label}.wav'
            samples = .3 * np.sin(2 * np.pi * (frequency + animal) * np.arange(8000) / 16000)
            with wave.open(str(root / filename), 'wb') as stream:
                stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                stream.writeframes((samples * 32767).astype('<i2').tobytes())
            records.append(dict(path=filename, animal_id=f'animal-{animal}',
                                species=species, label=label, dataset='synthetic'))
    path = root / 'manifest.json'
    path.write_text(json.dumps(records))
    return path


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = fixture(self.root)

    def test_split_disjoint_reproducible_and_order_independent(self):
        rows, _ = load_records(self.manifest, self.root / 'registry.json', 'dog')
        split = split_records(rows, 42)
        self.assertEqual(split, split_records(rows[::-1], 42))
        groups = [{r['animal_id'] for r in split[key]} for key in ('train', 'validation', 'test')]
        self.assertTrue(all(groups))
        self.assertFalse(groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])

    def test_unknown_identity_rejected(self):
        rows = json.loads(self.manifest.read_text())
        rows[0]['animal_id'] = ''
        self.manifest.write_text(json.dumps(rows))
        with self.assertRaises(ValueError):
            load_records(self.manifest, self.root / 'registry.json', 'dog')

    def test_path_escape_and_duplicate_content_rejected(self):
        rows = json.loads(self.manifest.read_text())
        rows[0]['path'] = '../outside.wav'
        self.manifest.write_text(json.dumps(rows))
        with self.assertRaises(ValueError):
            load_records(self.manifest, self.root / 'registry.json', 'dog')
        fixture(self.root)
        (self.root / '1-low.wav').write_bytes((self.root / '0-low.wav').read_bytes())
        with self.assertRaises(ValueError):
            load_records(self.manifest, self.root / 'registry.json', 'dog')

    def test_invalid_and_empty_audio_rejected(self):
        path = self.root / 'bad.wav'
        path.write_bytes(b'not audio')
        with self.assertRaises(ValueError):
            features(path)
        with wave.open(str(path), 'wb') as stream:
            stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        with self.assertRaises(ValueError):
            features(path)

    def test_known_metrics_and_abstention(self):
        result = classification_metrics(np.array([0, 1]), np.array([[.8, .2], [.7, .3]]), ['a', 'b'], .9)
        self.assertEqual(result['accuracy'], .5)
        self.assertAlmostEqual(result['macro_f1'], 1/3)
        self.assertEqual(result['confusion_matrix'], [[1, 0], [1, 0]])
        self.assertAlmostEqual(result['brier'], .53)
        self.assertAlmostEqual(result['ece'], .45)
        self.assertEqual(result['coverage'], 0)
        self.assertIsNone(result['selective_accuracy'])

    def test_dog_train_reload_and_reproduce(self):
        for species in ('dog',):
            with self.subTest(species=species):
                fixture(self.root, species)
                out = self.root / species
                result = run(self.manifest, self.root / 'registry.json', species, out)
                replay = evaluate(out / 'model.json', self.manifest, self.root / 'registry.json')
                self.assertEqual(result['test'], replay)
                self.assertTrue(result['synthetic'])
                self.assertGreater(result['test']['macro_f1'], .9)
                self.assertTrue((out / 'splits.json').exists())

    def test_evaluation_refuses_changed_manifest(self):
        out = self.root / 'run'
        run(self.manifest, self.root / 'registry.json', 'dog', out)
        rows = json.loads(self.manifest.read_text())
        rows[0]['label'] = 'changed'
        self.manifest.write_text(json.dumps(rows))
        with self.assertRaises(ValueError):
            evaluate(out / 'model.json', self.manifest, self.root / 'registry.json')

    def test_rights_checked_before_media_access(self):
        from unittest.mock import patch
        registry = self.root / 'registry.json'
        registry.write_text(json.dumps({'synthetic': {'status': 'unknown'}}))
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('media read')):
            with self.assertRaises(ValueError):
                load_records(self.manifest, registry, 'dog')

    def test_normalization_uses_training_animals_only(self):
        out = self.root / 'normalization'
        run(self.manifest, self.root / 'registry.json', 'dog', out)
        splits = json.loads((out / 'splits.json').read_text())
        model = json.loads((out / 'model.json').read_text())
        train = np.stack([features(self.root / r['path']) for r in splits['train']])
        np.testing.assert_allclose(model['mean'], train.mean(axis=0))
        second = self.root / 'repeat'
        run(self.manifest, self.root / 'registry.json', 'dog', second)
        self.assertEqual((out / 'model.json').read_bytes(), (second / 'model.json').read_bytes())

    def test_missing_class_and_insufficient_animals_rejected(self):
        rows, _ = load_records(self.manifest, self.root / 'registry.json', 'dog')
        with self.assertRaises(ValueError):
            split_records(rows[:4], 42)
        rows[0]['label'] = 'rare-single-animal-label'
        with self.assertRaises(ValueError):
            split_records(rows, 42)

    def test_wrong_sample_rate_and_truncated_audio_rejected(self):
        path = self.root / 'bad.wav'
        with wave.open(str(path), 'wb') as stream:
            stream.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
            stream.writeframes(b'\x00\x00' * 8000)
        with self.assertRaises(ValueError):
            features(path)
        path.write_bytes((self.root / '0-low.wav').read_bytes()[:-500])
        with self.assertRaises(ValueError):
            features(path)
