"""Offline, locked-window event benchmark. Supplied predictions are not inference."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from evaluation.video_contract import validate_contract,Contract
from training.pretrained_audio import DOG_LABELS

class Strict(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
class Event(Strict):
 label:Literal['Dog','Bark','Yip','Howl','Bow-wow','Growling','Whimper (dog)']
 start:float=Field(ge=0,allow_inf_nan=False)
 end:float=Field(gt=0,allow_inf_nan=False)
 animal_id:str|None=Field(default=None,min_length=1,max_length=160)
 @model_validator(mode='after')
 def ordered(self):
  if self.end<=self.start:raise ValueError('Empty event')
  return self
class ReferenceClip(Strict):
 clip_id:str=Field(min_length=1,max_length=160)
 known:bool
 reviewers:list[str]=Field(min_length=1,max_length=2)
 events:list[Event]=Field(max_length=200)
 @model_validator(mode='after')
 def independent(self):
  if len(set(self.reviewers))!=len(self.reviewers) or any(not r.strip() or len(r)>160 for r in self.reviewers):raise ValueError('Distinct explicit reviewers required')
  if not self.known and self.events:raise ValueError('Unknown windows cannot assert events')
  return self
class Reference(Strict):
 parent_sha256:str=Field(pattern='^[a-f0-9]{64}$')
 synthetic:bool
 locked_at:int=Field(gt=0)
 split:Literal['validation','test']
 clips:list[ReferenceClip]=Field(min_length=1,max_length=10000)
class PredictedClip(Strict):
 clip_id:str=Field(min_length=1,max_length=160)
 sha256:str=Field(pattern='^[a-f0-9]{64}$')
 abstained:bool
 events:list[Event]=Field(max_length=200)
 presence_probabilities:dict[str,float]|None=None
 latency_seconds:float|None=Field(default=None,ge=0,allow_inf_nan=False)
 @model_validator(mode='after')
 def abstention(self):
  if self.abstained and self.events:raise ValueError('Abstentions cannot assert events')
  if self.presence_probabilities is not None:
   if set(self.presence_probabilities)!=set(DOG_LABELS) or any(not math.isfinite(v) or not 0<=v<=1 for v in self.presence_probabilities.values()):raise ValueError('All seven bounded presence probabilities required')
  return self
class Run(Strict):
 reference_sha256:str=Field(pattern='^[a-f0-9]{64}$')
 synthetic:bool
 mode:Literal['audio','video','fused']
 model:str=Field(min_length=1,max_length=200)
 revision:str=Field(min_length=1,max_length=200)
 clips:list[PredictedClip]=Field(max_length=10000)

def reference_digest(reference):
 r=Reference.model_validate(reference)
 return hashlib.sha256(json.dumps(r.model_dump(),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def matching(ref,pred):
 # Maximum-cardinality bipartite matching at fixed tIoU>=.5. No greedy undercount.
 edges=[]
 for p in pred:
  candidates=[]
  for i,r in enumerate(ref):
   overlap=max(0,min(p.end,r.end)-max(p.start,r.start));union=max(p.end,r.end)-min(p.start,r.start)
   if overlap/union>=.5:candidates.append(i)
  edges.append(candidates)
 assigned={}
 def visit(p,seen):
  for r in edges[p]:
   if r in seen:continue
   seen.add(r)
   if r not in assigned or visit(assigned[r],seen):assigned[r]=p;return True
  return False
 for p in range(len(pred)):visit(p,set())
 return [(ref[r],pred[p]) for r,p in assigned.items()]

def evaluate(parent,registry,reference,run):
 parent_check=validate_contract(parent,registry);base=Contract.model_validate(parent)
 ref=Reference.model_validate(reference);run=Run.model_validate(run)
 if ref.parent_sha256!=parent_check['contract_sha256'] or ref.synthetic!=base.synthetic or ref.locked_at>base.locked_at:raise ValueError('Unbound event references')
 if run.reference_sha256!=reference_digest(reference) or run.synthetic!=ref.synthetic:raise ValueError('Unbound predictions')
 windows={r.clip_id:r for r in base.records if r.split==ref.split}
 refs={r.clip_id:r for r in ref.clips};preds={r.clip_id:r for r in run.clips}
 if set(refs)!=set(windows) or len(refs)!=len(ref.clips) or len(preds)!=len(run.clips) or not set(preds)<=set(windows):raise ValueError('Evaluation window mismatch')
 for key,refclip in refs.items():
  w=windows[key];p=preds.get(key)
  if p and p.sha256!=w.sha256:raise ValueError('Media hash mismatch')
  for e in refclip.events:
   if e.animal_id not in (None,w.animal_id):raise ValueError('Reference subject is outside target dog contract')
  for e in refclip.events+(p.events if p else []):
   if not w.start_seconds<=e.start<e.end<=w.end_seconds:raise ValueError('Events must use parent video clock and bounded window')
 counts={label:dict(tp=0,fp=0,fn=0) for label in DOG_LABELS};onsets=[];offsets=[];hours=0;unknown=0;accepted=0;verified=0;identity_errors=0;latencies=[];calibration=[]
 for key,r in refs.items():
  w=windows[key];p=preds.get(key)
  if p and p.latency_seconds is not None:latencies.append(p.latency_seconds)
  accepted+=bool(p and not p.abstained)
  if not r.known:unknown+=1;continue
  if p and p.presence_probabilities is not None:
   calibration.extend((p.presence_probabilities[label],int(any(e.label==label for e in r.events))) for label in DOG_LABELS)
  hours+=(w.end_seconds-w.start_seconds)/3600
  events=p.events if p and not p.abstained else []
  for label in DOG_LABELS:
   rr=[e for e in r.events if e.label==label];pp=[e for e in events if e.label==label];pairs=matching(rr,pp)
   c=counts[label];c['tp']+=len(pairs);c['fp']+=len(pp)-len(pairs);c['fn']+=len(rr)-len(pairs)
   for a,b in pairs:
    onsets.append(abs(a.start-b.start));offsets.append(abs(a.end-b.end))
    if a.animal_id is not None:
     verified+=int(b.animal_id==a.animal_id);identity_errors+=int(b.animal_id is not None and b.animal_id!=a.animal_id)
 for c in counts.values():
  n=2*c['tp']+c['fp']+c['fn'];c['f1']=2*c['tp']/n if n else None
 def mean(v):return sum(v)/len(v) if v else None
 latencies.sort()
 return dict(reference_sha256=run.reference_sha256,synthetic=run.synthetic,mode=run.mode,model=run.model,revision=run.revision,
  real_behavior_accuracy_established=False,per_class=counts,coverage=accepted/len(refs),missing_windows=len(refs)-len(preds),unknown_windows=unknown,
  false_positives_per_hour=sum(c['fp'] for c in counts.values())/hours if hours else None,known_hours=hours,
  presence_brier_score=mean([(p-y)**2 for p,y in calibration]),presence_probability_count=len(calibration),
  calibration_established=False,
  onset_mae_seconds=mean(onsets),offset_mae_seconds=mean(offsets),matched_events=len(onsets),speaker_identity_verified=verified,speaker_identity_errors=identity_errors,
  latency_p95_seconds=latencies[max(0,math.ceil(.95*len(latencies))-1)] if latencies else None,
  limitations=['Supplied predictions only; no inference/media alignment/identity audit','Fixed tIoU=.5; label synonyms are not merged','Unknown reference windows excluded from event metrics','Identity verified means reference agreement, not independent source verification','No calibrated emotion/intent probabilities or causal conclusions'])

def compare(parent,registry,reference,runs):
 parsed=[Run.model_validate(r) for r in runs]
 if len(parsed)!=3 or {r.mode for r in parsed}!={'audio','video','fused'}:raise ValueError('Exactly one audio/video/fused run required')
 return {r['mode']:evaluate(parent,registry,reference,r) for r in runs}

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('parent','registry','reference','runs','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args()
 def load(path):
  if path.stat().st_size>8000000:raise ValueError('Input too large')
  return json.loads(path.read_text())
 result=compare(load(a.parent),a.registry,load(a.reference),load(a.runs))
 with a.output.open('x') as out:json.dump(result,out,indent=2,allow_nan=False)
if __name__=='__main__':main()
