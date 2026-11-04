import asyncio
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from backend.accounts import Store, Note
from test_foundation import request


class PetProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'accounts.sqlite3'
        env=patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':str(self.path)})
        env.start();self.addCleanup(env.stop)
        self.store=Store(self.path);self.a,self.ta=self.store.issue();self.b,self.tb=self.store.issue()

    def call(self,method,path,token=None,**kwargs):
        headers={'X-PetSense-Session':token or self.ta,**kwargs.pop('headers',{})}
        return asyncio.run(request(method,path,headers=headers,**kwargs))

    def create(self,name='보리',token=None):
        response=self.call('POST','/v1/me/pets',token,headers={'X-Storage-Consent':'true'},json={'name':name})
        self.assertEqual(response.status_code,201,response.text)
        return response.json()

    def test_profiles_have_stable_owner_scoped_identity_even_with_same_name(self):
        first=self.create();second=self.create()
        self.assertNotEqual(first['id'],second['id']);self.assertEqual(first['species'],'dog')
        listed=self.call('GET','/v1/me/pets')
        self.assertEqual(len(listed.json()['items']),2);self.assertEqual(listed.headers['cache-control'],'no-store')
        self.assertEqual(self.call('GET','/v1/me/pets',self.tb).json()['items'],[])
        self.assertEqual(self.call('PATCH','/v1/me/pets/'+first['id'],self.tb,headers={'X-Storage-Consent':'true'},json={'name':'other'}).status_code,404)
        self.assertEqual(self.call('DELETE','/v1/me/pets/'+first['id'],self.tb,headers={'X-Delete-Confirm':'delete-pet'}).status_code,404)

    def test_consent_cat_and_owner_injection_rejected(self):
        self.assertEqual(self.call('POST','/v1/me/pets',json={'name':'dog'}).status_code,403)
        for body in [{'name':' '},{'name':'a','species':'cat'},{'name':'a','owner':self.b}]:
            self.assertEqual(self.call('POST','/v1/me/pets',headers={'X-Storage-Consent':'true'},json=body).status_code,422)
        self.assertEqual(self.call('POST','/v1/me/pets',headers={'X-Storage-Consent':'true'},content=b'x'*4097).status_code,413)
        self.assertEqual(self.call('GET','/v1/me/pets','bad').status_code,401)

    def test_note_binds_id_and_server_name_survives_rename(self):
        pet=self.create()
        note=self.call('POST','/v1/me/notes',headers={'X-Storage-Consent':'true'},json={'pet':'wrong-client-name','context':'현관','pet_id':pet['id']})
        self.assertEqual(note.status_code,201,note.text);self.assertEqual(note.json()['pet'],'보리')
        self.assertEqual(note.json()['pet_id'],pet['id'])
        changed=self.call('PATCH','/v1/me/pets/'+pet['id'],headers={'X-Storage-Consent':'true'},json={'name':'콩이'})
        self.assertEqual(changed.status_code,200);self.assertEqual(changed.json()['id'],pet['id'])
        listed=self.call('GET','/v1/me/notes?pet_id='+pet['id']).json()['items']
        self.assertEqual(len(listed),1);self.assertEqual(listed[0]['pet'],'보리')
        foreign=self.call('POST','/v1/me/notes',self.tb,headers={'X-Storage-Consent':'true'},json={'pet':'보리','context':'','pet_id':pet['id']})
        self.assertEqual(foreign.status_code,404)

    def test_profile_delete_only_removes_bound_notes(self):
        first=self.create();second=self.create()
        for pet in (first,second):
            self.call('POST','/v1/me/notes',headers={'X-Storage-Consent':'true'},json={'pet':'보리','context':'','pet_id':pet['id']})
        self.call('POST','/v1/me/notes',headers={'X-Storage-Consent':'true'},json={'pet':'보리','context':'legacy'})
        self.assertEqual(self.call('DELETE','/v1/me/pets/'+first['id']).status_code,400)
        self.assertEqual(self.call('DELETE','/v1/me/pets/'+first['id'],headers={'X-Delete-Confirm':'delete-pet'}).status_code,204)
        notes=self.call('GET','/v1/me/notes').json()['items']
        self.assertEqual(len(notes),2);self.assertEqual({r['pet_id'] for r in notes},{None,second['id']})

    def test_v1_migration_preserves_legacy_records_and_is_repeatable(self):
        old=Path(self.temp.name)/'v1.sqlite3'
        with sqlite3.connect(old) as db:
            db.executescript('CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,owner TEXT,expires REAL);CREATE TABLE notes(id TEXT PRIMARY KEY,owner TEXT,created REAL,expires REAL,pet TEXT,context TEXT);PRAGMA user_version=1;')
            db.execute('INSERT INTO notes VALUES(?,?,?,?,?,?)',('old',self.a,1,9999999999,'보리','legacy'))
        for _ in range(2):
            store=Store(old);self.assertEqual(store.list(self.a)[0]['id'],'old');self.assertIsNone(store.list(self.a)[0]['pet_id'])

    def test_account_delete_removes_profiles_and_all_sessions(self):
        self.create();other=self.create(token=self.tb)
        self.call('DELETE','/v1/me/account',headers={'X-Delete-Confirm':'delete-account'})
        self.assertEqual(self.call('GET','/v1/me/pets').status_code,401)
        self.assertEqual(self.call('GET','/v1/me/pets',self.tb).json()['items'][0]['id'],other['id'])

    def test_profile_cap_and_expiry_clean_bound_notes(self):
        for _ in range(20):self.create()
        self.assertEqual(self.call('POST','/v1/me/pets',headers={'X-Storage-Consent':'true'},json={'name':'extra'}).status_code,409)
        now=[1000];store=Store(Path(self.temp.name)/'ttl.sqlite3',clock=lambda:now[0])
        owner,token=store.issue();pet=store.pet_create(token,'dog')
        now[0]+=1;store.add(token,Note(pet='dog',context='',pet_id=pet['id']))
        now[0]=pet['expires'];_,fresh=store.issue(owner)
        self.assertEqual(store.pet_list(fresh),[]);self.assertEqual(store.list(owner),[])

    def test_revoked_session_and_future_schema_cannot_write(self):
        self.store.delete_account(self.a)
        with self.assertRaises(PermissionError):self.store.pet_create(self.ta,'dog')
        with sqlite3.connect(self.path) as db:db.execute('PRAGMA user_version=99')
        self.assertEqual(self.call('GET','/v1/me/pets',self.tb).status_code,503)
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],99)


if __name__=='__main__':unittest.main()
