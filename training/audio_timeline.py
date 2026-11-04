"""Local research adapters. Inject a scorer; no automatic model loads or network calls."""
import hashlib
import math
import statistics
from datetime import date
import numpy as np
from training.audio_quality import audio_quality


def analyze_windows(signal,scorer,*,offset=0.,video_duration=30.):
 s=np.asarray(signal,dtype=np.float32)
 if (s.ndim!=1 or not 1600<=len(s)<=480000 or not np.all(np.isfinite(s)) or np.max(np.abs(s))>1
     or type(offset) not in (float,int) or not math.isfinite(offset) or offset<0
     or type(video_duration) not in (float,int) or not math.isfinite(video_duration) or not 0<video_duration<=30
     or offset+len(s)/16000>video_duration):raise ValueError('Invalid bounded shared clock/signal')
 starts=list(range(0,max(1,len(s)-16000+1),8000))
 last=max(0,len(s)-16000)
 if last not in starts:starts.append(last)
 windows=[]
 for start in starts:
  chunk=s[start:min(start+16000,len(s))]
  digest=hashlib.sha256(chunk.astype('<f4').tobytes()).hexdigest()
  result=scorer(chunk,digest)
  if not isinstance(result,dict) or result.get('decision')!='abstain' or not isinstance(result.get('dog_event_scores'),list):raise ValueError('Scorer must preserve uncalibrated abstention contract')
  windows.append({'start':offset+start/16000,'end':offset+(start+len(chunk))/16000,
   'score_result':result,'audio_quality':audio_quality(chunk)})
 return {'clock':'parent_video_seconds','alignment_source':'caller_supplied_offset_unverified','windows':windows,
  'events':[],'decision':'abstain','limitation':'Overlapping window scores do not establish event onset/offset, speaker, emotion or intent'}


def pet_baseline(history,*,dog_id,model_revision,current_count,current_duration):
 if not isinstance(history,list) or len(history)>1000 or not dog_id or not model_revision:raise ValueError('Bounded history and known identity/revision required')
 def valid(count,duration):
  return type(count) is int and 0<=count<=100000 and type(duration) in (float,int) and math.isfinite(duration) and .1<=duration<=86400
 if not valid(current_count,current_duration):raise ValueError('Invalid current observation')
 days={};excluded=0
 for r in history:
  if not isinstance(r,dict):raise ValueError('Invalid history')
  if r.get('dog_id')!=dog_id or r.get('model_revision')!=model_revision or r.get('source')!='measured':excluded+=1;continue
  if not isinstance(r.get('day'),str) or not 1<=len(r['day'])<=32 or not valid(r.get('count'),r.get('duration')):raise ValueError('Invalid measured history')
  if date.fromisoformat(r['day']).isoformat()!=r['day']:raise ValueError('Canonical ISO calendar day required')
  c,d=days.get(r['day'],(0,0));days[r['day']]=(c+r['count'],d+r['duration'])
 rates=[c/d*60 for c,d in days.values()];baseline=statistics.median(rates) if len(rates)>=5 else None
 return {'days':len(rates),'excluded':excluded,'abstained':baseline is None,'baseline_per_minute':baseline,
  'delta_per_minute':current_count/current_duration*60-baseline if baseline is not None else None,
  'training_eligible':False,'limitations':['Caller-supplied measured history, not independently verified events','Device/context/sampling changes can change rates','Descriptive comparison only; no diagnosis or automatic feedback learning']}
