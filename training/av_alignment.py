"""Consent-only local demux/PTS alignment. Never fetches URLs or calls a model."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import numpy as np


def align(path,*,consent=False,cancel=None):
 if consent is not True:raise ValueError('Explicit local processing consent required')
 def cancelled():
  if cancel is not None and cancel.is_set():raise InterruptedError('Local AV processing cancelled')
 cancelled();path=Path(path).resolve()
 if path.suffix.lower() not in ('.mp4','.webm') or not path.is_file() or not 1<=path.stat().st_size<=25*1024*1024:raise ValueError('Bounded local MP4/WebM required')
 tools={k:shutil.which(k) for k in ('ffmpeg','ffprobe')}
 if not all(tools.values()):raise ValueError('Local ffmpeg/ffprobe required')
 media=path.read_bytes();original_hash=hashlib.sha256(media).hexdigest()
 deadline=time.monotonic()+45
 with tempfile.TemporaryDirectory(prefix='petsense-av-') as td:
  root=Path(td);seq=0
  source=root/('source'+path.suffix.lower());source.write_bytes(media);del media
  def run(tool,args,limit=2000000):
   nonlocal seq
   cancelled();seq+=1;out=root/f'out{seq}'
   with out.open('wb') as stream:
    proc=subprocess.Popen([tools[tool],'-v','error',*args],stdout=stream,stderr=subprocess.DEVNULL,
     cwd=root,env={k:os.environ[k] for k in ('PATH','SystemRoot') if k in os.environ},start_new_session=os.name=='posix')
    try:
     while proc.poll() is None:
      cancelled()
      if time.monotonic()>deadline or out.stat().st_size>limit:raise ValueError('Local AV deadline/output limit')
      time.sleep(.02)
     if proc.returncode or out.stat().st_size>limit:raise ValueError('Unsupported or damaged local AV')
    finally:
     if proc.poll() is None:
      if os.name=='posix':os.killpg(proc.pid,signal.SIGKILL)
      else:proc.kill()
     proc.wait()
   cancelled();return out.read_bytes()
  flags=['-protocol_whitelist','file,pipe','-format_whitelist','mov,matroska,webm']
  info=json.loads(run('ffprobe',flags+['-show_streams','-show_format','-of','json',str(source)]))
  video=next((s for s in info['streams'] if s['codec_type']=='video'),None)
  audio=next((s for s in info['streams'] if s['codec_type']=='audio'),None)
  duration=float(info['format']['duration'])
  if not video or not math.isfinite(duration) or not .5<=duration<=30 or not 1<=video.get('width',0)<=1920 or not 1<=video.get('height',0)<=1080:raise ValueError('Video duration/resolution limit')
  def frames(selector):
   d=json.loads(run('ffprobe',flags+['-select_streams',selector,'-show_frames','-show_entries','frame=best_effort_timestamp_time,nb_samples','-of','json',str(source)]))
   return d['frames']
  vf=frames('v:0');pts=[float(f['best_effort_timestamp_time']) for f in vf]
  if not 1<=len(pts)<=1800 or not all(math.isfinite(v) for v in pts) or any(b<=a for a,b in zip(pts,pts[1:])):raise ValueError('Invalid video timestamps')
  origin=pts[0];relative=[v-origin for v in pts]
  if relative[-1]>duration+.05:raise ValueError('Video clock mismatch')
  report={'schema_version':1,'source_sha256':original_hash,'duration':duration,
   'clock':'relative_to_first_decoded_video_frame','video_origin_pts':origin,'frame_times':relative,
   'audio_present':bool(audio),'audio_start':None,'audio_windows':[],
   'speaker_verified':False,'model_inference':False,'source':'local_ffmpeg_decoded_pts',
   'limitations':['Container timestamps only; sensor capture sync not verified','No sound event classification or speaker/emotion/intent inference','Audio discontinuity is rejected, not silently repaired']}
  if audio:
   af=frames('a:0');rate=int(audio['sample_rate'])
   if not 1<=len(af)<=10000 or not 8000<=rate<=192000:raise ValueError('Invalid audio frames/rate')
   samples=0;first=float(af[0]['best_effort_timestamp_time'])
   for f in af:
    stamp=float(f['best_effort_timestamp_time']);count=int(f['nb_samples'])
    if not math.isfinite(stamp) or not 0<count<=192000 or abs(stamp-(first+samples/rate))>.025:raise ValueError('Discontinuous audio clock')
    samples+=count
   raw=run('ffmpeg',flags+['-i',str(source),'-map','0:a:0','-vn','-ac','1','-ar','16000','-f','s16le','pipe:1'],limit=1000000)
   signal_data=np.frombuffer(raw,dtype='<i2').astype(np.float64)/32768
   if abs(len(signal_data)/16000-samples/rate)>.025:raise ValueError('Decoded sample duration mismatch')
   start=first-origin
   if start<-.05 or start+len(signal_data)/16000>duration+.1:raise ValueError('Audio outside bounded video clock')
   report['audio_start']=start
   for i in range(0,len(signal_data),1600):
    chunk=signal_data[i:i+1600];a=max(0.,start+i/16000);b=min(duration,start+(i+len(chunk))/16000)
    if b>a:report['audio_windows'].append({'start':a,'end':b,'rms_dbfs':float(20*np.log10(max(float(np.sqrt(np.mean(chunk*chunk))),1e-12)))})
  cancelled()
  if hashlib.sha256(path.read_bytes()).hexdigest()!=original_hash:raise ValueError('Source changed during alignment')
  return report


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--video',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--consent-local',action='store_true');a=p.parse_args()
 if a.output.exists():raise ValueError('Preserve existing report')
 try:r=align(a.video,consent=a.consent_local)
 except KeyboardInterrupt:p.exit(130,'Cancelled; temporary media discarded\n')
 with a.output.open('x') as stream:json.dump(r,stream,indent=2,allow_nan=False)
if __name__=='__main__':main()
