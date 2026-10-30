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

class Note(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    pet:str=Field(min_length=1,max_length=40)
    context:str=Field(max_length=500)
    # Only guardian notes are accepted; no client-supplied verified AI results.

class Store:
    def __init__(self,path,clock=time.time):
        self.path=Path(path);self.clock=clock
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, owner TEXT NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY, owner TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL, pet TEXT NOT NULL, context TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS notes_owner ON notes(owner,created);
            PRAGMA user_version=1;
            ''')
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
            db.execute('DELETE FROM notes WHERE expires<=?',(self.clock(),))
            db.execute('DELETE FROM sessions WHERE expires<=?',(self.clock(),))
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
            r=db.execute('SELECT owner FROM sessions WHERE token_hash=? AND expires>?',
              (hashlib.sha256(token.encode()).hexdigest(),self.clock())).fetchone()
            if not r:raise PermissionError('Session expired or revoked')
            owner=r[0];db.execute('DELETE FROM notes WHERE expires<=?',(self.clock(),))
            if db.execute('SELECT count(*) FROM notes WHERE owner=?',(owner,)).fetchone()[0]>=500:
                raise ValueError('Stored note limit reached')
            item={'id':str(uuid.uuid4()),'created':self.clock(),'expires':self.clock()+RETENTION,**note.model_dump()}
            db.execute('INSERT INTO notes VALUES(?,?,?,?,?,?)',(item['id'],owner,item['created'],item['expires'],note.pet,note.context))
        return {**item,'origin':'guardian_note','training_approved':False}
    def list(self,owner,offset=0):
        self.purge()
        with self.connect() as db:
            rows=db.execute('SELECT id,created,expires,pet,context FROM notes WHERE owner=? ORDER BY created DESC,id DESC LIMIT 100 OFFSET ?',(owner,offset)).fetchall()
        return [dict(zip(['id','created','expires','pet','context'],r),origin='guardian_note',training_approved=False) for r in rows]
    def delete(self,owner,note_id):
        with self.connect() as db:
            return db.execute('DELETE FROM notes WHERE owner=? AND id=?',(owner,note_id)).rowcount>0
    def delete_account(self,owner):
        with self.connect() as db:
            db.execute('DELETE FROM notes WHERE owner=?',(owner,))
            db.execute('DELETE FROM sessions WHERE owner=?',(owner,))

def access(request):
    path=os.getenv('PETSENSE_ACCOUNT_DB','')
    if not path:raise HTTPException(503,'Account notes are not configured')
    try:store=Store(path)
    except (OSError,sqlite3.Error):raise HTTPException(503,'Account store unavailable') from None
    token=request.headers.get('x-petsense-session','')
    owner=store.authenticate(token)
    if not owner:raise HTTPException(401,'Session expired, revoked or missing')
    return store,owner,token

@router.get('/v1/me/notes')
async def get_notes(request:Request,offset:int=0):
    store,owner,_=access(request)
    if not 0<=offset<=500:raise HTTPException(422,'Invalid offset')
    return {'items':store.list(owner,offset),'retention_days':30,'limit':100}

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
