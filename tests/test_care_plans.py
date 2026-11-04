import unittest
import test_journal_summary as fixtures
from datetime import datetime,timezone
from backend.plan_store import PlanStore
from backend.plans import PlanInput,Transition
from backend.journal import FollowupInput
from backend.journal_store import JournalConflict,JournalLimit

class PlanTests(unittest.TestCase):
    def setUp(self):
        fixtures.SummaryTests.setUp(self)
        self.store=PlanStore(self.store.path,clock=lambda:self.now)
        self.row=fixtures.SummaryTests.case(self)
    def data(self,**kw):
        return PlanInput(case_id=self.row['id'],goal='Observe naturally',due_at=datetime.fromtimestamp(self.now+3600,timezone.utc),**kw)
    def create(self,key='plan-key-00000001',data=None):return self.store.create_plan(self.token,data or self.data(),key)
    def follow(self):
        self.now+=1
        return self.store.add_followup(self.token,self.row['id'],FollowupInput(observed_at=datetime.fromtimestamp(self.now,timezone.utc),action='observe',what_done='Watched quietly'),f'plan-follow-key-{self.now}')['id']
    def test_idempotency_due_and_limits(self):
        row=self.create();self.assertEqual(self.create()['id'],row['id'])
        with self.assertRaises(JournalConflict):self.create(data=self.data().model_copy(update={'goal':'changed'}))
        for delta in [-1,31*86400]:
            with self.assertRaises(ValueError):self.create('invalid-plan-key',self.data().model_copy(update={'due_at':datetime.fromtimestamp(self.now+delta,timezone.utc)}))
        for i in range(9):self.create(f'plan-extra-key-{i:04d}')
        with self.assertRaises(JournalLimit):self.create('plan-overflow-key')
        self.assertEqual(self.create()['id'],row['id'])
    def test_completion_requires_same_case_new_nonfuture_followup_and_is_idempotent(self):
        old=self.follow();plan=self.create();self.now+=1
        with self.assertRaises(ValueError):self.store.transition(self.token,plan['id'],Transition(status='completed',followup_id='not-real'))
        # Force older timestamp because fixture clock can otherwise be equal.
        with self.store.connect() as db:db.execute('UPDATE journal_followups SET created=? WHERE id=?',(plan['created']-1,old))
        with self.assertRaises(ValueError):self.store.transition(self.token,plan['id'],Transition(status='completed',followup_id=old))
        follow=self.follow();change=Transition(status='completed',followup_id=follow)
        done=self.store.transition(self.token,plan['id'],change)
        self.assertEqual(done['status'],'completed');self.assertEqual(done['expires'],plan['expires'])
        self.assertEqual(self.store.transition(self.token,plan['id'],change),done)
        with self.assertRaises(JournalConflict):self.store.transition(self.token,plan['id'],Transition(status='cancelled'))
    def test_foreign_owner_and_other_case_are_denied(self):
        plan=self.create();_,other=self.store.issue()
        for fn,args in [(self.store.list_plans,(other,self.row['id'])),(self.store.delete_plan,(other,plan['id'])),(self.store.transition,(other,plan['id'],Transition(status='cancelled')))]:
            with self.assertRaises(KeyError):fn(*args)
        second=fixtures.SummaryTests.case(self)
        follow=self.store.add_followup(self.token,second['id'],FollowupInput(observed_at=datetime.fromtimestamp(self.now,timezone.utc),action='observe',what_done='other case'),'other-plan-followup')['id']
        with self.assertRaises(ValueError):self.store.transition(self.token,plan['id'],Transition(status='completed',followup_id=follow))
        self.assertEqual(self.store.list_plans(self.token,self.row['id'])[0]['status'],'planned')
    def test_case_pet_account_delete_and_idle_expiry(self):
        from scripts.privacy_maintenance import cleanup_once
        plan=self.create();self.store.delete_case(self.token,self.row['id'])
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM care_plans').fetchone()[0],0)
        self.row=fixtures.SummaryTests.case(self);self.create();self.store.pet_delete(self.token,self.pet)
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM care_plans').fetchone()[0],0)
        self.pet=self.store.pet_create(self.token,'dog')['id'];self.row=fixtures.SummaryTests.case(self);self.create()
        with self.store.connect() as db:db.execute('UPDATE care_plans SET expires=?',(self.now,))
        self.assertEqual(cleanup_once(self.store.path,clock=lambda:self.now)['removed']['care_plans'],1)
        self.create('plan-owner-delete');self.store.delete_account(self.owner)
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM care_plans').fetchone()[0],0)
    def test_migration_revoked_session_and_future_followup(self):
        from backend.accounts import SCHEMA_VERSION
        from backend.plan_store import PlanStore
        with self.store.connect() as db:db.execute('DROP TABLE care_plans');db.execute('PRAGMA user_version=6')
        self.store=PlanStore(self.store.path,clock=lambda:self.now)
        plan=self.create();follow=self.follow()
        with self.store.connect() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
            db.execute('UPDATE journal_followups SET observed=? WHERE id=?',(self.now+100,follow))
        with self.assertRaises(ValueError):self.store.transition(self.token,plan['id'],Transition(status='completed',followup_id=follow))
        with self.store.connect() as db:db.execute('DELETE FROM sessions WHERE owner=?',(self.owner,))
        with self.assertRaises(PermissionError):self.store.list_plans(self.token,self.row['id'])

class PlanApiTests(unittest.TestCase):
    def test_https_consent_csrf_completion_and_delete(self):
        import asyncio,os,tempfile,httpx
        from unittest.mock import patch
        from backend.app import app
        from backend.web_security import COOKIE,csrf_value
        from backend.journal import CaseInput
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':td+'/db','PETSENSE_ENABLE_WEB_AUTH':'true','PETSENSE_PUBLIC_ORIGIN':'https://test','PETSENSE_OPERATOR_NAME':'test','PETSENSE_PRIVACY_CONTACT':'test@example.invalid','PETSENSE_TERMS_VERSION':'test','PETSENSE_PRIVACY_VERSION':'test'}):
            store=PlanStore(td+'/db');_,token=store.issue();pet=store.pet_create(token,'dog')
            row=store.create_case(token,CaseInput(pet_id=pet['id'],observed_at=datetime.now(timezone.utc),behavior='barking'),'plan-http-case-key')
            async def run():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                    client.cookies.set(COOKIE,token)
                    headers={'Origin':'https://test','X-PetSense-CSRF':csrf_value(token),'X-Journal-Consent':'care-plan-storage-v1','Idempotency-Key':'plan-api-key-0001'}
                    body={'case_id':row['id'],'goal':'Observe','due_at':datetime.fromtimestamp(store.clock()+3600,timezone.utc).isoformat()}
                    self.assertEqual((await client.post('/v1/me/care-plans',json=body)).status_code,403)
                    self.assertEqual((await client.post('/v1/me/care-plans',headers={**headers,'X-Journal-Consent':'false'},json=body)).status_code,403)
                    result=await client.post('/v1/me/care-plans',headers=headers,json=body)
                    self.assertEqual(result.status_code,201);self.assertEqual(result.headers['cache-control'],'no-store')
                    url='/v1/me/care-plans/'+result.json()['id']
                    self.assertEqual((await client.patch(url,headers=headers,json={'status':'completed'})).status_code,422)
                    self.assertEqual((await client.patch(url,headers=headers,json={'status':'cancelled','followup_id':''})).status_code,422)
                    self.assertEqual((await client.patch(url,headers=headers,json={'status':'cancelled'})).status_code,200)
                    self.assertEqual((await client.delete(url,headers=headers)).status_code,400)
                    self.assertEqual((await client.delete(url,headers={**headers,'X-Delete-Confirm':'delete-plan'})).status_code,204)
            asyncio.run(run())
