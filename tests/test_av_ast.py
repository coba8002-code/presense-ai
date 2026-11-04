import json,subprocess,sys,tempfile,unittest,os
from pathlib import Path
from threading import Event
from unittest.mock import patch
from training.av_ast import run
class AVASTTests(unittest.TestCase):
 def test_no_consent_never_starts_worker(self):
  with patch('training.av_ast.subprocess.Popen',side_effect=AssertionError('worker started')):
   with self.assertRaises(ValueError):run('missing.webm',consent=False)
 def test_timeout_and_cancel_reap(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'clip.webm';p.write_bytes(b'fixture')
   with patch('training.av_ast.worker_command',return_value=[sys.executable,'-c','import time;time.sleep(20)']):
    with self.assertRaises(TimeoutError):run(p,consent=True,timeout=.1)
    flag=Event();flag.set()
    with self.assertRaises(InterruptedError):run(p,consent=True,cancel=flag)
 def test_non_json_worker_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'clip.webm';p.write_bytes(b'fixture')
   with patch('training.av_ast.worker_command',return_value=[sys.executable,'-c','print("not a report")']):
    with self.assertRaises(ValueError):run(p,consent=True)

 def test_credentials_removed_and_temp_root_discarded(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'clip.webm';p.write_bytes(b'fixture');record=Path(td)/'env.json'
   code="import os,json,pathlib;pathlib.Path("+repr(str(record))+").write_text(json.dumps({'password_present':bool(os.getenv('AX_LOGIN_PASSWORD')),'api_key_present':bool(os.getenv('OPENAI_API_KEY'))}));print('invalid')"
   factory=tempfile.TemporaryDirectory
   with patch.dict(os.environ,{'AX_LOGIN_PASSWORD':'synthetic-secret','OPENAI_API_KEY':'synthetic-key'}),patch('training.av_ast.worker_command',return_value=[sys.executable,'-c',code]),patch('training.av_ast.tempfile.TemporaryDirectory',lambda **kw:factory(dir=td,prefix='private-')):
    with self.assertRaises(ValueError):run(p,consent=True)
   self.assertEqual(json.loads(record.read_text()),{'password_present':False,'api_key_present':False})
   self.assertFalse(list(Path(td).glob('private-*')))
