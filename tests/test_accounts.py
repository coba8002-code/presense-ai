import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend.accounts import Store,Note
from test_foundation import request

class AccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'notes.sqlite3'
        self.env=patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':str(self.path)});self.env.start();self.addCleanup(self.env.stop)
        self.store=Store(self.path);self.a,self.ta=self.store.issue();self.b,self.tb=self.store.issue()
    def call(self,method,path,token=None,**kwargs):
        h={'X-PetSense-Session':token or self.ta,**kwargs.pop('headers',{})}
        return asyncio.run(request(method,path,headers=h,**kwargs))
    def add(self,token=None):return self.call('POST','/v1/me/notes',token,headers={'X-Storage-Consent':'true'},json={'pet':'보리','context':'현관'})
    def test_sessions_store_hash_not_token_and_require_valid_session(self):
        self.assertNotIn(self.ta.encode(),self.path.read_bytes())
        self.assertEqual(self.call('GET','/v1/me/notes','invalid').status_code,401)
        self.assertEqual(self.call('GET','/v1/me/notes').headers['cache-control'],'no-store')
    def test_disabled_without_store(self):
        with patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':''}):self.assertEqual(self.call('GET','/v1/me/notes').status_code,503)
    def test_owner_isolation_and_delete(self):
        r=self.add();self.assertEqual(r.status_code,201);item=r.json()
        self.assertFalse(item['training_approved']);self.assertEqual(item['origin'],'guardian_note')
        self.assertEqual(len(self.call('GET','/v1/me/notes').json()['items']),1)
        self.assertEqual(self.call('GET','/v1/me/notes',self.tb).json()['items'],[])
        self.assertEqual(self.call('DELETE','/v1/me/notes/'+item['id'],self.tb).status_code,404)
        self.assertEqual(self.call('DELETE','/v1/me/notes/'+item['id']).status_code,204)
        self.assertEqual(self.call('GET','/v1/me/notes').json()['items'],[])
    def test_consent_and_injected_owner_or_model_result_rejected(self):
        self.assertEqual(self.call('POST','/v1/me/notes',json={'pet':'a','context':''}).status_code,403)
        for data in [{'pet':'a','context':'','owner':self.b},{'pet':'a','context':'','result':{'production_ready':True}},{'pet':' ','context':''}]:
            self.assertEqual(self.call('POST','/v1/me/notes',headers={'X-Storage-Consent':'true'},json=data).status_code,422)
        self.assertEqual(self.call('POST','/v1/me/notes',headers={'X-Storage-Consent':'true'},content=b'a'*4097).status_code,413)
    def test_account_deletion_revokes_all_sessions_not_other_user(self):
        _,other=self.store.issue(self.a);self.add()
        self.assertEqual(self.call('DELETE','/v1/me/account').status_code,400)
        self.assertEqual(self.call('DELETE','/v1/me/account',headers={'X-Delete-Confirm':'delete-account'}).status_code,204)
        self.assertEqual(self.call('GET','/v1/me/notes').status_code,401)
        self.assertIsNone(self.store.authenticate(other));self.assertEqual(self.store.authenticate(self.tb),self.b)
    def test_expiry_and_retention(self):
        now=[1000000];s=Store(self.path,clock=lambda:now[0]);owner,token=s.issue(ttl=60)
        item=s.add(token,Note(pet='dog',context='test'))
        now[0]+=61;self.assertIsNone(s.authenticate(token))
        with self.assertRaises(PermissionError):s.add(token,Note(pet='dog',context=''))
        now[0]=item['expires'];self.assertEqual(s.list(owner),[])
    def test_pagination_and_no_foreign_id_access(self):
        self.assertEqual(self.call('GET','/v1/me/notes?offset=-1').status_code,422)
        self.assertEqual(self.call('DELETE','/v1/me/notes/not-found').status_code,404)
