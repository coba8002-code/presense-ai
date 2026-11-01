import json,subprocess,tempfile,unittest,shutil
from threading import Timer
from unittest.mock import patch
from pathlib import Path
from threading import Event
from training.av_alignment import align
@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'Local media tools required; dedicated CI step runs after installation')
class AVTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def fixture(self,audio=True,vfr=False):
  p=self.root/('av.webm' if audio else 'silent.webm')
  cmd=['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x120:rate=10:duration=2']
  if audio:cmd+=['-itsoffset','0.3','-f','lavfi','-i','sine=frequency=800:sample_rate=48000:duration=1.5']
  if vfr:cmd+=['-vf',r'select=not(mod(n\,3))+not(mod(n\,5))','-fps_mode','vfr']
  cmd+=['-c:v','libvpx']
  cmd+=['-c:a','libopus'] if audio else ['-an']
  subprocess.run(cmd+[str(p)],check=True);return p
 def test_real_audio_and_video_common_clock(self):
  r=align(self.fixture(),consent=True)
  self.assertTrue(r['audio_present']);self.assertGreater(len(r['audio_windows']),5)
  self.assertAlmostEqual(r['audio_start'],.3,delta=.025)
  self.assertTrue(all(a<b for a,b in zip(r['frame_times'],r['frame_times'][1:])))
  self.assertFalse(r['speaker_verified']);self.assertFalse(r['model_inference'])
 def test_no_audio_and_cancel_and_consent(self):
  p=self.fixture(False);self.assertFalse(align(p,consent=True)['audio_present'])
  with self.assertRaises(ValueError):align(p,consent=False)
  flag=Event();flag.set()
  with self.assertRaises(InterruptedError):align(p,consent=True,cancel=flag)
 def test_invalid_input_no_output_artifacts(self):
  p=self.root/'bad.webm';p.write_bytes(b'bad')
  with self.assertRaises(ValueError):align(p,consent=True)
  self.assertEqual(list(self.root.iterdir()),[p])

 def test_variable_frame_times_and_mid_processing_cancel(self):
  p=self.fixture(vfr=True);r=align(p,consent=True)
  gaps={round(b-a,2) for a,b in zip(r['frame_times'],r['frame_times'][1:])}
  self.assertGreater(len(gaps),1)
  flag=Event();timer=Timer(.01,flag.set);timer.start()
  factory=tempfile.TemporaryDirectory
  try:
   with patch('training.av_alignment.tempfile.TemporaryDirectory',lambda **kw:factory(dir=self.root,prefix='private-')):
    with self.assertRaises(InterruptedError):align(p,consent=True,cancel=flag)
  finally:timer.cancel()
  self.assertFalse(list(self.root.glob('private-*')))

 def test_frame_and_audio_hooks_use_decoded_private_media(self):
  p=self.fixture();seen={}
  def sound(signal,start,duration):
   seen['samples']=len(signal);self.assertAlmostEqual(start,.3,delta=.025)
   return {'test_observer':True}
  def picture(report,image):
   self.assertTrue(image(0).startswith(b'\x89PNG\r\n\x1a\n'))
   with self.assertRaises(ValueError):image(-1)
   seen['frames']=len(report['frame_times']);return {'test_observer':True}
  result=align(p,consent=True,audio_observer=sound,frame_observer=picture)
  self.assertGreater(seen['samples'],16000);self.assertGreater(seen['frames'],5)
  self.assertTrue(result['model_inference'])
