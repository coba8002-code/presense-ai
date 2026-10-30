"""Owner-scoped guardian reports and followups; no model or efficacy inference."""
import hashlib
import json
import re
import sqlite3
import uuid
from backend.accounts import Store

CONSENT='journal-storage-v1'
class JournalLimit(ValueError):pass
class JournalConflict(ValueError):pass


def fingerprint(data,key):
    if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9._-]{16,128}',key):raise ValueError('Invalid idempotency key')
    payload=data.model_dump_json()
    return payload,hashlib.sha256(key.encode()).hexdigest(),hashlib.sha256(payload.encode()).hexdigest()


class JournalStore(Store):
    @staticmethod
    def view(row):
        result={key:row[key] for key in ['id','pet_id','pet_name','created','expires','consent_version']}
        return {**result,'data':json.loads(row['payload']),'kind':'guardian_report','model_analysis':False,'training_approved':False}

    def _begin(self,db,token):
        db.row_factory=sqlite3.Row;db.execute('BEGIN IMMEDIATE')
        owner=self.session_owner(db,token);self._purge(db)
        return owner

    def _case(self,db,owner,case_id):
        row=db.execute('SELECT * FROM journal_cases WHERE id=? AND owner=? AND expires>?',(case_id,owner,self.clock())).fetchone()
        if not row:raise KeyError('Case not found')
        return row

    def _time(self,value):
        observed=value.timestamp();now=self.clock()
        if not now-90*86400<=observed<=now+300:raise ValueError('Observation time outside permitted range')
        return observed

    def create_case(self,token,data,key):
        payload,key_hash,payload_hash=fingerprint(data,key)
        with self.connect() as db:
            owner=self._begin(db,token);pet=self._pet(db,owner,data.pet_id)
            old=db.execute('SELECT * FROM journal_cases WHERE owner=? AND key_hash=?',(owner,key_hash)).fetchone()
            if old:
                if old['payload_hash']!=payload_hash:raise JournalConflict('Idempotency conflict')
                return {**self.view(old),'reused':True}
            observed=self._time(data.observed_at)
            if db.execute('SELECT count(*) FROM journal_cases WHERE owner=?',(owner,)).fetchone()[0]>=500:raise JournalLimit('Case limit reached')
            now=self.clock();expires=now+data.retention_days*86400;case_id=str(uuid.uuid4())
            db.execute('INSERT INTO journal_cases VALUES(?,?,?,?,?,?,?,?,?,?,?)',(case_id,owner,data.pet_id,pet['name'],observed,now,expires,payload,CONSENT,key_hash,payload_hash))
            db.execute('UPDATE pets SET expires=MAX(expires,?) WHERE id=? AND owner=?',(expires,data.pet_id,owner))
            return {**self.view(self._case(db,owner,case_id)),'reused':False}

    def list_cases(self,token,pet_id=None,offset=0):
        if not isinstance(offset,int) or not 0<=offset<=500:raise ValueError('Invalid offset')
        with self.connect() as db:
            owner=self._begin(db,token)
            if pet_id:self._pet(db,owner,pet_id)
            total=db.execute('SELECT count(*) FROM journal_cases WHERE owner=? AND (? IS NULL OR pet_id=?)',(owner,pet_id,pet_id)).fetchone()[0]
            rows=db.execute('SELECT c.*,(SELECT count(*) FROM journal_followups f WHERE f.case_id=c.id AND f.owner=c.owner) AS followup_count FROM journal_cases c WHERE c.owner=? AND (? IS NULL OR c.pet_id=?) ORDER BY c.observed DESC,c.id DESC LIMIT 50 OFFSET ?',(owner,pet_id,pet_id,offset)).fetchall()
            items=[{**self.view(row),'followup_count':row['followup_count']} for row in rows]
            return {'items':items,'total':total,'next_offset':offset+50 if offset+50<total else None}

    def get_case(self,token,case_id):
        with self.connect() as db:
            owner=self._begin(db,token);row=self._case(db,owner,case_id)
            rows=db.execute('SELECT id,observed,created,payload FROM journal_followups WHERE owner=? AND case_id=? ORDER BY observed,id LIMIT 20',(owner,case_id)).fetchall()
            followups=[{'id':r['id'],'created':r['created'],'data':json.loads(r['payload']),'kind':'guardian_report','model_analysis':False,'training_approved':False} for r in rows]
            return {**self.view(row),'followups':followups}

    def add_followup(self,token,case_id,data,key):
        payload,key_hash,payload_hash=fingerprint(data,key)
        with self.connect() as db:
            owner=self._begin(db,token);case=self._case(db,owner,case_id)
            old=db.execute('SELECT * FROM journal_followups WHERE owner=? AND case_id=? AND key_hash=?',(owner,case_id,key_hash)).fetchone()
            if old:
                if old['payload_hash']!=payload_hash:raise JournalConflict('Idempotency conflict')
                return {'id':old['id'],'reused':True}
            observed=self._time(data.observed_at)
            if observed<case['observed']:raise ValueError('Followup precedes observation')
            if db.execute('SELECT count(*) FROM journal_followups WHERE owner=? AND case_id=?',(owner,case_id)).fetchone()[0]>=20:raise JournalLimit('Followup limit reached')
            followup_id=str(uuid.uuid4())
            db.execute('INSERT INTO journal_followups VALUES(?,?,?,?,?,?,?,?)',(followup_id,owner,case_id,observed,self.clock(),payload,key_hash,payload_hash))
            return {'id':followup_id,'reused':False}

    def delete_case(self,token,case_id):
        with self.connect() as db:
            owner=self._begin(db,token);self._case(db,owner,case_id)
            db.execute('DELETE FROM journal_followups WHERE owner=? AND case_id=?',(owner,case_id))
            db.execute('DELETE FROM journal_cases WHERE owner=? AND id=?',(owner,case_id))
