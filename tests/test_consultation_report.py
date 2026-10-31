import unittest
import test_journal_summary as fixtures
from backend.consultation_report import build_report
from backend.journal import FollowupInput
from datetime import datetime,timezone

class ReportTests(unittest.TestCase):
    setUp=fixtures.SummaryTests.setUp
    case=fixtures.SummaryTests.case

    def test_boundaries_order_limit_and_missing_context(self):
        self.case(7*86400);self.case(7*86400+1);self.case(-1)
        report=build_report(self.store,self.token,self.pet,7)
        self.assertEqual(report['total'],1)
        self.assertEqual(report['missing']['before'],1)
        self.assertEqual(report['missing']['followup'],1)
        for i in range(101):self.case(i)
        report=build_report(self.store,self.token,self.pet,7)
        self.assertEqual(report['total'],102);self.assertEqual(report['included'],100);self.assertTrue(report['truncated'])
        observed=[row['data']['observed_at'] for row in report['cases']]
        self.assertEqual(observed,sorted(observed))
        self.assertFalse(report['model_analysis']);self.assertFalse(report['training_approved'])

    def test_scope_deleted_expired_and_revoked_session(self):
        row=self.case();other_pet=self.store.pet_create(self.token,'same')['id'];self.case(pet=other_pet)
        _,foreign=self.store.issue()
        with self.assertRaises(KeyError):build_report(self.store,foreign,self.pet,7)
        self.assertEqual(build_report(self.store,self.token,self.pet,7)['total'],1)
        self.store.delete_case(self.token,row['id'])
        self.assertEqual(build_report(self.store,self.token,self.pet,7)['total'],0)
        row=self.case()
        with self.store.connect() as db:db.execute('UPDATE journal_cases SET expires=? WHERE id=?',(self.now,row['id']))
        self.assertEqual(build_report(self.store,self.token,self.pet,7)['total'],0)
        with self.store.connect() as db:db.execute('DELETE FROM sessions WHERE owner=?',(self.owner,))
        with self.assertRaises(PermissionError):build_report(self.store,self.token,self.pet,7)

    def test_followup_future_filter_and_no_retention_extension(self):
        row=self.case()
        for i,delta in enumerate([0,100]):
            follow=FollowupInput(observed_at=datetime.fromtimestamp(self.now+delta,timezone.utc),action='observe',what_done='literal <script>')
            self.store.add_followup(self.token,row['id'],follow,f'report-followup-{i:08d}')
        report=build_report(self.store,self.token,self.pet,30)
        self.assertEqual(len(report['cases'][0]['followups']),1)
        self.assertEqual(report['missing']['followup'],0)
        self.assertEqual(self.store.get_case(self.token,row['id'])['expires'],row['expires'])
        for bad in [1,8,True,'7']:
            with self.assertRaises(ValueError):build_report(self.store,self.token,self.pet,bad)

class ReportApiTests(unittest.TestCase):
    def test_private_api_validates_period_and_denies_viewer(self):
        import asyncio,os,tempfile,httpx
        from unittest.mock import patch
        from backend.care_store import CareStore
        from backend.app import app
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':td+'/db','PETSENSE_ENABLE_WEB_AUTH':'false'}):
            store=CareStore(td+'/db');_,owner=store.issue();_,viewer=store.issue();pet=store.pet_create(owner,'private')
            invite=store.invite(owner,pet['id'],1);store.accept(viewer,invite['code'])
            async def run():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                    url='/v1/me/journal/report?pet_id='+pet['id']
                    response=await client.get(url,headers={'X-PetSense-Session':owner})
                    self.assertEqual(response.status_code,200);self.assertEqual(response.headers['cache-control'],'no-store')
                    self.assertEqual(response.json()['total'],0)
                    self.assertEqual((await client.get(url)).status_code,401)
                    self.assertEqual((await client.get(url,headers={'X-PetSense-Session':viewer})).status_code,404)
                    self.assertEqual((await client.get(url+'&days=8',headers={'X-PetSense-Session':owner})).status_code,422)
            asyncio.run(run())
