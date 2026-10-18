import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from training.small_vlm import load_manifest, normalize_prediction


class SmallVLMTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        policy = dict(status='approved', training_allowed=True, commercial_allowed=True,
                      source='owned', version='1', license='owner permission',
                      rights_evidence='signed release', consent='yes', reviewer='expert',
                      reviewed_at='2026-10-18')
        self.registry = self.root / 'registry.json'
        self.registry.write_text(json.dumps({'dogs': policy}))
        self.rows = []
        for i in range(5):
            for label in ('standing', 'sitting'):
                name = f'{i}-{label}.png'
                data = name.encode()
                (self.root / name).write_bytes(data)
                self.rows.append(dict(path=name, sha256=hashlib.sha256(data).hexdigest(),
                    species='dog', label=label, animal_id=f'dog{i}', recording_group=f'session{i}',
                    source_id=f'source{i}', dataset='dogs', reviewer='expert', review_evidence='local review',
                    reviewed_at='2026-10-18', split='train' if i < 3 else 'validation' if i == 3 else 'test'))
        self.manifest = self.root / 'frames.json'

    def load(self):
        self.manifest.write_text(json.dumps(self.rows))
        return load_manifest(self.manifest, self.registry)

    def test_accepts_disjoint_reviewed_manifest(self):
        rows, policies = self.load()
        self.assertEqual(len(rows), 10)
        self.assertIn('dogs', policies)

    def test_rejects_cross_split_identity_source_and_session(self):
        for field in ('animal_id', 'source_id', 'recording_group'):
            with self.subTest(field=field):
                old = self.rows[-1][field]
                self.rows[-1][field] = self.rows[0][field]
                with self.assertRaises(ValueError): self.load()
                self.rows[-1][field] = old

    def test_rejects_species_temporal_labels_tamper_and_escape(self):
        for field, value in [('species','cat'), ('label','walking'), ('sha256','0'*64),
                             ('path','../outside.png'), ('reviewer',' '), ('animal_id','unknown')]:
            with self.subTest(field=field):
                old = self.rows[0][field]
                self.rows[0][field] = value
                with self.assertRaises(ValueError): self.load()
                self.rows[0][field] = old

    def test_rejects_unapproved_rights(self):
        self.registry.write_text('{}')
        with self.assertRaises(ValueError): self.load()

    def test_abstains_on_unstructured_or_non_dog_answer(self):
        self.assertEqual(normalize_prediction(' sitting '), 'sitting')
        for answer in ('cat sitting', 'walking', 'The dog is sitting.', '', 'SITTING'):
            self.assertEqual(normalize_prediction(answer), 'unknown')
