import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('pc',Path(__file__).parents[1]/'local_pc/pc.py')
pc=importlib.util.module_from_spec(spec);spec.loader.exec_module(pc)

class LocalPCTests(unittest.TestCase):
    def test_inventory_hashes_and_does_not_follow_linked_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'data';root.mkdir();(root/'dog.wav').write_bytes(b'local audio')
            (root/'skip.key').write_text('not collected')
            out=Path(td)/'result.json';pc.inventory(root,out)
            result=json.loads(out.read_text());self.assertEqual(len(result['files']),1)
            self.assertEqual(result['files'][0]['sha256'],pc.digest(root/'dog.wav'))
            self.assertFalse(result['training_approved'])
            with self.assertRaises(FileExistsError):pc.inventory(root,out)

    def test_download_rejects_invalid_keys_before_start(self):
        with tempfile.TemporaryDirectory() as td,patch.object(pc.shutil,'which',return_value='/usr/bin/aihubshell'),patch.object(pc.subprocess,'Popen') as run:
            with self.assertRaises(ValueError):pc.aihub(59,'1;touch bad',1,td,'aihubshell')
            with self.assertRaises(ValueError):pc.aihub(59,'1',None,td,'aihubshell')
            with self.assertRaises(ValueError):pc.aihub(59,'1',float('nan'),td,'aihubshell')
            run.assert_not_called()

    def test_download_rejects_insufficient_disk_before_credentials(self):
        with tempfile.TemporaryDirectory() as td,patch.object(pc.shutil,'which',return_value='/usr/bin/aihubshell'),patch.object(pc.shutil,'disk_usage') as disk,patch.object(pc.getpass,'getpass') as key:
            disk.return_value.free=100
            with self.assertRaises(ValueError):pc.aihub(59,'123',1,td,'aihubshell')
            key.assert_not_called()

    def test_esc10_rejects_tampered_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'file.wav').write_bytes(b'tampered')
            rows=[{'category':'dog' if i<40 else 'rain','path':'file.wav','sha256':'0'*64} for i in range(400)]
            (root/'inventory.json').write_text(json.dumps({'files':rows}))
            with self.assertRaisesRegex(ValueError,'hash mismatch'):pc.verify_esc(root)

    def test_esc10_rejects_parent_escape(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'data';root.mkdir()
            rows=[{'category':'dog' if i<40 else 'rain','path':'../secret.wav','sha256':'0'*64} for i in range(400)]
            (root/'inventory.json').write_text(json.dumps({'files':rows}))
            with self.assertRaisesRegex(ValueError,'path/hash'):pc.verify_esc(root)
