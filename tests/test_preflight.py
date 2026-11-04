import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from training.data import approve_dataset, load_records
from test_audio import fixture


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = fixture(self.root)
        self.registry = self.root / 'registry.json'

    def invoke(self):
        return subprocess.run([sys.executable, '-m', 'training.preflight',
                               '--manifest', str(self.manifest), '--registry', str(self.registry),
                               '--species', 'dog'], capture_output=True, text=True, timeout=15)

    def test_cli_checks_data_without_training(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['record_count'], 18)
        self.assertEqual(report['animal_count'], 9)
        self.assertEqual(sum(p['records'] for p in report['partitions'].values()), 18)
        self.assertFalse(list(self.root.glob('model*')))

    def test_cli_denies_rights_with_actionable_error(self):
        self.registry.write_text(json.dumps({'synthetic': {'status': 'unknown'}}))
        result = self.invoke()
        self.assertEqual(result.returncode, 2)
        self.assertIn('not approved', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_cli_checks_wav_content(self):
        (self.root / '0-low.wav').write_bytes(b'invalid')
        result = self.invoke()
        self.assertEqual(result.returncode, 2)
        self.assertIn('WAV', result.stderr)

    def test_registry_non_object_fails_closed(self):
        for invalid in ([], None, 42, {'synthetic': []}):
            with self.subTest(invalid=invalid):
                self.registry.write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):
                    approve_dataset(self.registry, 'synthetic')

    def test_identity_whitespace_and_absolute_paths_are_rejected(self):
        for field, value in [('animal_id', 'animal-0 '),
                             ('path', str(self.root / '0-low.wav'))]:
            with self.subTest(field=field):
                fixture(self.root)
                rows = json.loads(self.manifest.read_text())
                rows[0][field] = value
                self.manifest.write_text(json.dumps(rows))
                with self.assertRaises(ValueError):
                    load_records(self.manifest, self.registry, 'dog')

    def test_synthetic_type_cannot_hide_real_provenance(self):
        policy = json.loads(self.registry.read_text())
        policy['synthetic']['synthetic'] = 'true'
        self.registry.write_text(json.dumps(policy))
        with self.assertRaises(ValueError):
            approve_dataset(self.registry, 'synthetic')
