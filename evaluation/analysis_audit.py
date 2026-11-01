"""Offline household-cluster uncertainty, failure queues and human explanation rubric.

No model inference, reference generation, automatic label approval or training.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Literal
from pydantic import Field,field_validator
from evaluation.event_evaluation import Run,Reference,Strict,evaluate,matching
from evaluation.video_contract import Contract
from training.pretrained_audio import DOG_LABELS


def run_digest(run):
 return hashlib.sha256(json.dumps(Run.model_validate(run).model_dump(),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def audit_run(parent,registry,reference,run,*,repetitions=500,seed=0):
 if type(repetitions) is not int or not 100<=repetitions<=2000 or type(seed) is not int or not 0<=seed<=2**32-1:raise ValueError('Bounded integer bootstrap policy required')
 result=evaluate(parent,registry,reference,run)  # Reuse exact hash, source, split/window and rights gates.
 refs=Reference.model_validate(reference);predictions=Run.model_validate(run)
 rows={r.clip_id:r for r in Contract.model_validate(parent).records};pred={r.clip_id:r for r in predictions.clips}
 groups={};failures=[]
 for ref in refs.clips:
  row=rows[ref.clip_id];p=pred.get(ref.clip_id)
  if not ref.known:continue
  events=p.events if p and not p.abstained else []
  tp=fp=fn=0
  for label in DOG_LABELS:
   rr=[e for e in ref.events if e.label==label];pp=[e for e in events if e.label==label];n=len(matching(rr,pp));tp+=n;fp+=len(pp)-n;fn+=len(rr)-n
  agg=groups.setdefault(row.household_id,[0,0,0,0.])
  for i,n in enumerate([tp,fp,fn,row.end_seconds-row.start_seconds]):agg[i]+=n
  if p is None or p.abstained or fp or fn:
   failures.append({'clip_id':ref.clip_id,'kind':'missing_or_abstained' if p is None or p.abstained else 'event_mismatch',
    'tp':tp,'fp':fp,'fn':fn,'source_sha256':row.sha256,'start':row.start_seconds,'end':row.end_seconds,
    'review_status':'unreviewed','training_eligible':False})
 rng=random.Random(seed);values=list(groups.values());f1_draws=[];fp_draws=[]
 if len(values)>=5:
  for _ in range(repetitions):
   selected=[values[rng.randrange(len(values))] for _ in values];tp,fp,fn,seconds=[sum(x[i] for x in selected) for i in range(4)]
   if 2*tp+fp+fn:f1_draws.append(2*tp/(2*tp+fp+fn))
   if seconds:fp_draws.append(fp/seconds*3600)
 def interval(draws):
  if not draws:return None
  draws.sort();return [draws[max(0,math.ceil(len(draws)*q)-1)] for q in (.025,.975)]
 return {'run_sha256':run_digest(run),'reference_sha256':result['reference_sha256'],'synthetic':result['synthetic'],
  'status':'household_percentile_bootstrap' if len(values)>=5 else 'insufficient_independent_households',
  'households':len(values),'minimum_households':5,'repetitions':repetitions,'seed':seed,
  'micro_f1_ci95':interval(f1_draws),'false_positives_per_hour_ci95':interval(fp_draws),'f1_valid_draws':len(f1_draws),
  'failure_cases':failures,'training_eligible':False,'real_behavior_accuracy_established':False,
  'limitations':['Percentile intervals over household clusters; not BCa or proof of population representativeness',
   'Known event windows only; absent F1 denominators yield omitted F1 draws',
   'Review queue contains supplied prediction errors, not newly verified labels',
   'Synthetic runs and small/biased samples cannot establish actual behavioral accuracy']}


class Explanation(Strict):
 clip_id:str=Field(min_length=1,max_length=160)
 text:str=Field(min_length=1,max_length=10000)
class Review(Strict):
 clip_id:str=Field(min_length=1,max_length=160)
 explanation_sha256:str=Field(pattern='^[a-f0-9]{64}$')
 reviewer:str=Field(min_length=1,max_length=160)
 model_identity_hidden:Literal[True]
 grounded:bool
 causal_overclaim:bool
 emotion_intent_overclaim:bool
 useful_question:bool
 @field_validator('model_identity_hidden',mode='before')
 @classmethod
 def explicit_blind(cls,value):
  if value is not True:raise ValueError('Explicit true required for identity-blind review')
  return value
class ReviewBundle(Strict):
 run_sha256:str=Field(pattern='^[a-f0-9]{64}$')
 synthetic:bool
 explanations:list[Explanation]=Field(max_length=10000)
 reviews:list[Review]=Field(max_length=20000)


def review_explanations(run,document):
 parsed=Run.model_validate(run);doc=ReviewBundle.model_validate(document)
 if doc.run_sha256!=run_digest(run) or doc.synthetic!=parsed.synthetic:raise ValueError('Reviews not bound to exact run')
 ids={p.clip_id for p in parsed.clips};texts={e.clip_id:e.text for e in doc.explanations}
 if len(texts)!=len(doc.explanations) or not set(texts)<=ids:raise ValueError('Unknown/duplicate explanation window')
 reviews={};seen=set()
 for r in doc.reviews:
  if not r.reviewer.strip() or r.reviewer!=r.reviewer.strip() or r.clip_id not in texts or r.explanation_sha256!=hashlib.sha256(texts[r.clip_id].encode()).hexdigest():raise ValueError('Review not bound to explanation')
  key=(r.clip_id,r.reviewer)
  if key in seen:raise ValueError('Duplicate reviewer for explanation')
  seen.add(key);reviews.setdefault(r.clip_id,[]).append(r)
  if len(reviews[r.clip_id])>2:raise ValueError('At most two independent reviewers per explanation')
 disagreements=0;double=0
 for group in reviews.values():
  if len(group)==2:
   double+=1
   disagreements+=int(any(getattr(group[0],k)!=getattr(group[1],k) for k in ('grounded','causal_overclaim','emotion_intent_overclaim','useful_question')))
 return {'run_sha256':doc.run_sha256,'synthetic':doc.synthetic,'explanations':len(texts),'review_rows':len(doc.reviews),
  'unreviewed_windows':len(texts)-len(reviews),'double_reviewed_windows':double,'needs_adjudication':disagreements,
  'ungrounded_reviews':sum(not r.grounded for r in doc.reviews),'causal_overclaim_reviews':sum(r.causal_overclaim for r in doc.reviews),
  'emotion_intent_overclaim_reviews':sum(r.emotion_intent_overclaim for r in doc.reviews),'useful_question_reviews':sum(r.useful_question for r in doc.reviews),
  'training_eligible':False,'automatic_approval':False,'reviewer_qualifications_verified':False,
  'limitations':['Human assertions only; names do not prove independent identity or expertise','Disagreement requires external adjudication; no automatic label promotion','Text/rubric hashes bind artifacts, not factual truth or behavioral causality']}


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('parent','registry','reference','run','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--reviews',type=Path);p.add_argument('--seed',type=int,default=0);p.add_argument('--repetitions',type=int,default=500);a=p.parse_args()
 def load(path):
  if path.stat().st_size>8000000:raise ValueError('Bounded input required')
  return json.loads(path.read_text())
 run=load(a.run);result=audit_run(load(a.parent),a.registry,load(a.reference),run,repetitions=a.repetitions,seed=a.seed)
 if a.reviews:result['explanation_review']=review_explanations(run,load(a.reviews))
 with a.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)
if __name__=='__main__':main()
