import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from backend.care_store import CareStore
from backend.journal_store import JournalStore
from backend.journal import CaseInput,FollowupInput
from backend.accounts import SCHEMA_VERSION

class CareTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'db';self.now=10000000
        self.store=CareStore(self.path,clock=lambda:self.now)
        self.owner,self.token=self.store.issue(ttl=604800)
        self.reader,self.reader_token=self.store.issue(ttl=604800)
        self.stranger,self.stranger_token=self.store.issue(ttl=604800)
        self.pet=self.store.pet_create(self.token,'same')['id']
        self.journal=JournalStore(self.path,clock=lambda:self.now)
        self.case=self.journal.create_case(self.token,CaseInput(pet_id=self.pet,observed_at=datetime.fromtimestamp(self.now,timezone.utc),behavior='barking'),'care-journal-key-0001')

    def grant(self):
        invite=self.store.invite(self.token,self.pet,7)
        self.store.accept(self.reader_token,invite['code'])
        return invite

    def test_code_hash_scope_and_read_only_view(self):
        invite=self.grant()
        with self.store.connect() as db:
            row=db.execute('SELECT code_hash,recipient FROM care_shares').fetchone()
            self.assertEqual(row,(hashlib.sha256(invite['code'].encode()).hexdigest(),self.reader))
        items=self.store.shared_cases(self.reader_token,invite['id'])
        self.assertEqual(items['items'][0]['id'],self.case['id'])
        detail=self.store.shared_case(self.reader_token,invite['id'],self.case['id'])
        self.assertFalse(detail['model_analysis']);self.assertNotIn('owner',json.dumps(detail))
        self.assertEqual(self.store.list_shares(self.reader_token)['received'][0]['role'],'viewer')
        with self.assertRaises(KeyError):self.journal.delete_case(self.reader_token,self.case['id'])
        with self.assertRaises(KeyError):self.store.shared_cases(self.stranger_token,invite['id'])
        with self.assertRaises(KeyError):self.store.shared_cases(self.token,invite['id'])

    def test_accept_replay_and_concurrent_claim_are_single_recipient(self):
        invite=self.store.invite(self.token,self.pet,7)
        def claim(token):
            try:return self.store.accept(token,invite['code'])
            except KeyError:return None
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(claim,[self.reader_token,self.stranger_token]))
        self.assertEqual(sum(r is not None for r in results),1)
        winner=self.reader_token if results[0] else self.stranger_token
        self.assertEqual(self.store.accept(winner,invite['code'])['id'],invite['id'])
        with self.assertRaises(KeyError):self.store.accept(self.token,invite['code'])
        with self.assertRaises(KeyError):self.store.accept(self.reader_token,'x'*43)

    def test_expiry_revoke_leave_and_no_profile_extension(self):
        before=self.store.pet_list(self.token)[0]['expires'];invite=self.grant()
        self.assertEqual(self.store.pet_list(self.token)[0]['expires'],before)
        with self.assertRaises(KeyError):self.store.revoke(self.stranger_token,invite['id'])
        self.store.revoke(self.reader_token,invite['id'])
        with self.assertRaises(KeyError):self.store.shared_cases(self.reader_token,invite['id'])
        invite=self.grant();self.store.revoke(self.token,invite['id'])
        with self.assertRaises(KeyError):self.store.accept(self.reader_token,invite['code'])
        invite=self.store.invite(self.token,self.pet,1)
        self.now+=86400
        with self.assertRaises(KeyError):self.store.accept(self.reader_token,invite['code'])

    def test_other_dog_case_and_new_followups_deletion(self):
        invite=self.grant();other=self.store.pet_create(self.token,'same')['id']
        other_case=self.journal.create_case(self.token,CaseInput(pet_id=other,observed_at=datetime.fromtimestamp(self.now,timezone.utc),behavior='pacing'),'care-other-case-001')
        with self.assertRaises(KeyError):self.store.shared_case(self.reader_token,invite['id'],other_case['id'])
        self.journal.add_followup(self.token,self.case['id'],FollowupInput(observed_at=datetime.fromtimestamp(self.now,timezone.utc),action='observe',what_done='<b>note</b>'),'care-followup-key-01')
        self.assertEqual(len(self.store.shared_case(self.reader_token,invite['id'],self.case['id'])['followups']),1)
        self.journal.delete_case(self.token,self.case['id'])
        self.assertEqual(self.store.shared_cases(self.reader_token,invite['id'])['total'],0)

    def test_cascades_and_session_revocation(self):
        invite=self.grant()
        with self.store.connect() as db:db.execute('DELETE FROM sessions WHERE owner=?',(self.reader,))
        with self.assertRaises(PermissionError):self.store.shared_cases(self.reader_token,invite['id'])
        self.store.delete_account(self.reader)
        self.assertEqual(self.store.list_shares(self.token)['sent'],[])
        _,self.reader_token=self.store.issue(self.reader)
        self.grant();self.store.pet_delete(self.token,self.pet)
        self.assertEqual(self.store.list_shares(self.reader_token)['received'],[])

    def test_accepted_expiry_owner_deletion_and_idle_maintenance(self):
        from scripts.privacy_maintenance import cleanup_once
        invite=self.store.invite(self.token,self.pet,1)
        self.store.accept(self.reader_token,invite['code'])
        self.now+=86400
        self.assertEqual(cleanup_once(self.path,clock=lambda:self.now)['removed']['care_shares'],1)
        with self.assertRaises(KeyError):self.store.shared_cases(self.reader_token,invite['id'])
        invite=self.grant();self.store.delete_account(self.owner)
        self.assertEqual(self.store.list_shares(self.reader_token)['received'],[])

    def test_limits_bad_days_and_preserving_v5_migration(self):
        for days in [0,2,True,'7']:
            with self.assertRaises(ValueError):self.store.invite(self.token,self.pet,days)
        for _ in range(20):self.store.invite(self.token,self.pet,7)
        with self.assertRaises(ValueError):self.store.invite(self.token,self.pet,7)
        with self.store.connect() as db:
            db.execute('DROP TABLE care_shares');db.execute('PRAGMA user_version=5')
        upgraded=CareStore(self.path,clock=lambda:self.now)
        self.assertEqual(upgraded.pet_list(self.token)[0]['id'],self.pet)
        self.assertEqual(self.journal.get_case(self.token,self.case['id'])['id'],self.case['id'])
        with upgraded.connect() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)

class CareApiTests(unittest.TestCase):
    def test_https_csrf_consent_scope_and_no_store(self):
        import asyncio,os,httpx
        from unittest.mock import patch
        from backend.app import app
        from backend.web_security import COOKIE,csrf_value
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':td+'/db','PETSENSE_ENABLE_WEB_AUTH':'true','PETSENSE_PUBLIC_ORIGIN':'https://test','PETSENSE_OPERATOR_NAME':'test','PETSENSE_PRIVACY_CONTACT':'test@example.invalid','PETSENSE_TERMS_VERSION':'test','PETSENSE_PRIVACY_VERSION':'test'}):
            store=CareStore(td+'/db');_,owner=store.issue();_,reader=store.issue();pet=store.pet_create(owner,'test')
            async def run():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                    client.cookies.set(COOKIE,owner)
                    headers={'Origin':'https://test','X-PetSense-CSRF':csrf_value(owner),'X-Journal-Consent':'care-sharing-v1'}
                    body={'pet_id':pet['id'],'days':1}
                    self.assertEqual((await client.post('/v1/me/care-shares',json=body)).status_code,403)
                    self.assertEqual((await client.post('/v1/me/care-shares',headers={**headers,'X-Journal-Consent':'false'},json=body)).status_code,403)
                    self.assertEqual((await client.post('/v1/me/care-shares',headers=headers,json={**body,'role':'editor'})).status_code,422)
                    result=await client.post('/v1/me/care-shares',headers=headers,json=body)
                    self.assertEqual(result.status_code,201);self.assertEqual(result.headers['cache-control'],'no-store');invite=result.json()
                    client.cookies.set(COOKIE,reader);headers['X-PetSense-CSRF']=csrf_value(reader)
                    self.assertEqual((await client.post('/v1/me/care-shares/accept',headers=headers,json={'code':invite['code']})).status_code,200)
                    route='/v1/me/care-shares/'+invite['id']
                    self.assertEqual((await client.get(route+'/journal')).status_code,200)
                    self.assertEqual((await client.delete(route,headers=headers)).status_code,400)
                    self.assertEqual((await client.delete(route,headers={**headers,'X-Delete-Confirm':'leave-or-revoke'})).status_code,204)
                    self.assertEqual((await client.get(route+'/journal')).status_code,404)
            asyncio.run(run())
