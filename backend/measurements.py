"""Owner-only immutable snapshots of server job scores, never behavior truth."""
import asyncio
from collections import defaultdict
from datetime import datetime,timezone
import hashlib
import json
import math
import re
import sqlite3
import statistics
import uuid
from typing import Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field,ValidationError,field_validator
from starlette.requests import ClientDisconnect
from backend.accounts import Store,access
from training.pretrained_audio import MODEL,REVISION,DOG_LABELS
router=APIRouter()
CONDITIONS=('indoors_quiet','indoors_noise','outdoors','unknown')
SOURCES=('pretrained_model','synthetic_fixture')

class ObservationInput(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
 job_id:str=Field(pattern=r'^[a-f0-9-]{36}$')
 device_id:str=Field(pattern=r'^[A-Za-z0-9_-]{1,40}$')
 condition:Literal['indoors_quiet','indoors_noise','outdoors','unknown']
 same_dog_confirmed:Literal[True]
 @field_validator('same_dog_confirmed',mode='before')
 @classmethod
 def explicit(cls,value):
  if value is not True:raise ValueError('Guardian identity attestation required')
  return value
class FeedbackInput(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
 reason:Literal['seems_right','context_missing','wrong_dog','noise','not_sure']

class MeasurementStore(Store):
 def begin(self,db,token):
  db.row_factory=sqlite3.Row;db.execute('BEGIN IMMEDIATE');owner=self.session_owner(db,token);self._purge(db);return owner
 @staticmethod
 def view(row):
  return {k:row[k] for k in ('id','pet_id','source_job_id','created','submitted','expires')}|json.loads(row['payload'])|{'training_approved':False,'species_verified':False}
 def save(self,token,data):
  data=ObservationInput.model_validate(data)
  with self.connect() as db:
   owner=self.begin(db,token);job=db.execute("SELECT * FROM audio_jobs WHERE owner=? AND id=? AND status='succeeded' AND expires>?",(owner,data.job_id,self.clock())).fetchone()
   if not job:raise KeyError('Completed owner job required')
   if job['created']>self.clock():raise ValueError('Source submission timestamp is in the future')
   pet=self._pet(db,owner,job['pet_id']);r=json.loads(job['result']);scores=r.get('dog_event_scores',[]);duration=r.get('input_duration_seconds');source=r.get('execution_kind')
   if source not in SOURCES or r.get('model')!=MODEL or r.get('revision')!=REVISION or r.get('decision')!='abstain' or r.get('species_verified') is not False or type(duration) not in (float,int) or not math.isfinite(duration) or not .1<=duration<=10 or not re.fullmatch('[a-f0-9]{64}',r.get('input_sha256','')):raise ValueError('Unverified measurement provenance')
   expected=hashlib.sha256(json.dumps([job['pet_id'],r['input_sha256'],MODEL,REVISION,'temporary-audio-v1']).encode()).hexdigest()
   if expected!=job['payload_hash'] or len(scores)!=7 or {s.get('label') for s in scores}!=set(DOG_LABELS) or any(type(s.get('score')) not in (float,int) or not math.isfinite(s['score']) or not 0<=s['score']<=1 for s in scores):raise ValueError('Invalid source model result')
   scores=[{'label':label,'score':float(next(s['score'] for s in scores if s['label']==label))} for label in DOG_LABELS]
   value={'source_kind':source,'model':MODEL,'revision':REVISION,'input_sha256':r['input_sha256'],'device_id':data.device_id,'condition':data.condition,'duration_seconds':duration,'duration_bucket_deciseconds':round(duration*10),'scores':scores,'same_dog_source':'guardian_attestation_not_tracking','unit':'uncalibrated_score','record_time_kind':'server_job_submission_not_capture_time'}
   payload=json.dumps(value,sort_keys=True,separators=(',',':'));fingerprint=hashlib.sha256(payload.encode()).hexdigest()
   old=db.execute('SELECT * FROM model_observations WHERE owner=? AND source_job_id=?',(owner,job['id'])).fetchone()
   if old:
    if old['payload_hash']!=fingerprint:raise ValueError('Immutable observation context differs')
    return self.view(old)
   if db.execute('SELECT count(*) FROM model_observations WHERE owner=?',(owner,)).fetchone()[0]>=200:raise ValueError('Observation quota')
   ident=str(uuid.uuid4());now=self.clock();expires=min(now+30*86400,pet['expires'])
   db.execute('INSERT INTO model_observations VALUES(?,?,?,?,?,?,?,?,?)',(ident,owner,job['pet_id'],job['id'],now,job['created'],expires,payload,fingerprint))
   return self.view(db.execute('SELECT * FROM model_observations WHERE id=?',(ident,)).fetchone())
 def listing(self,token,pet_id,device_id,condition,source_kind):
  if not re.fullmatch('[A-Za-z0-9_-]{1,40}',device_id) or condition not in CONDITIONS or source_kind not in SOURCES:raise ValueError('Explicit measurement stratum required')
  with self.connect() as db:
   owner=self.begin(db,token);self._pet(db,owner,pet_id)
   rows=db.execute('SELECT * FROM model_observations WHERE owner=? AND pet_id=? AND submitted<=? ORDER BY submitted DESC,id LIMIT 200',(owner,pet_id,self.clock())).fetchall()
   all_items=[self.view(row) for row in rows]
   strata=[{'device_id':d,'condition':c,'source_kind':s} for d,c,s in sorted({(r['device_id'],r['condition'],r['source_kind']) for r in all_items})]
   items=[r for r in all_items if r['device_id']==device_id and r['condition']==condition and r['source_kind']==source_kind]
   feedback={r['observation_id']:dict(r) for r in db.execute('SELECT observation_id,reason,status FROM observation_feedback WHERE owner=?',(owner,))}
   for r in items:r['feedback']=(feedback.get(r['id']) or None)
   daily=defaultdict(list);current=items[0] if items else None
   if current:
    current_day=datetime.fromtimestamp(current['submitted'],timezone.utc).date().isoformat()
    for r in items[1:]:
     day=datetime.fromtimestamp(r['submitted'],timezone.utc).date().isoformat()
     if day<current_day and r['duration_bucket_deciseconds']==current['duration_bucket_deciseconds'] and r['model']==current['model'] and r['revision']==current['revision']:daily[day].append(r)
   medians={label:statistics.median([statistics.mean(next(s['score'] for s in r['scores'] if s['label']==label) for r in day) for day in daily.values()]) for label in DOG_LABELS} if len(daily)>=5 and condition!='unknown' else None
   return {'strata':strata,'items':items,'baseline':{'ready':medians is not None,'historical_days':len(daily),'minimum_days':5,'unit':'uncalibrated_score','medians':medians,'deltas':{s['label']:s['score']-medians[s['label']] for s in current['scores']} if medians and current else None,'condition_known':condition!='unknown','current_observation_id':current['id'] if current else None,'source_kind':source_kind,'device_id':device_id,'condition':condition,'interpretation':'Self-selected samples and unverified device/context; not event frequency, emotion or improvement','training_approved':False}}
 def delete_observation(self,token,ident):
  with self.connect() as db:
   owner=self.begin(db,token)
   if not db.execute('SELECT 1 FROM model_observations WHERE owner=? AND id=?',(owner,ident)).fetchone():raise KeyError('Observation not found')
   db.execute('DELETE FROM observation_feedback WHERE owner=? AND observation_id=?',(owner,ident));db.execute('DELETE FROM model_observations WHERE owner=? AND id=?',(owner,ident))
 def delete_feedback(self,token,ident):
  with self.connect() as db:
   owner=self.begin(db,token)
   if not db.execute('SELECT 1 FROM model_observations WHERE owner=? AND id=?',(owner,ident)).fetchone():raise KeyError('Observation not found')
   db.execute('DELETE FROM observation_feedback WHERE owner=? AND observation_id=?',(owner,ident))
 def feedback(self,token,ident,reason):
  FeedbackInput(reason=reason)
  with self.connect() as db:
   owner=self.begin(db,token)
   if not db.execute('SELECT 1 FROM model_observations WHERE owner=? AND id=?',(owner,ident)).fetchone():raise KeyError('Observation not found')
   old=db.execute('SELECT * FROM observation_feedback WHERE owner=? AND observation_id=?',(owner,ident)).fetchone()
   if old:
    if old['reason']!=reason:raise ValueError('Existing immutable feedback differs; delete observation to withdraw')
    return {'id':old['id'],'reason':reason,'status':old['status'],'training_approved':False}
   ident_feedback=str(uuid.uuid4());db.execute('INSERT INTO observation_feedback(id,owner,observation_id,created,reason,status) VALUES(?,?,?,?,?,?)',(ident_feedback,owner,ident,self.clock(),reason,'unreviewed'))
   return {'id':ident_feedback,'reason':reason,'status':'unreviewed','training_approved':False}


def context(request):
 store,_,token=access(request);return MeasurementStore(store.path),token

def operation(fn,*args):
 try:return fn(*args)
 except PermissionError:raise HTTPException(401,'Session expired') from None
 except KeyError:raise HTTPException(404,'Owned source or dog not found') from None
 except ValueError:raise HTTPException(422,'Invalid or immutable observation/context') from None
 except sqlite3.Error:raise HTTPException(503,'Observation store unavailable') from None

async def payload(request,model):
 if request.headers.get('x-observation-consent')!='model-metadata-v1':raise HTTPException(403,'Separate metadata/feedback storage consent required')
 if request.headers.get('content-type','').split(';')[0]!='application/json':raise HTTPException(415,'Expected JSON')
 data=bytearray()
 try:
  async with asyncio.timeout(15):
   async for chunk in request.stream():
    data.extend(chunk)
    if len(data)>4096:raise HTTPException(413,'Metadata too large')
  return model.model_validate_json(data)
 except (ValidationError,ClientDisconnect):raise HTTPException(422,'Invalid metadata') from None
 except TimeoutError:raise HTTPException(408,'Metadata deadline') from None

@router.post('/v1/me/observations',status_code=201)
async def save(request:Request):
 store,token=context(request);data=await payload(request,ObservationInput);return operation(store.save,token,data)
@router.get('/v1/me/observations')
async def listing(request:Request,pet_id:str,device_id:str,condition:str,source_kind:str='pretrained_model'):
 store,token=context(request);return operation(store.listing,token,pet_id,device_id,condition,source_kind)
@router.delete('/v1/me/observations/{ident}',status_code=204)
async def erase(ident:str,request:Request):
 store,token=context(request)
 if request.headers.get('x-delete-confirm')!='delete-observation':raise HTTPException(400,'Confirmation required')
 operation(store.delete_observation,token,ident)
@router.post('/v1/me/observations/{ident}/feedback',status_code=201)
async def feedback(ident:str,request:Request):
 store,token=context(request);data=await payload(request,FeedbackInput);return operation(store.feedback,token,ident,data.reason)

@router.delete('/v1/me/observations/{ident}/feedback',status_code=204)
async def withdraw_feedback(ident:str,request:Request):
 store,token=context(request)
 if request.headers.get('x-delete-confirm')!='delete-feedback':raise HTTPException(400,'Confirmation required')
 operation(store.delete_feedback,token,ident)
