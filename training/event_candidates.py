"""Unvalidated hysteresis postprocessing of uncalibrated window scores, not labels."""
import math
from training.pretrained_audio import DOG_LABELS


def candidates(windows,*,enter=.6,exit=.4,max_gap=.2):
 if not isinstance(windows,list) or len(windows)>60:raise ValueError('Bounded windows required')
 if any(type(v) not in (float,int) or not math.isfinite(v) for v in (enter,exit,max_gap)) or not 0<=exit<enter<=1 or not 0<=max_gap<=1:raise ValueError('Invalid experimental thresholds')
 last=-1;last_end=-1;parsed=[]
 for w in windows:
  if not isinstance(w,dict) or any(type(w.get(k)) not in (float,int) or not math.isfinite(w[k]) for k in ('start','end')) or not 0<=w['start']<w['end']<=30 or w['start']<=last:raise ValueError('Invalid window clock')
  if w['end']<last_end:raise ValueError('Window ends must not go backwards')
  last=w['start'];last_end=w['end'];values=w.get('dog_event_scores')
  if not isinstance(values,list) or len(values)>7:raise ValueError('Invalid scores')
  scores={}
  for x in values:
   if not isinstance(x,dict) or x.get('label') not in DOG_LABELS or x['label'] in scores or type(x.get('score')) not in (float,int) or not math.isfinite(x['score']) or not 0<=x['score']<=1:raise ValueError('Invalid uncalibrated score')
   scores[x['label']]=x['score']
  quality=w.get('audio_quality',{})
  if not isinstance(quality,dict):raise ValueError('Invalid quality cues')
  flags=quality.get('warnings',[])
  if not isinstance(flags,list) or any(f not in ('near_silence','clipping') for f in flags):raise ValueError('Unknown signal quality flag')
  parsed.append((w,scores,flags))
 found=[]
 for label in DOG_LABELS:
  active=[]
  def finish():
   if active:
    first=active[0][0];last=active[-1][0]
    found.append({'label':label,'start':first['start'],'end':last['end'],'onset_interval':[first['start'],first['end']],
     'offset_interval':[last['start'],last['end']],'peak_score':max(s[label] for _,s,_ in active),
     'quality_flags':sorted({f for _,_,flags in active for f in flags}),'speaker':'unconfirmed','status':'unvalidated_candidate'})
    active.clear()
  for w,scores,flags in parsed:
   if active and (w['start']>active[-1][0]['end']+max_gap or scores.get(label,0)<exit):finish()
   if scores.get(label,0)>=enter or (active and scores.get(label,0)>=exit):active.append((w,scores,flags))
  finish()
 return {'policy':'experimental-hysteresis-v1','enter':enter,'exit':exit,'max_gap':max_gap,'validated':False,'decision':'abstain',
  'candidates':sorted(found,key=lambda c:(c['start'],c['label'])),'limitations':['Heuristic thresholds are not validation-fitted','Boundaries are window envelopes, not measured onset/offset','Quality flags do not measure noise SNR','Parent/child labels may overlap; no speaker/emotion/intent attribution']}
