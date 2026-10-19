from importlib.metadata import PackageNotFoundError
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.check_environment import check_packages


class EnvironmentTests(unittest.TestCase):
    def test_reports_missing_and_mismatched_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / 'requirements.lock'
            lock.write_text('# test\nalpha==1.0\nbeta==2.0\ngamma==3.0\n')
            def version(name):
                if name == 'gamma':
                    raise PackageNotFoundError(name)
                return {'alpha': '1.0', 'beta': '1.5'}[name]
            with patch('scripts.check_environment.metadata.version', side_effect=version):
                result = check_packages(lock)
            self.assertEqual([p['status'] for p in result], ['ok', 'mismatch', 'missing'])

    def test_non_pinned_requirement_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / 'requirements.lock'
            lock.write_text('package>=1.0\n')
            with self.assertRaises(ValueError):
                check_packages(lock)
