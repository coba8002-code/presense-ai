"""Local operator review cards; no web approval role or automatic training rights."""
import argparse
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator
from backend.accounts import SCHEMA_VERSION

class Strict(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
class Review(Strict):
 reviewer:str=Field(min_length=1,max_length=160)
 qualification_evidence:str=Field(min_length=1,max_length=600)
 verdict:Literal['supports','contradicts','needs_more_evidence']
 model_identity_hidden:Literal[True]
 @field_validator('model_identity_hidden',mode='before')
 @classmethod
 def blind(cls,value):
  if value is not True:raise ValueError('Explicit identity-blind attestation required')
  return value
class Card(Strict):
 observation_id:str=Field(pattern=r'^[a-f0-9-]{36}$')
 observation_payload_sha256:str=Field(pattern=r'^[a-f0-9]{64}$')
 feedback_sha256:str=Field(pattern=r'^[a-f0-9]{64}$')
 reviews:list[Review]=Field(min_length=2,max_length=2)

def feedback_digest(row):
 data={k:row[k] for k in ('id','owner','observation_id','created','reason')}
 return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def review_card(path,document,*,write=False,now=None):
 card=Card.model_validate(document);now=time.time() if now is None else now
 if type(write) is not bool or type(now) not in (int,float) or not math.isfinite(now):raise ValueError('Explicit review mode and finite clock required')
 if len({r.reviewer for r in card.reviews})!=2 or any(r.reviewer!=r.reviewer.strip() or not r.reviewer.strip() or not r.qualification_evidence.strip() for r in card.reviews):raise ValueError('Distinct explicit reviewer evidence required')
 path=Path(path)
 if not path.is_file() or path.is_symlink():raise ValueError('Existing local database required')
 digest=hashlib.sha256(json.dumps(card.model_dump(),sort_keys=True,separators=(',',':')).encode()).hexdigest()
 status='disputed' if card.reviews[0].verdict!=card.reviews[1].verdict else ('needs_more_evidence' if card.reviews[0].verdict=='needs_more_evidence' else 'reviewed_not_training_approved')
 with closing(sqlite3.connect(path.resolve().as_uri()+('?mode=rw' if write else '?mode=ro'),uri=True)) as db:
  db.row_factory=sqlite3.Row
  with db:
   db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
   if db.execute('PRAGMA user_version').fetchone()[0]!=SCHEMA_VERSION:raise ValueError('Initialize current schema separately')
   row=db.execute('SELECT f.*,m.payload,m.payload_hash,m.created AS observation_created,m.expires,p.expires AS pet_expires FROM observation_feedback f JOIN model_observations m ON f.observation_id=m.id AND f.owner=m.owner JOIN pets p ON p.id=m.pet_id AND p.owner=m.owner WHERE m.id=?',(card.observation_id,)).fetchone()
   if not row or row['expires']<=now or row['pet_expires']<=now or row['observation_created']>now:raise ValueError('Expired or missing review source')
   if row['payload_hash']!=card.observation_payload_sha256 or hashlib.sha256(row['payload'].encode()).hexdigest()!=row['payload_hash'] or feedback_digest(row)!=card.feedback_sha256:raise ValueError('Stale or changed feedback/observation')
   previous=json.loads(row['review_payload']) if row['review_payload'] else None
   if previous and previous['card_sha256']!=digest:raise ValueError('Existing immutable review differs; no overwrite')
   written=False
   if write and not previous:
    summary=json.dumps({'card_sha256':digest,'reviewed_at':now,'qualification_verified':False,'training_approved':False},sort_keys=True)
    db.execute('UPDATE observation_feedback SET status=?,review_payload=? WHERE id=?',(status,summary,row['id']));written=True
 return {'observation_id':card.observation_id,'card_sha256':digest,'status':status,'written':written,'reviewer_qualifications_verified':False,'training_approved':False,'limitations':['Reviewer evidence is an assertion, not credential verification','Review agreement is not ground truth or data-license approval','No new web role, automatic labels or training operation']}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True);p.add_argument('--card',type=Path,required=True);p.add_argument('--write-review',action='store_true');a=p.parse_args()
 if a.card.stat().st_size>16000:raise ValueError('Bounded review card required')
 print(json.dumps(review_card(a.db,json.loads(a.card.read_text()),write=a.write_review),allow_nan=False))
if __name__=='__main__':main()
