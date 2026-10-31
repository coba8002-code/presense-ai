from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from backend.journal import CaseInput, FollowupInput
from backend.journal_store import JournalStore

class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.now=10000000
        self.store=JournalStore(Path(self.temp.name)/'db',clock=lambda:self.now)
        self.owner,self.token=self.store.issue(ttl=604800)
        self.pet=self.store.pet_create(self.token,'same')['id']
        self.seq=0

    def case(self,age=0,pet=None):
        self.seq+=1
        return self.store.create_case(self.token,CaseInput(pet_id=pet or self.pet,observed_at=datetime.fromtimestamp(self.now-age,timezone.utc),behavior='barking'),f'case-summary-{self.seq:08d}')

    def test_window_all_pages_future_and_followups(self):
        for _ in range(51):self.case()
        edge=self.case(7*86400);self.case(7*86400+1);self.case(-1)
        self.store.add_followup(self.token,edge['id'],FollowupInput(observed_at=datetime.fromtimestamp(self.now,timezone.utc),action='observe',what_done='observed'),'summary-follow-0001')
        report=self.store.summary(self.token,self.pet,7)
        self.assertEqual(report['case_count'],52)
        self.assertEqual(report['cases_with_followup'],1)
        self.assertEqual(report['cases_without_followup'],51)
        self.assertEqual(report['followup_count'],1)
        self.assertEqual(report['behavior_counts'],{'barking':52})
        self.assertFalse(report['model_analysis']);self.assertFalse(report['training_approved'])
        self.assertEqual(self.store.summary(self.token,self.pet,30)['case_count'],53)

    def test_isolation_validation_revocation_and_delete(self):
        row=self.case();second=self.store.pet_create(self.token,'same')['id'];self.case(pet=second)
        _,other=self.store.issue()
        with self.assertRaises(KeyError):self.store.summary(other,self.pet,7)
        for invalid in [0,8,90,True,'7']:
            with self.assertRaises(ValueError):self.store.summary(self.token,self.pet,invalid)
        self.assertEqual(self.store.summary(self.token,self.pet,7)['case_count'],1)
        self.store.delete_case(self.token,row['id'])
        self.assertEqual(self.store.summary(self.token,self.pet,7)['case_count'],0)
        with self.store.connect() as db:db.execute('DELETE FROM sessions WHERE owner=?',(self.owner,))
        with self.assertRaises(PermissionError):self.store.summary(self.token,self.pet,7)

    def test_future_followup_excluded_and_no_retention_extension(self):
        row=self.case()
        self.store.add_followup(self.token,row['id'],FollowupInput(observed_at=datetime.fromtimestamp(self.now+100,timezone.utc),action='observe',what_done='clock ahead'),'summary-future-0001')
        self.assertEqual(self.store.summary(self.token,self.pet,7)['cases_without_followup'],1)
        self.assertEqual(self.store.get_case(self.token,row['id'])['expires'],row['expires'])
        # Expired case excluded even when its observed timestamp is in the window.
        with self.store.connect() as db:db.execute('UPDATE journal_cases SET expires=? WHERE id=?',(self.now,row['id']))
        self.assertEqual(self.store.summary(self.token,self.pet,7)['case_count'],0)
