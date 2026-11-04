import asyncio
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from backend.audio_process import run_ast,WorkerError,WorkerTimeout
from training.pretrained_audio import DOG_LABELS,MODEL,REVISION

class ProcessAudioTests(unittest.TestCase):
    def payload(self,raw):
        return {'model':MODEL,'revision':REVISION,'input_sha256':hashlib.sha256(raw).hexdigest(),'decision':'abstain','production_ready':False,'species_verified':False,'dog_event_scores':[{'label':x,'score':.1} for x in DOG_LABELS]}
    def command(self,script):return patch('backend.audio_process.worker_command',return_value=[sys.executable,'-c',script])
    def test_real_child_protocol_and_offline_environment(self):
        result=self.payload(b'audio')
        script="import os,sys;assert os.environ['HF_HUB_OFFLINE']=='1';assert 'OPENAI_API_KEY' not in os.environ;assert sys.stdin.buffer.read()==b'audio';print("+repr(json.dumps(result))+")"
        with patch.dict(os.environ,{'OPENAI_API_KEY':'must-not-reach-child'}),self.command(script):self.assertEqual(asyncio.run(run_ast(b'audio',timeout=5)),result)
    def test_timeout_kills_and_reaps_process(self):
        with tempfile.TemporaryDirectory() as td:
            pidfile=Path(td)/'pid'
            script=f"import os,time;from pathlib import Path;Path({str(pidfile)!r}).write_text(str(os.getpid()));time.sleep(30)"
            with self.command(script),self.assertRaises(WorkerTimeout):asyncio.run(run_ast(b'audio',timeout=.5))
            if os.name=='posix' and pidfile.exists():
                with self.assertRaises(ProcessLookupError):os.kill(int(pidfile.read_text()),0)
    def test_cancel_kills_child(self):
        async def scenario(path):
            task=asyncio.create_task(run_ast(b'audio',timeout=10))
            for _ in range(200):
                if path.exists():break
                await asyncio.sleep(.005)
            self.assertTrue(path.exists());task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'pid'
            script=f"import os,time;from pathlib import Path;Path({str(path)!r}).write_text(str(os.getpid()));time.sleep(30)"
            with self.command(script):asyncio.run(scenario(path))
            if os.name=='posix':
                with self.assertRaises(ProcessLookupError):os.kill(int(path.read_text()),0)
    def test_bad_exit_bad_output_and_forged_provenance_rejected(self):
        bad=self.payload(b'audio');bad['input_sha256']='wrong'
        for script in ['raise SystemExit(3)',"print('not-json')",'print('+repr(json.dumps(bad))+')',"print('x'*100000)"]:
            with self.subTest(script=script[:30]),self.command(script),self.assertRaises(WorkerError):asyncio.run(run_ast(b'audio',timeout=5))
    def test_invalid_deadline_rejected_before_spawn(self):
        with self.assertRaises(ValueError):asyncio.run(run_ast(b'x',timeout=float('nan')))
