import json
from pathlib import Path
import tempfile
import unittest
import wave
import numpy as np
from test_audio import fixture
from training.autolearn import process_job, scan, decide


class AutoLearnTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('train', 'benchmark'):
            folder = self.root / name
            folder.mkdir()
            manifest = fixture(folder)
            rows = json.loads(manifest.read_text())
            for row in rows:
                row['animal_id'] = name + '-' + row['animal_id']
                row['recording_group'] = row['animal_id'] + '-session'
                if name == 'benchmark':
                    path = folder / row['path']
                    with wave.open(str(path), 'rb') as w:
                        params, data = w.getparams(), w.readframes(w.getnframes())
                    with wave.open(str(path), 'wb') as w:
                        w.setparams(params)
                        w.writeframes((np.frombuffer(data, '<i2') // 2).astype('<i2').tobytes())
            manifest.write_text(json.dumps(rows))
        registry = json.loads((self.root / 'train/registry.json').read_text())
        registry['synthetic'].update(acquisition_evidence='locally generated', label_review='test author')
        (self.root / 'registry.json').write_text(json.dumps(registry))
        self.spec = dict(version=1, species='dog', manifest='train/manifest.json',
                         benchmark='benchmark/manifest.json', registry='registry.json')
        self.job = self.root / 'job.json'
        self.save()
        self.output = self.root / 'output'

    def save(self):
        self.job.write_text(json.dumps(self.spec))

    def test_real_training_artifacts_and_idempotence(self):
        first = process_job(self.job, self.output)
        self.assertEqual(first['decision'], 'synthetic_only')
        self.assertEqual(first['benchmark']['count'], 18)
        self.assertTrue(np.isfinite(first['benchmark']['macro_f1']))
        from evaluation.evaluate import evaluate
        replay = evaluate(self.output / first['run_id'] / 'model.json',
                          self.root / 'train/manifest.json', self.root / 'registry.json')
        saved = json.loads((self.output / first['run_id'] / 'metrics.json').read_text())
        self.assertEqual(replay, saved['test'])
        self.assertTrue((self.output / first['run_id'] / 'model.json').is_file())
        self.assertEqual(process_job(self.job, self.output)['run_id'], first['run_id'])
        self.assertEqual(len(list(self.output.glob('*/result.json'))), 1)
        self.assertFalse((self.output / 'active.json').exists())

    def test_revoked_rights_block_even_previously_completed_job(self):
        process_job(self.job, self.output)
        registry = json.loads((self.root / 'registry.json').read_text())
        registry['synthetic']['commercial_allowed'] = False
        (self.root / 'registry.json').write_text(json.dumps(registry))
        with self.assertRaisesRegex(ValueError, 'approved'):
            process_job(self.job, self.output)

    def test_holdout_identity_and_session_leakage_blocked(self):
        p = self.root / 'benchmark/manifest.json'
        rows = json.loads(p.read_text())
        for field, value in [('animal_id', 'train-animal-0'), ('recording_group', 'train-animal-0-session')]:
            original = rows[0][field]
            rows[0][field] = value
            p.write_text(json.dumps(rows))
            with self.assertRaisesRegex(ValueError, 'overlap'):
                process_job(self.job, self.output)
            rows[0][field] = original

    def test_unreviewed_acquisition_blocked(self):
        p = self.root / 'registry.json'
        data = json.loads(p.read_text())
        del data['synthetic']['acquisition_evidence']
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'acquisition_evidence'):
            process_job(self.job, self.output)

    def test_url_and_unknown_job_fields_rejected(self):
        for changes in [{'manifest': 'https://youtube.com/watch?v=test'}, {'command': 'bad'}]:
            previous = self.spec.copy()
            self.spec.update(changes)
            self.save()
            with self.assertRaises(ValueError):
                process_job(self.job, self.output)
            self.spec = previous

    def test_incumbent_replayed_on_same_benchmark(self):
        first = process_job(self.job, self.output)
        self.spec['incumbent'] = str(self.output / first['run_id'] / 'model.json')
        self.save()
        second = process_job(self.job, self.output)
        self.assertEqual(first['benchmark'], second['incumbent_benchmark'])
        self.assertNotEqual(first['run_id'], second['run_id'])

    def test_failure_does_not_stop_next_job(self):
        queue = self.root / 'queue'
        queue.mkdir()
        (queue / 'broken.json').write_text('{')
        valid = {**self.spec, **{k: str(self.root / self.spec[k]) for k in ('manifest','benchmark','registry')}}
        (queue / 'valid.json').write_text(json.dumps(valid))
        result = scan(queue, self.output)
        self.assertEqual(result[0]['status'], 'blocked')
        self.assertEqual(result[1]['status'], 'completed')

    def test_quality_gate_rejects_regression_and_low_coverage(self):
        good = dict(macro_f1=.9, coverage=.9, ece=.05, per_class_f1=[.9,.9])
        limits = dict(min_macro_f1=.8, min_coverage=.5, max_ece=.15, min_improvement=.01)
        self.assertEqual(decide(good, None, False, limits), 'review_required')
        self.assertEqual(decide(good, good, False, limits), 'rejected')
        self.assertEqual(decide({**good, 'coverage':.1}, None, False, limits), 'rejected')
        self.assertEqual(decide(good, {**good,'macro_f1':.8}, False, limits), 'candidate')

    def test_training_session_leakage_rejected(self):
        p = self.root / 'train/manifest.json'
        rows = json.loads(p.read_text())
        for row in rows:
            row['recording_group'] = 'same-recording'
        p.write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError, 'overlap'):
            process_job(self.job, self.output)

    def test_lock_contention_blocks_without_partial_result(self):
        import fcntl
        self.output.mkdir()
        with (self.output / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, 'lock'):
                process_job(self.job, self.output)
        self.assertEqual(list(self.output.glob('*/result.json')), [])

    def test_invalid_limits_rejected(self):
        self.spec['limits'] = {'min_macro_f1': float('nan')}
        self.save()
        with self.assertRaisesRegex(ValueError, 'limits'):
            process_job(self.job, self.output)

    def test_failed_training_can_retry_without_partial_artifact(self):
        from unittest.mock import patch
        with patch('training.autolearn.run', side_effect=ValueError('interrupted fit')):
            with self.assertRaisesRegex(ValueError, 'interrupted'):
                process_job(self.job, self.output)
        self.assertEqual(list(self.output.glob('*/result.json')), [])
        self.assertEqual(process_job(self.job, self.output)['status'], 'completed')
