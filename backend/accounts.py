"""Single-PC prototype sessions and owner-scoped notes, not production identity."""
from contextlib import contextmanager
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

router=APIRouter()
RETENTION=30*86400
SCHEMA_VERSION=5

class Note(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    pet:str=Field(min_length=1,max_length=40)
    context:str=Field(max_length=500)
    pet_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
    # Only guardian notes are accepted; no client-supplied verified AI results.

class Store:
    def __init__(self,path,clock=time.time):
        self.path=Path(path);self.clock=clock
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if version>SCHEMA_VERSION:raise sqlite3.DatabaseError('Unsupported account schema')
            if version<SCHEMA_VERSION:
                db.execute('BEGIN IMMEDIATE')
                if db.execute('PRAGMA user_version').fetchone()[0]>SCHEMA_VERSION:raise sqlite3.DatabaseError('Unsupported account schema')
                db.execute('CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, owner TEXT NOT NULL, expires REAL NOT NULL)')
                db.execute('CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY, owner TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL, pet TEXT NOT NULL, context TEXT NOT NULL)')
                if 'pet_id' not in {r[1] for r in db.execute('PRAGMA table_info(notes)')}:
                    db.execute('ALTER TABLE notes ADD COLUMN pet_id TEXT')
                db.execute('CREATE INDEX IF NOT EXISTS notes_owner ON notes(owner,created)')
                db.execute('CREATE INDEX IF NOT EXISTS notes_pet ON notes(owner,pet_id)')
                db.execute('CREATE TABLE IF NOT EXISTS pets(id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL, expires REAL NOT NULL)')
                db.execute('CREATE INDEX IF NOT EXISTS pets_owner ON pets(owner)')
                db.execute('CREATE TABLE IF NOT EXISTS audio_jobs(id TEXT PRIMARY KEY,owner TEXT NOT NULL,pet_id TEXT NOT NULL,key_hash TEXT NOT NULL,payload_hash TEXT NOT NULL,session_hash TEXT NOT NULL,created REAL NOT NULL,expires REAL NOT NULL,raw_deadline REAL NOT NULL,status TEXT NOT NULL,media BLOB,result TEXT,error TEXT,lease TEXT,lease_until REAL,UNIQUE(owner,key_hash))')
                db.execute('CREATE INDEX IF NOT EXISTS audio_jobs_owner ON audio_jobs(owner,created)')
                db.execute('CREATE TABLE IF NOT EXISTS audio_usage(owner TEXT NOT NULL,day INTEGER NOT NULL,count INTEGER NOT NULL,PRIMARY KEY(owner,day))')
                db.execute('CREATE TABLE IF NOT EXISTS members(owner TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE,password_salt TEXT NOT NULL,password_hash TEXT NOT NULL,recovery_hash TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL,terms_version TEXT NOT NULL,privacy_version TEXT NOT NULL)')
                db.execute('CREATE TABLE IF NOT EXISTS auth_limits(bucket TEXT PRIMARY KEY,window REAL NOT NULL,count INTEGER NOT NULL)')
                db.execute('CREATE TABLE IF NOT EXISTS auth_leases(id TEXT PRIMARY KEY,expires REAL NOT NULL)')
                from backend.journal_schema import create_tables
                create_tables(db)
                db.execute('PRAGMA user_version='+str(SCHEMA_VERSION))
        if os.name=='posix':os.chmod(self.path,0o600)
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=5)
        db.execute('PRAGMA secure_delete=ON')
        try:
            with db:
                yield db
        finally:
            db.close()
    def purge(self):
        with self.connect() as db:
            self._purge(db)
    def _purge(self,db):
        now=self.clock()
        from backend.journal_schema import purge
        purge(db,now)
        db.execute('DELETE FROM auth_limits WHERE window<?',(now-86400,))
        db.execute('DELETE FROM auth_leases WHERE expires<=?',(now,))
        db.execute('DELETE FROM audio_jobs WHERE expires<=? OR pet_id IN (SELECT id FROM pets WHERE expires<=?)',(now,now))
        db.execute("UPDATE audio_jobs SET status='expired',media=NULL,result=NULL,error='expired',lease=NULL WHERE status IN ('queued','running') AND raw_deadline<=?",(now,))
        db.execute("UPDATE audio_jobs SET status='cancelled',media=NULL,result=NULL,error='session_revoked',lease=NULL WHERE status IN ('queued','running') AND NOT EXISTS (SELECT 1 FROM sessions s WHERE s.token_hash=audio_jobs.session_hash AND s.owner=audio_jobs.owner AND s.expires>?)",(now,))
        db.execute("UPDATE audio_jobs SET status='failed',media=NULL,result=NULL,error='worker_lost',lease=NULL WHERE status='running' AND lease_until<=?",(now,))
        db.execute('DELETE FROM audio_usage WHERE day<?',(int(now//86400)-1,))
        db.execute('DELETE FROM notes WHERE expires<=? OR pet_id IN (SELECT id FROM pets WHERE expires<=?)',(now,now))
        db.execute('DELETE FROM pets WHERE expires<=?',(now,))
        db.execute('DELETE FROM sessions WHERE expires<=?',(now,))
    def session_owner(self,db,token):
        if not isinstance(token,str) or not 20<=len(token)<=200:raise PermissionError('Invalid session')
        row=db.execute('SELECT owner FROM sessions WHERE token_hash=? AND expires>?',
            (hashlib.sha256(token.encode()).hexdigest(),self.clock())).fetchone()
        if not row:raise PermissionError('Session expired or revoked')
        return row[0]
    def _pet(self,db,owner,pet_id):
        row=db.execute('SELECT id,name,created,updated,expires FROM pets WHERE id=? AND owner=? AND expires>?',
            (pet_id,owner,self.clock())).fetchone()
        if not row:raise KeyError('Pet not found')
        return dict(zip(['id','name','created','updated','expires'],row),species='dog')
    def pet_list(self,token):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');owner=self.session_owner(db,token);self._purge(db)
            ids=[r[0] for r in db.execute('SELECT id FROM pets WHERE owner=? ORDER BY created,id LIMIT 20',(owner,))]
            return [self._pet(db,owner,item) for item in ids]
    def pet_create(self,token,name):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');owner=self.session_owner(db,token);self._purge(db)
            if db.execute('SELECT count(*) FROM pets WHERE owner=?',(owner,)).fetchone()[0]>=20:raise ValueError('Pet limit reached')
            pet_id=str(uuid.uuid4());now=self.clock()
            db.execute('INSERT INTO pets VALUES(?,?,?,?,?,?)',(pet_id,owner,name,now,now,now+RETENTION))
            return self._pet(db,owner,pet_id)
    def pet_update(self,token,pet_id,name):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');owner=self.session_owner(db,token);self._pet(db,owner,pet_id)
            db.execute('UPDATE pets SET name=?,updated=?,expires=MAX(expires,?) WHERE id=? AND owner=?',(name,self.clock(),self.clock()+RETENTION,pet_id,owner))
            return self._pet(db,owner,pet_id)
    def pet_delete(self,token,pet_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');owner=self.session_owner(db,token);self._pet(db,owner,pet_id)
            from backend.journal_schema import delete_pet
            delete_pet(db,owner,pet_id)
            db.execute('DELETE FROM notes WHERE owner=? AND pet_id=?',(owner,pet_id))
            db.execute('DELETE FROM audio_jobs WHERE owner=? AND pet_id=?',(owner,pet_id))
            db.execute('DELETE FROM pets WHERE owner=? AND id=?',(owner,pet_id))
    def issue(self,owner=None,ttl=86400):
        if not 60<=ttl<=604800:raise ValueError('Session lifetime must be 60 seconds to 7 days')
        owner=str(uuid.UUID(owner)) if owner else str(uuid.uuid4())
        token=secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),owner,self.clock()+ttl))
        return owner,token
    def authenticate(self,token):
        if not isinstance(token,str) or not 20<=len(token)<=200:return None
        with self.connect() as db:
            r=db.execute('SELECT owner FROM sessions WHERE token_hash=? AND expires>?',
              (hashlib.sha256(token.encode()).hexdigest(),self.clock())).fetchone()
        return r[0] if r else None
    def add(self,token,note):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            owner=self.session_owner(db,token);self._purge(db)
            if db.execute('SELECT count(*) FROM notes WHERE owner=?',(owner,)).fetchone()[0]>=500:
                raise ValueError('Stored note limit reached')
            item={'id':str(uuid.uuid4()),'created':self.clock(),'expires':self.clock()+RETENTION,**note.model_dump()}
            if note.pet_id:item['pet']=self._pet(db,owner,note.pet_id)['name']
            db.execute('INSERT INTO notes(id,owner,created,expires,pet,context,pet_id) VALUES(?,?,?,?,?,?,?)',(item['id'],owner,item['created'],item['expires'],item['pet'],note.context,note.pet_id))
        return {**item,'origin':'guardian_note','training_approved':False}
    def list(self,owner,offset=0,pet_id=None):
        self.purge()
        with self.connect() as db:
            if pet_id:self._pet(db,owner,pet_id)
            rows=db.execute('SELECT id,created,expires,pet,context,pet_id FROM notes WHERE owner=? AND (? IS NULL OR pet_id=?) ORDER BY created DESC,id DESC LIMIT 100 OFFSET ?',(owner,pet_id,pet_id,offset)).fetchall()
        return [dict(zip(['id','created','expires','pet','context','pet_id'],r),origin='guardian_note',training_approved=False) for r in rows]
    def delete(self,owner,note_id):
        with self.connect() as db:
            return db.execute('DELETE FROM notes WHERE owner=? AND id=?',(owner,note_id)).rowcount>0
    def delete_account(self,owner):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');self._erase_owner(db,owner)
    def _erase_owner(self,db,owner):
        row=db.execute('SELECT email FROM members WHERE owner=?',(owner,)).fetchone()
        if row:db.execute('DELETE FROM auth_limits WHERE bucket=?',('identity:'+hashlib.sha256(row[0].encode()).hexdigest(),))
        for table in ('journal_followups','journal_cases','notes','pets','audio_jobs','audio_usage','sessions','members'):
            db.execute('DELETE FROM '+table+' WHERE owner=?',(owner,))

def access(request):
    path=os.getenv('PETSENSE_ACCOUNT_DB','')
    if not path:raise HTTPException(503,'Account notes are not configured')
    try:store=Store(path)
    except (OSError,sqlite3.Error):raise HTTPException(503,'Account store unavailable') from None
    from backend.web_security import session_token
    token=session_token(request)
    owner=store.authenticate(token)
    if not owner:raise HTTPException(401,'Session expired, revoked or missing')
    return store,owner,token

@router.get('/v1/me/notes')
async def get_notes(request:Request,offset:int=0,pet_id:str|None=None):
    store,owner,_=access(request)
    if not 0<=offset<=500:raise HTTPException(422,'Invalid offset')
    try:items=store.list(owner,offset,pet_id)
    except KeyError:raise HTTPException(404,'Pet not found') from None
    return {'items':items,'retention_days':30,'limit':100}

@router.post('/v1/me/notes',status_code=201)
async def add_note(request:Request):
    store,_,token=access(request)
    if request.headers.get('x-storage-consent')!='true':raise HTTPException(403,'Explicit storage consent required')
    body=bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>4096:raise HTTPException(413,'Note too large')
    try:note=Note.model_validate_json(body)
    except ValidationError:raise HTTPException(422,'Invalid guardian note') from None
    if not note.pet.strip():raise HTTPException(422,'Pet name is empty')
    try:return store.add(token,note)
    except KeyError:raise HTTPException(404,'Pet not found') from None
    except PermissionError:raise HTTPException(401,'Session expired or revoked') from None
    except ValueError:raise HTTPException(409,'Stored note limit reached') from None

@router.delete('/v1/me/notes/{note_id}',status_code=204)
async def delete_note(note_id:str,request:Request):
    store,owner,_=access(request)
    if not store.delete(owner,note_id):raise HTTPException(404,'Note not found')

@router.delete('/v1/me/account',status_code=204)
async def delete_account(request:Request):
    store,owner,_=access(request)
    if request.headers.get('x-delete-confirm')!='delete-account':raise HTTPException(400,'Account deletion confirmation required')
    with store.connect() as db:
        if db.execute('SELECT 1 FROM members WHERE owner=?',(owner,)).fetchone():raise HTTPException(403,'Password reauthentication required at web account endpoint')
    store.delete_account(owner)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',required=True);p.add_argument('--owner');p.add_argument('--ttl',type=int,default=86400);p.add_argument('--token-file',required=True)
    a=p.parse_args();out=Path(a.token_file)
    # Exclusive private file: do not print bearer credentials to terminal logs.
    out.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        owner,token=Store(a.db).issue(a.owner,a.ttl)
        with os.fdopen(fd,'w') as f:json.dump({'owner':owner,'session':token,'ttl_seconds':a.ttl},f)
    except BaseException:
        try:os.close(fd)
        except OSError:pass
        out.unlink(missing_ok=True);raise
    print('Local session created in the specified private file.')

if __name__=='__main__':main()
