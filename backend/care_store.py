"""Single-use invitations and bounded viewer grants for one dog's journal."""
import hashlib
import secrets
import uuid
from backend.journal_store import JournalStore


class CareStore(JournalStore):
    @staticmethod
    def grant_view(row):
        return {key:row[key] for key in ('id','pet_id','created','expires','accepted')} | {'role':'viewer','status':'accepted' if row['recipient'] else 'pending'}

    def invite(self,token,pet_id,days):
        if type(days) is not int or days not in (1,7):raise ValueError('Invalid sharing period')
        with self.connect() as db:
            owner=self._begin(db,token);pet=self._pet(db,owner,pet_id)
            total=db.execute('SELECT count(*) FROM care_shares WHERE owner=?',(owner,)).fetchone()[0]
            count=db.execute('SELECT count(*) FROM care_shares WHERE owner=? AND pet_id=?',(owner,pet_id)).fetchone()[0]
            if total>=100 or count>=20:raise ValueError('Sharing limit reached')
            now=self.clock();code=secrets.token_urlsafe(32);share_id=str(uuid.uuid4())
            expires=min(now+days*86400,pet['expires']);invite_expires=min(now+86400,expires)
            db.execute('INSERT INTO care_shares VALUES(?,?,?,?,?,?,?,?,?)',(share_id,owner,pet_id,hashlib.sha256(code.encode()).hexdigest(),None,now,invite_expires,expires,None))
            row=db.execute('SELECT * FROM care_shares WHERE id=?',(share_id,)).fetchone()
            return {**self.grant_view(row),'code':code,'invite_expires':invite_expires}

    def accept(self,token,code):
        if not isinstance(code,str) or len(code)!=43:raise KeyError('Invitation unavailable')
        with self.connect() as db:
            recipient=self._begin(db,token)
            row=db.execute('SELECT * FROM care_shares WHERE code_hash=?',(hashlib.sha256(code.encode()).hexdigest(),)).fetchone()
            if not row or row['owner']==recipient or row['recipient'] not in (None,recipient):raise KeyError('Invitation unavailable')
            if row['recipient'] is None:
                if row['invite_expires']<=self.clock():raise KeyError('Invitation unavailable')
                if db.execute('SELECT count(*) FROM care_shares WHERE recipient=?',(recipient,)).fetchone()[0]>=100:raise ValueError('Sharing limit reached')
                db.execute('UPDATE care_shares SET recipient=?,accepted=? WHERE id=?',(recipient,self.clock(),row['id']))
                row=db.execute('SELECT * FROM care_shares WHERE id=?',(row['id'],)).fetchone()
            return self.grant_view(row)

    def list_shares(self,token):
        with self.connect() as db:
            actor=self._begin(db,token)
            rows=db.execute('SELECT s.*,p.name FROM care_shares s JOIN pets p ON p.id=s.pet_id AND p.owner=s.owner WHERE s.owner=? OR s.recipient=? ORDER BY s.created DESC,s.id',(actor,actor)).fetchall()
            return {side:[{**self.grant_view(row),'pet_name':row['name']} for row in rows if row[column]==actor] for side,column in [('sent','owner'),('received','recipient')]}

    def revoke(self,token,share_id):
        with self.connect() as db:
            actor=self._begin(db,token)
            if not db.execute('DELETE FROM care_shares WHERE id=? AND (owner=? OR recipient=?)',(share_id,actor,actor)).rowcount:raise KeyError('Share unavailable')

    def _grant(self,db,actor,share_id):
        row=db.execute('SELECT s.* FROM care_shares s JOIN pets p ON p.id=s.pet_id AND p.owner=s.owner WHERE s.id=? AND s.recipient=? AND s.expires>? AND p.expires>?',(share_id,actor,self.clock(),self.clock())).fetchone()
        if not row:raise KeyError('Share unavailable')
        return row

    def shared_cases(self,token,share_id,offset=0):
        if type(offset) is not int or not 0<=offset<=500:raise ValueError('Invalid offset')
        with self.connect() as db:
            actor=self._begin(db,token);grant=self._grant(db,actor,share_id)
            params=(grant['owner'],grant['pet_id'])
            total=db.execute('SELECT count(*) FROM journal_cases WHERE owner=? AND pet_id=?',params).fetchone()[0]
            rows=db.execute('SELECT * FROM journal_cases WHERE owner=? AND pet_id=? ORDER BY observed DESC,id DESC LIMIT 50 OFFSET ?',(*params,offset)).fetchall()
            return {'items':[self.view(row) for row in rows],'total':total,'next_offset':offset+50 if offset+50<total else None}

    def shared_case(self,token,share_id,case_id):
        with self.connect() as db:
            actor=self._begin(db,token);grant=self._grant(db,actor,share_id)
            row=self._case(db,grant['owner'],case_id)
            if row['pet_id']!=grant['pet_id']:raise KeyError('Case unavailable')
            follows=db.execute('SELECT id,created,payload FROM journal_followups WHERE owner=? AND case_id=? ORDER BY observed,id LIMIT 20',(grant['owner'],case_id)).fetchall()
            import json
            return {**self.view(row),'followups':[{'id':r['id'],'created':r['created'],'data':json.loads(r['payload']),'kind':'guardian_report','model_analysis':False,'training_approved':False} for r in follows]}
