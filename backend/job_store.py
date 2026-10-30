"""Single-PC durable AST queue. Explicit temporary media consent is an HTTP prerequisite."""
from contextlib import contextmanager
import hashlib
import json
import re
import sqlite3
import uuid
from backend.accounts import Store
from backend.audio_process import validate_result, WorkerError
from training.pretrained_audio import read_wav_bytes, MODEL, REVISION

class Conflict(ValueError):pass
class Capacity(ValueError):pass


class JobStore(Store):
    @contextmanager
    def connect(self):
        with super().connect() as db:
            db.row_factory=sqlite3.Row
            yield db

    @staticmethod
    def view(row,reused=None):
        data={key:row[key] for key in ('id','pet_id','created','expires','raw_deadline','status','error')}
        data['result']=json.loads(row['result']) if row['status']=='succeeded' and row['result'] else None
        data['training_approved']=False
        if reused is not None:data['reused']=reused
        return data

    def enqueue(self,token,pet_id,key,raw):
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9._-]{16,128}',key):raise ValueError('Invalid idempotency key')
        _,digest=read_wav_bytes(raw)
        key_hash=hashlib.sha256(key.encode()).hexdigest()
        fingerprint=hashlib.sha256(json.dumps([pet_id,digest,MODEL,REVISION,'temporary-audio-v1']).encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');owner=self.session_owner(db,token);self._purge(db);self._pet(db,owner,pet_id)
            old=db.execute('SELECT * FROM audio_jobs WHERE owner=? AND key_hash=?',(owner,key_hash)).fetchone()
            if old:
                if old['payload_hash']!=fingerprint:raise Conflict('Idempotency content changed')
                return self.view(old,True)
            now=self.clock();day=int(now//86400)
            count=db.execute('SELECT count FROM audio_usage WHERE owner=? AND day=?',(owner,day)).fetchone()
            if count and count[0]>=20:raise Capacity('Daily job quota reached')
            if db.execute("SELECT count(*) FROM audio_jobs WHERE owner=? AND status IN ('queued','running')",(owner,)).fetchone()[0]>=2:raise Capacity('Owner pending limit')
            if db.execute("SELECT count(*) FROM audio_jobs WHERE status IN ('queued','running')").fetchone()[0]>=8:raise Capacity('Global pending limit')
            job_id=str(uuid.uuid4())
            db.execute("INSERT INTO audio_jobs(id,owner,pet_id,key_hash,payload_hash,session_hash,created,expires,raw_deadline,status,media) VALUES(?,?,?,?,?,?,?,?,?,'queued',?)",
                (job_id,owner,pet_id,key_hash,fingerprint,hashlib.sha256(token.encode()).hexdigest(),now,now+86400,now+900,raw))
            db.execute('INSERT INTO audio_usage VALUES(?,?,1) ON CONFLICT(owner,day) DO UPDATE SET count=count+1',(owner,day))
            return self.view(db.execute('SELECT * FROM audio_jobs WHERE id=?',(job_id,)).fetchone(),False)

    def get(self,token,job_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');owner=self.session_owner(db,token);self._purge(db)
            row=db.execute('SELECT * FROM audio_jobs WHERE id=? AND owner=?',(job_id,owner)).fetchone()
            if not row:raise KeyError('Job not found')
            return self.view(row)

    def list_jobs(self,token):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');owner=self.session_owner(db,token);self._purge(db)
            rows=db.execute('SELECT * FROM audio_jobs WHERE owner=? ORDER BY created DESC,id DESC LIMIT 20',(owner,)).fetchall()
            return [self.view(row) for row in rows]

    def cancel(self,token,job_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');owner=self.session_owner(db,token)
            if not db.execute('SELECT 1 FROM audio_jobs WHERE id=? AND owner=?',(job_id,owner)).fetchone():raise KeyError('Job not found')
            db.execute("UPDATE audio_jobs SET status='cancelled',media=NULL,result=NULL,error='client_cancelled',lease=NULL WHERE id=? AND owner=?",(job_id,owner))
            return self.view(db.execute('SELECT * FROM audio_jobs WHERE id=?',(job_id,)).fetchone())

    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');self._purge(db);now=self.clock()
            if db.execute("SELECT 1 FROM audio_jobs WHERE status='running'").fetchone():return None
            row=db.execute("SELECT * FROM audio_jobs WHERE status='queued' ORDER BY created,id LIMIT 1").fetchone()
            if not row:return None
            lease=str(uuid.uuid4())
            db.execute("UPDATE audio_jobs SET status='running',lease=?,lease_until=? WHERE id=?",(lease,now+90,row['id']))
            return {'id':row['id'],'lease':lease,'raw':bytes(row['media'])}

    def keep_running(self,claim):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');self._purge(db)
            return bool(db.execute("SELECT 1 FROM audio_jobs WHERE id=? AND lease=? AND status='running' AND lease_until>?",(claim['id'],claim['lease'],self.clock())).fetchone())

    def finish(self,claim,result=None,error=None):
        if result is not None:
            try:validate_result(claim['raw'],json.dumps(result,allow_nan=False).encode())
            except (WorkerError,ValueError,TypeError):raise ValueError('Invalid model result') from None
        if error not in (None,'model_unavailable','deadline_exceeded','worker_lost'):raise ValueError('Invalid worker error')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');self._purge(db)
            return db.execute("UPDATE audio_jobs SET status=?,result=?,error=?,media=NULL,lease=NULL WHERE id=? AND lease=? AND status='running' AND lease_until>?",
                ('succeeded' if result is not None else 'failed',json.dumps(result,allow_nan=False) if result is not None else None,error,claim['id'],claim['lease'],self.clock())).rowcount==1
