"""First-party beta credentials; standard scrypt and one-time offline recovery codes."""
import hashlib
import re
import secrets
import sqlite3
import uuid
from backend.accounts import Store

SESSION_TTL=86400
class AuthLimit(ValueError):pass
class AuthBusy(ValueError):pass

def email_value(value):
    if not isinstance(value,str):raise ValueError('Invalid email')
    value=value.strip().lower()
    if len(value)>254 or not re.fullmatch(r'[a-z0-9][a-z0-9._+-]{0,63}@(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}',value):raise ValueError('Invalid email')
    return value

def password_value(value):
    if not isinstance(value,str) or not 15<=len(value)<=128 or len(value.encode())>512 or not value.strip():raise ValueError('Invalid password length')
    return value

def derive(password,salt):
    return hashlib.scrypt(password_value(password).encode(),salt=salt,n=32768,r=8,p=3,dklen=32,maxmem=64*1024*1024).hex()

def digest(value):return hashlib.sha256(value.encode()).hexdigest()

class AuthStore(Store):
    def _member_email(self,email):
        with self.connect() as db:
            db.row_factory=sqlite3.Row
            row=db.execute('SELECT * FROM members WHERE email=?',(email,)).fetchone()
            return dict(row) if row else None

    def _verify(self,row,password):
        actual=derive(password,bytes.fromhex(row['password_salt']) if row else bytes(16))
        matched=secrets.compare_digest(actual,row['password_hash'] if row else '0'*64)
        return bool(row and matched)

    def _session(self,db,owner):
        token=secrets.token_urlsafe(32);token_hash=digest(token)
        db.execute('DELETE FROM sessions WHERE expires<=?',(self.clock(),))
        db.execute('INSERT INTO sessions VALUES(?,?,?)',(token_hash,owner,self.clock()+SESSION_TTL))
        db.execute('DELETE FROM sessions WHERE owner=? AND token_hash!=? AND token_hash NOT IN (SELECT token_hash FROM sessions WHERE owner=? AND token_hash!=? ORDER BY expires DESC,token_hash LIMIT 4)',(owner,token_hash,owner,token_hash))
        return token

    def register(self,email,password,terms_version,privacy_version):
        email=email_value(email);password_value(password)
        if any(not isinstance(v,str) or not v.strip() or len(v)>100 for v in [terms_version,privacy_version]):raise ValueError('Policy versions required')
        salt=secrets.token_bytes(16);hashed=derive(password,salt);code=secrets.token_urlsafe(32);owner=str(uuid.uuid4())
        try:
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('INSERT INTO members VALUES(?,?,?,?,?,?,?,?,?)',(owner,email,salt.hex(),hashed,digest(code),self.clock(),self.clock(),terms_version,privacy_version))
                token=self._session(db,owner)
        except sqlite3.IntegrityError:raise ValueError('Account registration unavailable') from None
        return {'owner':owner,'token':token,'recovery_code':code}

    def login(self,email,password):
        row=self._member_email(email_value(email))
        if not self._verify(row,password):raise PermissionError('Invalid credentials')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM members WHERE owner=? AND password_hash=?',(row['owner'],row['password_hash'])).fetchone():raise PermissionError('Credentials changed')
            return row['owner'],self._session(db,row['owner'])

    def member(self,token):
        with self.connect() as db:
            owner=self.session_owner(db,token)
            row=db.execute('SELECT email FROM members WHERE owner=?',(owner,)).fetchone()
            if not row:raise PermissionError('Web account required')
            return {'email':row[0],'email_verified':False}

    def logout(self,token):
        with self.connect() as db:db.execute('DELETE FROM sessions WHERE token_hash=?',(digest(token),))

    def recover(self,email,code,password):
        email=email_value(email);password_value(password);row=self._member_email(email)
        salt=secrets.token_bytes(16);hashed=derive(password,salt)
        valid=isinstance(code,str) and bool(re.fullmatch(r'[A-Za-z0-9_-]{43}',code))
        match=secrets.compare_digest(digest(code) if valid else '0'*64,row['recovery_hash'] if row else '0'*64)
        if not row or not valid or not match:raise PermissionError('Invalid recovery credentials')
        fresh=secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            changed=db.execute('UPDATE members SET password_salt=?,password_hash=?,recovery_hash=?,updated=? WHERE owner=? AND recovery_hash=? AND password_hash=?',
                (salt.hex(),hashed,digest(fresh),self.clock(),row['owner'],row['recovery_hash'],row['password_hash'])).rowcount
            if changed!=1:raise PermissionError('Recovery credentials changed')
            db.execute('DELETE FROM sessions WHERE owner=?',(row['owner'],))
            self._purge(db)
        return fresh

    def change(self,token,old_password,new_password):
        member=self.member(token);row=self._member_email(member['email'])
        if not self._verify(row,old_password):raise PermissionError('Invalid credentials')
        salt=secrets.token_bytes(16);hashed=derive(new_password,salt);code=secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');owner=self.session_owner(db,token)
            if db.execute('UPDATE members SET password_salt=?,password_hash=?,recovery_hash=?,updated=? WHERE owner=? AND password_hash=?',
                (salt.hex(),hashed,digest(code),self.clock(),owner,row['password_hash'])).rowcount!=1:raise PermissionError('Credentials changed')
            db.execute('DELETE FROM sessions WHERE owner=?',(owner,));self._purge(db)
            return self._session(db,owner),code

    def delete_member(self,token,password):
        member=self.member(token);row=self._member_email(member['email'])
        if not self._verify(row,password):raise PermissionError('Invalid credentials')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');owner=self.session_owner(db,token)
            if not db.execute('SELECT 1 FROM members WHERE owner=? AND password_hash=?',(owner,row['password_hash'])).fetchone():raise PermissionError('Credentials changed')
            self._erase_owner(db,owner)

    def reserve(self,peer,email,kind):
        if kind not in ('signup','login','recover','change','delete'):raise ValueError('Invalid auth action')
        now=self.clock();peer_bucket='peer:'+kind+':'+digest(peer)
        limits=[('global',20,60),(peer_bucket,3 if kind=='signup' else 5 if kind=='recover' else 10,3600 if kind=='signup' else 900 if kind=='recover' else 300),('identity:'+digest(email_value(email)),10,900)]
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');db.execute('DELETE FROM auth_limits WHERE window<?',(now-86400,));db.execute('DELETE FROM auth_leases WHERE expires<=?',(now,))
            for bucket,cap,seconds in limits:
                window=int(now//seconds)*seconds;row=db.execute('SELECT window,count FROM auth_limits WHERE bucket=?',(bucket,)).fetchone()
                if row and row[0]==window and row[1]>=cap:raise AuthLimit('Authentication rate limit')
                count=row[1]+1 if row and row[0]==window else 1
                db.execute('INSERT OR REPLACE INTO auth_limits VALUES(?,?,?)',(bucket,window,count))
            if db.execute('SELECT 1 FROM auth_leases').fetchone():raise AuthBusy('Password service busy')
            lease=str(uuid.uuid4());db.execute('INSERT INTO auth_leases VALUES(?,?)',(lease,now+45))
            return lease

    def release(self,lease):
        with self.connect() as db:db.execute('DELETE FROM auth_leases WHERE id=?',(lease,))
