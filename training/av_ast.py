"""Explicit offline cached-AST analysis of a local AV file, isolated and cancellable."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from training.pretrained_audio import MODEL,REVISION,DOG_LABELS


def worker_command():return [sys.executable,'-m','training.av_ast_worker']


def run(path,*,consent=False,timeout=120,cancel=None,vision=False,pose=False):
 if type(vision) is not bool or type(pose) is not bool:raise ValueError('Explicit vision flag required')
 if os.name!='posix':raise ValueError('Use Linux/WSL for isolated AV scoring')
 if consent is not True:raise ValueError('Explicit local consent required')
 if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=300:raise ValueError('Invalid bounded timeout')
 def check():
  if cancel is not None and cancel.is_set():raise InterruptedError('Cancelled')
 check();path=Path(path).resolve()
 if path.suffix.lower() not in ('.mp4','.webm') or not path.is_file() or not 1<=path.stat().st_size<=25*1024*1024:raise ValueError('Bounded local AV required')
 digest=hashlib.sha256(path.read_bytes()).hexdigest()
 env={k:os.environ[k] for k in ('PATH','HOME','SystemRoot','HF_HOME','HF_HUB_CACHE','XDG_CACHE_HOME') if k in os.environ}
 env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
 with tempfile.TemporaryDirectory(prefix='petsense-av-ast-') as td:
  env.update(TMPDIR=td,TEMP=td,TMP=td)
  with (Path(td)/'result.json').open('w+b') as out:
   proc=subprocess.Popen(worker_command(),cwd=Path(__file__).resolve().parents[1],stdin=subprocess.PIPE,stdout=out,stderr=subprocess.DEVNULL,env=env,start_new_session=os.name=='posix')
   try:
    payload=json.dumps({'path':str(path),'consent':True,'vision':vision,'pose':pose}).encode()
    if len(payload)>4096:raise ValueError('Path too long')
    proc.stdin.write(payload);proc.stdin.close();deadline=time.monotonic()+timeout
    while proc.poll() is None:
     check()
     if time.monotonic()>deadline:raise TimeoutError('AV model deadline')
     if os.fstat(out.fileno()).st_size>200000:raise ValueError('AV model output limit')
     time.sleep(.02)
    check()
    if proc.returncode:raise ValueError('Local cached AST/AV unavailable')
    out.seek(0);raw=out.read(200001)
    if len(raw)>200000:raise ValueError('AV report too large')
    r=json.loads(raw)
    if r.get('source_sha256')!=digest or r.get('source')!='local_ffmpeg_decoded_pts' or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Source mismatch')
    duration=r.get('duration');times=r.get('frame_times')
    if r.get('schema_version')!=1 or type(r.get('audio_present')) is not bool or type(duration) not in (float,int) or not math.isfinite(duration) or not .5<=duration<=30 or not isinstance(times,list) or not 1<=len(times)<=1800:raise ValueError('Invalid AV timing contract')
    if any(type(t) not in (float,int) or not math.isfinite(t) or not 0<=t<=duration+.05 for t in times) or any(b<=a for a,b in zip(times,times[1:])):raise ValueError('Invalid decoded video clock')
    if r.get('audio_present'):
     m=r.get('audio_model',{})
     if m.get('model')!=MODEL or m.get('revision')!=REVISION or m.get('decision')!='abstain' or m.get('species_verified') is not False or not isinstance(m.get('windows'),list) or not 1<=len(m['windows'])<=60:raise ValueError('Invalid AST model contract')
     for w in m['windows']:
      if not all(type(w.get(k)) in (float,int) and math.isfinite(w[k]) for k in ('start','end')) or not 0<=w['start']<w['end']<=r['duration']:raise ValueError('Invalid scored window')
      scores=w.get('dog_event_scores',[])
      if len(scores)!=7 or {s.get('label') for s in scores}!=set(DOG_LABELS) or any(type(s.get('score')) not in (float,int) or not math.isfinite(s['score']) or not 0<=s['score']<=1 for s in scores):raise ValueError('Invalid window scores')
    if vision:
     from training.small_vlm import MODEL as VM,REVISION as VR,LABELS
     v=r.get('vision_model',{})
     if v.get('model')!=VM or v.get('revision')!=VR or v.get('decision')!='abstain' or v.get('species_verified') is not False or not isinstance(v.get('observations'),list) or not 1<=len(v['observations'])<=6:raise ValueError('Invalid vision model contract')
     for obs in v['observations']:
      if obs.get('posture_candidate') not in LABELS or type(obs.get('seconds')) not in (float,int) or not math.isfinite(obs['seconds']) or not 0<=obs['seconds']<=r['duration']:raise ValueError('Invalid vision candidate')
    if pose:
     from training.dog_pose import DETECTOR,DETECTOR_REV,POSE,POSE_REV
     from training.track_pose import adapt
     p=r.get('pose_model',{})
     if p.get('detector_model')!=DETECTOR or p.get('detector_revision')!=DETECTOR_REV or p.get('keypoint_model')!=POSE or p.get('keypoint_revision')!=POSE_REV or p.get('decision')!='abstain' or p.get('identity_verified') is not False or not isinstance(p.get('frames'),list) or not 1<=len(p['frames'])<=6:raise ValueError('Invalid dog pose model contract')
     if any(not isinstance(f.get('detections'),list) or len(f['detections'])>4 for f in p['frames']):raise ValueError('Pose detection limit')
     doc={'source_sha256':digest,'source_kind':'upstream_model','model':DETECTOR+'/'+POSE,'revision':DETECTOR_REV+'+'+POSE_REV,'width':p['width'],'height':p['height'],'frames':[{'seconds':f['seconds'],'detections':[{k:d[k] for k in ('box','score','keypoints')} for d in f['detections']]} for f in p['frames']]}
     adapt(doc)
    return r
   finally:
    if proc.poll() is None:
     if os.name=='posix':os.killpg(proc.pid,signal.SIGKILL)
     else:proc.kill()
    proc.wait()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--video',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--consent-local',action='store_true');p.add_argument('--with-vision',action='store_true');p.add_argument('--with-pose',action='store_true');a=p.parse_args()
 if a.output.exists():raise ValueError('Preserve existing report')
 r=run(a.video,consent=a.consent_local,vision=a.with_vision,pose=a.with_pose)
 with a.output.open('x') as stream:json.dump(r,stream,allow_nan=False,indent=2)
if __name__=='__main__':main()
