import hashlib,json,unittest
import test_measurements as fixtures
from evaluation.feedback_review import review_card,feedback_digest
class FeedbackReviewTests(unittest.TestCase):
 setUp=fixtures.MeasurementTests.setUp
 sample=fixtures.MeasurementTests.sample
 def card(self):
  obs,_=self.sample();self.store.feedback(self.token,obs['id'],'noise')
  with self.store.connect() as db:
   db.row_factory=__import__('sqlite3').Row
   f=dict(db.execute('SELECT * FROM observation_feedback').fetchone());m=dict(db.execute('SELECT * FROM model_observations').fetchone())
  return {'observation_id':obs['id'],'observation_payload_sha256':m['payload_hash'],'feedback_sha256':feedback_digest(f),'reviews':[{'reviewer':r,'qualification_evidence':'synthetic attestation, not credential verification','verdict':'needs_more_evidence','model_identity_hidden':True} for r in ['a','b']]}
 def test_dry_run_then_bound_review_no_training(self):
  c=self.card();r=review_card(self.path,c,now=self.now);self.assertEqual(r['status'],'needs_more_evidence');self.assertFalse(r['written']);self.assertFalse(r['training_approved'])
  r=review_card(self.path,c,now=self.now,write=True);self.assertTrue(r['written'])
  row=self.store.listing(self.token,self.pet,'phone-a','indoors_quiet','synthetic_fixture')['items'][0];self.assertEqual(row['feedback']['status'],'needs_more_evidence')
 def test_stale_payload_duplicate_reviewers_and_expiry_rejected(self):
  c=self.card();bad={**c,'feedback_sha256':'0'*64}
  with self.assertRaises(ValueError):review_card(self.path,bad,now=self.now,write=True)
  c['reviews'][1]['reviewer']='a'
  with self.assertRaises(ValueError):review_card(self.path,c,now=self.now)
  c['reviews'][1]['reviewer']='b'
  with self.assertRaises(ValueError):review_card(self.path,c,now=self.now+31*86400)
 def test_disagreement_and_withdrawal(self):
  c=self.card();c['reviews'][1]['verdict']='supports';self.assertEqual(review_card(self.path,c,now=self.now)['status'],'disputed')
  self.store.delete_feedback(self.token,c['observation_id'])
  with self.assertRaises(ValueError):review_card(self.path,c,now=self.now,write=True)
