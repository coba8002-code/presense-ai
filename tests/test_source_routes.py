import json
from pathlib import Path
import tempfile
import unittest
from training.data import approve_dataset
from training.source_routes import route, report


class SourceRoutesTests(unittest.TestCase):
    def test_restricted_and_unknown_licenses(self):
        for license in ('CC BY-NC-SA 4.0', 'cc-by-nc-4.0', 'research-only'):
            self.assertEqual(route({'license': license}), 'research_review')
        self.assertEqual(route({'license': 'CC BY-NC-ND 4.0'}), 'permission_required')
        self.assertEqual(route({'license': 'unknown'}), 'permission_required')
        self.assertEqual(route({'license': 'CC BY 4.0'}), 'commercial_candidate')

    def test_boolean_approval_cannot_override_research_lane(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'registry.json'
            policy = dict(status='approved', training_allowed=True, commercial_allowed=True,
                          source='source', version='v1', license='CC BY-NC 4.0', rights_evidence='evidence',
                          consent='documented', reviewer='operator', reviewed_at='2026-11-01')
            for extra in ({}, {'usage_lane':'commercial_candidate'}, {'license':'CC BY 4.0','usage_lane':'research_review'}):
                p.write_text(json.dumps({'x':{**policy, **extra}}))
                with self.assertRaises(ValueError): approve_dataset(p,'x')

    def test_report_is_not_permission_or_training(self):
        result = report({'x':{'license':'CC BY 4.0'}, 'y':{'license':'cc-by-nc-4.0'},
                         'cat':{'species':'cat','license':'unknown'}})
        self.assertEqual(len(result['sources']),2)
        self.assertFalse(result['training_performed'])
        self.assertTrue(all(not r['training_ready'] for r in result['sources']))
        self.assertEqual(len(result['permission_requests']),1)

    def test_registered_sources_remain_blocked(self):
        registry = json.loads(Path('datasets/registry.json').read_text())
        for name in ('dogspeak','interpet4d','barkmeow','dog-pain','pawgaze','b-doped','canine-emotions-av'):
            self.assertIn(name, registry)
            with self.assertRaises(ValueError): approve_dataset('datasets/registry.json',name)
