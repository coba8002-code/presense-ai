import asyncio
from datetime import datetime, timezone
import json
import os
import sqlite3
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import httpx
from pydantic import ValidationError
from backend.accounts import Store, Note, RETENTION, SCHEMA_VERSION
from backend.journal_store import JournalStore, JournalLimit, JournalConflict
from backend.journal import CaseInput, FollowupInput
from backend.app import app


def instant(value):return datetime.fromtimestamp(value,timezone.utc)


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'private.sqlite3';self.now=[10000000.0]
        self.store=JournalStore(self.path,clock=lambda:self.now[0]);self.owner,self.token=self.store.issue(ttl=604800)
        _,self.other=self.store.issue(ttl=604800);self.pet=self.store.pet_create(self.token,'same-name')['id']

    def data(self,**changes):return CaseInput(pet_id=self.pet,observed_at=instant(self.now[0]),behavior='barking',before='visitor',during='short sounds',after='walked away',**changes)
    def create(self,key='journal-key-0001',**changes):return self.store.create_case(self.token,self.data(**changes),key)
    def follow(self,**changes):return FollowupInput(observed_at=instant(self.now[0]),action='observe',what_done='watched from a distance',outcome='unknown',note='guardian report',**changes)

    def test_idempotency_snapshot_and_unverified_output(self):
        first=self.create();second=self.create()
        self.assertEqual(first['id'],second['id']);self.assertTrue(second['reused'])
        self.assertEqual(first['kind'],'guardian_report');self.assertFalse(first['model_analysis']);self.assertFalse(first['training_approved'])
        with self.assertRaises(JournalConflict):self.store.create_case(self.token,self.data(retention_days=90),'journal-key-0001')
        self.store.pet_update(self.token,self.pet,'renamed')
        self.assertEqual(self.store.get_case(self.token,first['id'])['pet_name'],'same-name')
        self.assertNotIn(self.token,json.dumps(first));self.assertNotIn('owner',first)

    def test_owner_scope_same_name_and_unknown_ids_are_private(self):
        item=self.create();other_pet=self.store.pet_create(self.other,'same-name')['id']
        for fn,args in [(self.store.get_case,(self.other,item['id'])),(self.store.delete_case,(self.other,item['id'])),(self.store.add_followup,(self.other,item['id'],self.follow(),'journal-follow-0001')),(self.store.create_case,(self.other,self.data(),'other-case-key-0001'))]:
            with self.assertRaises(KeyError):fn(*args)
        self.assertEqual(self.store.list_cases(self.other,other_pet,0)['total'],0)

    def test_retention_only_explicitly_extends_selected_profile_not_notes_or_other_dog(self):
        second=self.store.pet_create(self.token,'same-name')['id']
        note=self.store.add(self.token,Note(pet='same-name',pet_id=self.pet,context='older note'))
        item=self.create(retention_days=90);deadline=item['expires']
        self.assertEqual(deadline,self.now[0]+90*86400)
        self.store.pet_update(self.token,self.pet,'renamed')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT expires FROM pets WHERE id=?',(self.pet,)).fetchone()[0],deadline)
            self.assertEqual(db.execute('SELECT expires FROM pets WHERE id=?',(second,)).fetchone()[0],self.now[0]+RETENTION)
            self.assertEqual(db.execute('SELECT expires FROM notes WHERE id=?',(note['id'],)).fetchone()[0],self.now[0]+RETENTION)

    def test_followup_replay_bound_to_case_and_never_extends_case_expiry(self):
        case=self.create();self.now[0]+=100
        first=self.store.add_followup(self.token,case['id'],self.follow(),'followup-key-0001')
        same=self.store.add_followup(self.token,case['id'],self.follow(),'followup-key-0001')
        self.assertEqual(first['id'],same['id']);self.assertTrue(same['reused'])
        detail=self.store.get_case(self.token,case['id']);self.assertEqual(detail['expires'],case['expires']);self.assertEqual(len(detail['followups']),1)
        with self.assertRaises(JournalConflict):self.store.add_followup(self.token,case['id'],self.follow().model_copy(update={'note':'changed'}),'followup-key-0001')
        with self.assertRaises(ValueError):self.store.add_followup(self.token,case['id'],self.follow().model_copy(update={'observed_at':instant(self.now[0]-200)}),'followup-key-0002')

    def test_case_delete_pet_delete_and_account_delete_cascade(self):
        for mode in ['case','pet','account']:
            case=self.create(key='key-for-delete-'+mode);self.store.add_followup(self.token,case['id'],self.follow(),'followup-for-'+mode)
            if mode=='case':self.store.delete_case(self.token,case['id'])
            elif mode=='pet':
                self.store.pet_delete(self.token,self.pet);self.pet=self.store.pet_create(self.token,'another')['id']
            else:self.store.delete_account(self.owner)
            with self.store.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM journal_cases').fetchone()[0],0)
                self.assertEqual(db.execute('SELECT count(*) FROM journal_followups').fetchone()[0],0)

    def test_expiry_and_revocation_reject_writes_and_remove_derived_rows(self):
        item=self.create();self.store.add_followup(self.token,item['id'],self.follow(),'followup-key-0001')
        with self.store.connect() as db:db.execute('DELETE FROM sessions WHERE owner=?',(self.owner,))
        with self.assertRaises(PermissionError):self.store.add_followup(self.token,item['id'],self.follow(),'followup-key-0002')
        self.now[0]=item['expires']+1;self.store.purge()
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM journal_followups').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM journal_cases').fetchone()[0],0)

    def test_time_validation_limits_and_pagination(self):
        for time in [self.now[0]+301,self.now[0]-90*86400-1]:
            with self.assertRaises(ValueError):self.store.create_case(self.token,self.data().model_copy(update={'observed_at':instant(time)}),'invalid-time-key')
        with self.assertRaises(ValidationError):CaseInput.model_validate_json(json.dumps({'pet_id':self.pet,'observed_at':'2026-01-01T12:00:00','behavior':'barking'}))
        item=self.create()
        for i in range(20):self.store.add_followup(self.token,item['id'],self.follow(),'followup-loop-key-'+str(i))
        with self.assertRaises(JournalLimit):self.store.add_followup(self.token,item['id'],self.follow(),'followup-key-overflow')
        for i in range(50):self.create(key='page-case-loop-key-'+str(i))
        first=self.store.list_cases(self.token,self.pet,0);second=self.store.list_cases(self.token,self.pet,50)
        self.assertEqual((first['total'],len(first['items']),len(second['items'])),(51,50,1))
        self.assertFalse({x['id'] for x in first['items']} & {x['id'] for x in second['items']})

    def test_v4_upgrade_preserves_existing_notes_and_cannot_downgrade_future_schema(self):
        note=self.store.add(self.token,Note(pet='same-name',context='original'))
        with self.store.connect() as db:
            db.execute('DROP TABLE journal_followups');db.execute('DROP TABLE journal_cases');db.execute('PRAGMA user_version=4')
        restored=JournalStore(self.path,clock=lambda:self.now[0]);self.assertEqual(restored.authenticate(self.token),self.owner)
        self.assertEqual(restored.list(self.owner)[0]['id'],note['id']);self.assertEqual(restored.list_cases(self.token,None,0)['total'],0)
        with restored.connect() as db:db.execute('PRAGMA user_version='+str(SCHEMA_VERSION+1))
        with self.assertRaises(sqlite3.DatabaseError):JournalStore(self.path)

    def test_concurrent_replays_store_one_case_and_capacity_never_charges_replay(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows=list(pool.map(lambda _:self.create(),range(2)))
        self.assertEqual(rows[0]['id'],rows[1]['id'])
        for i in range(499):self.create(key='capacity-case-key-'+str(i))
        self.assertTrue(self.create()['reused'])
        with self.assertRaises(JournalLimit):self.create(key='capacity-case-overflow')

    def test_thirty_day_case_expires_while_consented_ninety_day_case_and_other_owner_survive(self):
        first=self.create();second=self.create(key='ninety-day-case-key',retention_days=90)
        other_pet=self.store.pet_create(self.other,'other')['id']
        other_data=self.data(retention_days=90).model_copy(update={'pet_id':other_pet})
        other=self.store.create_case(self.other,other_data,'other-owner-case-key')
        self.now[0]+=31*86400;self.store.purge()
        _,token=self.store.issue(self.owner)
        self.assertEqual(self.store.get_case(token,second['id'])['id'],second['id'])
        with self.assertRaises(KeyError):self.store.get_case(token,first['id'])
        self.store.delete_account(self.owner)
        with self.store.connect() as db:self.assertIsNotNone(db.execute('SELECT id FROM journal_cases WHERE id=?',(other['id'],)).fetchone())


class JournalApiTests(unittest.TestCase):
    def test_cookie_csrf_and_member_deletion_cover_journal_and_followups(self):
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':td+'/test.sqlite3','PETSENSE_ENABLE_WEB_AUTH':'true','PETSENSE_PUBLIC_ORIGIN':'https://test','PETSENSE_OPERATOR_NAME':'Test','PETSENSE_PRIVACY_CONTACT':'test@example.invalid','PETSENSE_TERMS_VERSION':'test','PETSENSE_PRIVACY_VERSION':'test'}):
            async def scenario():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                    headers={'Origin':'https://test','X-PetSense-Request':'web'}
                    response=await client.post('/v1/auth/signup',headers=headers,json={'email':'guardian@example.invalid','password':'synthetic-private-password','accept_terms':True,'accept_privacy':True,'terms_version':'test','privacy_version':'test'})
                    self.assertEqual(response.status_code,201)
                    csrf=(await client.get('/v1/auth/session')).json()['csrf_token']
                    headers.update({'X-PetSense-CSRF':csrf,'X-Storage-Consent':'true','X-Journal-Consent':'journal-storage-v1','Idempotency-Key':'cookie-journal-key'})
                    pet=(await client.post('/v1/me/pets',headers=headers,json={'name':'dog'})).json()
                    data={'pet_id':pet['id'],'observed_at':datetime.now(timezone.utc).isoformat(),'behavior':'pacing'}
                    self.assertEqual((await client.post('/v1/me/journal',headers={k:v for k,v in headers.items() if k!='X-PetSense-CSRF'},json=data)).status_code,403)
                    case=await client.post('/v1/me/journal',headers=headers,json=data);self.assertEqual(case.status_code,201,case.text)
                    follow=await client.post('/v1/me/journal/'+case.json()['id']+'/followups',headers=headers,json={'observed_at':datetime.now(timezone.utc).isoformat(),'action':'observe','what_done':'observed quietly'})
                    self.assertEqual(follow.status_code,201,follow.text)
                    self.assertEqual((await client.post('/v1/auth/delete',headers=headers,json={'password':'synthetic-private-password'})).status_code,204)
                    with Store(td+'/test.sqlite3').connect() as db:
                        self.assertEqual(db.execute('SELECT count(*) FROM journal_cases').fetchone()[0],0)
                        self.assertEqual(db.execute('SELECT count(*) FROM journal_followups').fetchone()[0],0)
            asyncio.run(scenario())

    def test_http_requires_explicit_consent_bound_json_and_owner(self):
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':td+'/test.sqlite3','PETSENSE_ENABLE_WEB_AUTH':'false'}):
            store=Store(td+'/test.sqlite3');_,token=store.issue();pet=store.pet_create(token,'dog')
            headers={'X-PetSense-Session':token,'X-Journal-Consent':'journal-storage-v1','Idempotency-Key':'http-journal-key-0001'}
            data={'pet_id':pet['id'],'observed_at':datetime.now(timezone.utc).isoformat(),'behavior':'barking','retention_days':30}
            async def scenario():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                    self.assertEqual((await client.post('/v1/me/journal',json=data)).status_code,401)
                    self.assertEqual((await client.post('/v1/me/journal',headers={'X-PetSense-Session':token},json=data)).status_code,403)
                    self.assertEqual((await client.post('/v1/me/journal',headers=headers,json={**data,'owner':'injected'})).status_code,422)
                    self.assertEqual((await client.post('/v1/me/journal',headers=headers,content=b'x'*4097)).status_code,413)
                    response=await client.post('/v1/me/journal',headers=headers,json=data)
                    self.assertEqual(response.status_code,201,response.text);self.assertEqual(response.headers['cache-control'],'no-store')
                    item=response.json();self.assertFalse(item['training_approved'])
                    summary_url='/v1/me/journal/summary?pet_id='+pet['id']
                    summary=await client.get(summary_url,headers=headers)
                    self.assertEqual(summary.status_code,200)
                    self.assertEqual(summary.json()['case_count'],1)
                    self.assertEqual(summary.headers['cache-control'],'no-store')
                    self.assertEqual((await client.get(summary_url)).status_code,401)
                    self.assertEqual((await client.get(summary_url+'&days=8',headers=headers)).status_code,422)
                    detail=await client.get('/v1/me/journal/'+item['id'],headers=headers)
                    self.assertEqual(detail.status_code,200)
                    self.assertEqual((await client.delete('/v1/me/journal/'+item['id'],headers=headers)).status_code,400)
                    self.assertEqual((await client.delete('/v1/me/journal/'+item['id'],headers={**headers,'X-Delete-Confirm':'delete-case'})).status_code,204)
            asyncio.run(scenario())
