import json,sqlite3,tempfile,unittest
from pathlib import Path
from backend.pet_details import DogDetails,CaptureContext
from backend.accounts import Store
from backend.job_store import JobStore,Conflict
from test_audio_jobs import wav
class DogContextTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.now=1000.;self.path=Path(self.tmp.name)/'db';self.store=JobStore(self.path,clock=lambda:self.now);_,self.token=self.store.issue(ttl=604800);_,self.other=self.store.issue(ttl=604800)
 def test_unknown_mixed_and_reported_breed_without_verified_claim(self):
  self.assertIsNone(DogDetails().age_months)
  for data in ({'breed_kind':'reported'},{'breed_kind':'unknown','breed_name':'Poodle'},{'breed_verified':True},{'weight_kg':float('nan')},{'age_months':True}):
   with self.subTest(data=data),self.assertRaises(ValueError):DogDetails.model_validate(data)
  detail=DogDetails(breed_kind='reported',breed_name='푸들',weight_kg=5.,age_months=24)
  pet=self.store.pet_create(self.token,'dog',detail.model_dump());self.assertEqual(pet['details']['source'],'guardian_report');self.assertFalse(pet['details']['verified'])
  renamed=self.store.pet_update(self.token,pet['id'],'renamed');self.assertEqual(renamed['details']['breed_name'],'푸들')
 def test_job_snapshot_owner_scope_idempotency_and_worker_separation(self):
  pet=self.store.pet_create(self.token,'dog',DogDetails(breed_kind='mixed').model_dump());context=CaptureContext(setting='play',dogs='multiple').model_dump()
  job=self.store.enqueue(self.token,pet['id'],'context-key-00001',wav(),context)
  self.store.pet_update(self.token,pet['id'],'dog',DogDetails(breed_kind='reported',breed_name='poodle').model_dump())
  self.assertEqual(self.store.get(self.token,job['id'])['guardian_context']['profile']['details']['breed_kind'],'mixed')
  self.assertEqual(self.store.enqueue(self.token,pet['id'],'context-key-00001',wav(),context)['id'],job['id'])
  with self.assertRaises(Conflict):self.store.enqueue(self.token,pet['id'],'context-key-00001',wav(),CaptureContext(setting='alone').model_dump())
  with self.assertRaises(KeyError):self.store.get(self.other,job['id'])
  self.assertNotIn('guardian_context',self.store.claim())
  self.store.cancel(self.token,job['id']);self.assertIsNone(self.store.get(self.token,job['id'])['guardian_context'])
 def test_profile_delete_expiry_and_account_deletion_cascade(self):
  for mode in ('pet','expiry','account'):
   pet=self.store.pet_create(self.token,'dog',DogDetails().model_dump());job=self.store.enqueue(self.token,pet['id'],'context-cleanup-'+mode,wav(),CaptureContext().model_dump())
   if mode=='pet':self.store.pet_delete(self.token,pet['id'])
   elif mode=='expiry':
    with self.store.connect() as db:db.execute('UPDATE audio_jobs SET expires=1 WHERE id=?',(job['id'],))
    self.store.purge()
   else:self.store.delete_account(self.store.authenticate(self.token))
   with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM job_contexts').fetchone()[0],0)
 def test_v8_migration_preserves_name_and_leaves_details_unknown(self):
  pet=self.store.pet_create(self.token,'legacy')
  with sqlite3.connect(self.path) as db:db.execute('DROP TABLE pet_details');db.execute('DROP TABLE job_contexts');db.execute('PRAGMA user_version=8')
  again=Store(self.path,clock=lambda:self.now);self.assertIsNone(again.pet_list(self.token)[0]['details']);self.assertEqual(again.pet_list(self.token)[0]['id'],pet['id'])

import test_audio_jobs as job_helpers
import test_pet_profiles as profile_helpers
class ContextApiTests(unittest.TestCase):
 setUp=job_helpers.AudioJobApiTests.setUp
 headers=job_helpers.AudioJobApiTests.headers
 call=job_helpers.AudioJobApiTests.call
 def test_context_requires_separate_consent_and_rejects_verified_injection(self):
  h={**self.headers(),'X-PetSense-Context':json.dumps({'setting':'play'})}
  self.assertEqual(self.call(headers=h).status_code,403)
  h['X-Context-Storage-Consent']='guardian-context-v1';r=self.call(headers=h);self.assertEqual(r.status_code,202)
  self.assertFalse(r.json()['guardian_context']['verified']);self.assertFalse(r.json()['guardian_context']['model_conditioning'])
  for extra in ({'verified':True},{'speaker':'automatically_verified'},{'device_id':'私の住所'},{'setting':'aggressive'}):
   bad={**h,'X-PetSense-Context':json.dumps(extra)};self.assertEqual(self.call(headers=bad).status_code,422)
  self.assertEqual(self.call(headers={**h,'X-PetSense-Context':'x'*2049}).status_code,413)
class DetailsApiTests(unittest.TestCase):
 setUp=profile_helpers.PetProfileTests.setUp
 call=profile_helpers.PetProfileTests.call
 def test_details_owner_consent_strict_fields_and_clear_to_unknown(self):
  body={'name':'dog','details':{'breed_kind':'mixed','age_months':18,'weight_kg':7.5}}
  self.assertEqual(self.call('POST','/v1/me/pets',json=body).status_code,403)
  h={'X-Storage-Consent':'true'};r=self.call('POST','/v1/me/pets',headers=h,json=body);self.assertEqual(r.status_code,201)
  pet=r.json();self.assertFalse(pet['details']['verified'])
  self.assertEqual(self.call('GET','/v1/me/pets',self.tb).json()['items'],[])
  for extra in ({'age_months':-1},{'weight_kg':True},{'breed_verified':True},{'breed_kind':'reported','breed_name':' '}):
   self.assertEqual(self.call('PATCH','/v1/me/pets/'+pet['id'],headers=h,json={'name':'dog','details':extra}).status_code,422)
  cleared=self.call('PATCH','/v1/me/pets/'+pet['id'],headers=h,json={'name':'dog','details':None});self.assertEqual(cleared.json()['details']['breed_kind'],'unknown')

class InterpretationLimitTests(unittest.TestCase):
 def test_body_reference_prompts_are_not_breed_stereotypes(self):
  from backend.pet_details import interpretation_limits
  a=DogDetails(breed_kind='reported',breed_name='Poodle',tail='curled',ears='floppy',coat='long').model_dump()
  b={**a,'breed_name':'Unknown mix label'};c=CaptureContext().model_dump()
  self.assertEqual(interpretation_limits(a,c),interpretation_limits(b,c));self.assertIn('ear_base_visibility_check_needed',interpretation_limits(a,c))
  self.assertIn('tail_cue_not_applicable_reported',interpretation_limits({'tail':'absent'},CaptureContext(visibility='clear',speaker='guardian_confirmed').model_dump()))
