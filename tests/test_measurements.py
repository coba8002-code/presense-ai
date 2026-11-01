import json,tempfile,unittest,sqlite3
from pathlib import Path
from backend.job_store import JobStore
from backend.measurements import MeasurementStore,ObservationInput
from test_audio_jobs import wav,result
class MeasurementTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.now=1000000.;self.path=Path(self.tmp.name)/'db';self.store=MeasurementStore(self.path,clock=lambda:self.now);self.jobs=JobStore(self.path,clock=lambda:self.now);self.owner,self.token=self.store.issue(ttl=604800);_,self.other=self.store.issue();self.pet=self.store.pet_create(self.token,'dog')['id']
 def sample(self,key='measurement-job-00001',device='phone-a',condition='indoors_quiet'):
  raw=wav();job=self.jobs.enqueue(self.token,self.pet,key,raw);claim=self.jobs.claim();self.jobs.finish(claim,{**result(raw),'execution_kind':'synthetic_fixture','duration_seconds':1.})
  data=ObservationInput(job_id=job['id'],device_id=device,condition=condition,same_dog_confirmed=True)
  return self.store.save(self.token,data),data
 def test_immutable_source_scope_and_no_client_model_claim(self):
  obs,data=self.sample();self.assertEqual(self.store.save(self.token,data)['id'],obs['id'])
  with self.assertRaises(ValueError):self.store.save(self.token,data.model_copy(update={'device_id':'other'}))
  with self.assertRaises(KeyError):self.store.save(self.other,data)
  self.assertEqual(obs['source_kind'],'synthetic_fixture');self.assertFalse(obs['training_approved']);self.assertFalse(obs['species_verified'])
 def test_baseline_does_not_mix_context_device_and_source(self):
  for i in range(6):
   if i:self.now+=86400
   obs,_=self.sample(key=f'measurement-day-{i:08d}')
  report=self.store.listing(self.token,self.pet,'phone-a','indoors_quiet','synthetic_fixture')
  self.assertTrue(report['baseline']['ready']);self.assertEqual(report['baseline']['unit'],'uncalibrated_score')
  self.assertFalse(self.store.listing(self.token,self.pet,'phone-b','indoors_quiet','synthetic_fixture')['baseline']['ready'])
 def test_feedback_is_unreviewed_and_erasure_cascades(self):
  obs,_=self.sample();f=self.store.feedback(self.token,obs['id'],'noise');self.assertEqual(f['status'],'unreviewed');self.assertFalse(f['training_approved'])
  with self.assertRaises(KeyError):self.store.feedback(self.other,obs['id'],'noise')
  self.jobs.cancel(self.token,obs['source_job_id']);self.assertEqual(self.store.listing(self.token,self.pet,'phone-a','indoors_quiet','synthetic_fixture')['items'],[])
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM observation_feedback').fetchone()[0],0)
 def test_expiry_pet_account_and_v7_upgrade(self):
  obs,_=self.sample();self.store.feedback(self.token,obs['id'],'not_sure');self.now=obs['expires']+1
  from scripts.privacy_maintenance import cleanup_once
  cleaned=cleanup_once(self.path,clock=lambda:self.now)
  self.assertEqual(cleaned['removed']['model_observations'],1);self.assertEqual(cleaned['removed']['observation_feedback'],1)
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM model_observations').fetchone()[0],0)
 def test_unknown_job_provenance_refused(self):
  raw=wav();j=self.jobs.enqueue(self.token,self.pet,'unknown-source-000001',raw);claim=self.jobs.claim();self.jobs.finish(claim,{**result(raw),'duration_seconds':1.})
  with self.assertRaises(ValueError):self.store.save(self.token,ObservationInput(job_id=j['id'],device_id='phone',condition='unknown',same_dog_confirmed=True))

 def test_v7_migration_preserves_source_and_pet_delete(self):
  obs,data=self.sample()
  with self.store.connect() as db:
   db.execute('DROP TABLE observation_feedback');db.execute('DROP TABLE model_observations');db.execute('PRAGMA user_version=7')
  upgraded=MeasurementStore(self.path,clock=lambda:self.now)
  restored=upgraded.save(self.token,data)
  self.assertEqual(restored['source_job_id'],obs['source_job_id'])
  upgraded.feedback(self.token,restored['id'],'not_sure');upgraded.pet_delete(self.token,self.pet)
  with upgraded.connect() as db:
   self.assertEqual(db.execute('SELECT count(*) FROM model_observations').fetchone()[0],0)
   self.assertEqual(db.execute('SELECT count(*) FROM observation_feedback').fetchone()[0],0)
 def test_account_delete_and_job_expiry_separate_consent(self):
  obs,_=self.sample();self.store.feedback(self.token,obs['id'],'not_sure');self.now+=86401;self.store.purge()
  self.assertEqual(len(self.store.listing(self.token,self.pet,'phone-a','indoors_quiet','synthetic_fixture')['items']),1)
  self.store.delete_account(self.owner)
  with self.store.connect() as db:
   self.assertEqual(db.execute('SELECT count(*) FROM model_observations').fetchone()[0],0);self.assertEqual(db.execute('SELECT count(*) FROM observation_feedback').fetchone()[0],0)

class MeasurementDurationTests(unittest.TestCase):
 setUp=MeasurementTests.setUp
 def test_duration_is_bound_to_verified_input_not_model_claim(self):
  raw=wav();job=self.jobs.enqueue(self.token,self.pet,'duration-proof-key-01',raw);claim=self.jobs.claim();self.jobs.finish(claim,{**result(raw),'execution_kind':'synthetic_fixture','duration_seconds':9.})
  r=self.store.save(self.token,ObservationInput(job_id=job['id'],device_id='phone',condition='unknown',same_dog_confirmed=True))
  self.assertEqual(r['duration_seconds'],1.)

class MeasurementMetadataTests(unittest.TestCase):
 setUp=MeasurementTests.setUp
 def test_only_whitelisted_score_metadata_persisted(self):
  raw=wav();j=self.jobs.enqueue(self.token,self.pet,'whitelist-score-key-01',raw);claim=self.jobs.claim();r={**result(raw),'execution_kind':'synthetic_fixture','duration_seconds':1.};r['dog_event_scores'][0]['private_text']='must-not-persist';self.jobs.finish(claim,r)
  obs=self.store.save(self.token,ObservationInput(job_id=j['id'],device_id='phone',condition='unknown',same_dog_confirmed=True))
  self.assertNotIn('must-not-persist',json.dumps(obs))

class MeasurementApiTests(unittest.TestCase):
 def test_cookie_csrf_consent_no_forged_model_or_review_fields(self):
  import asyncio,os,httpx
  from unittest.mock import patch
  from backend.app import app
  with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':td+'/db','PETSENSE_ENABLE_WEB_AUTH':'true','PETSENSE_PUBLIC_ORIGIN':'https://test','PETSENSE_OPERATOR_NAME':'Test','PETSENSE_PRIVACY_CONTACT':'test@example.invalid','PETSENSE_TERMS_VERSION':'test','PETSENSE_PRIVACY_VERSION':'test','PETSENSE_SIGNUP_MODE':'open'}):
   async def scenario():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as c:
     h={'Origin':'https://test','X-PetSense-Request':'web'}
     signup=await c.post('/v1/auth/signup',headers=h,json={'email':'metadata@example.invalid','password':'synthetic-private-password','accept_terms':True,'accept_privacy':True,'terms_version':'test','privacy_version':'test'});self.assertEqual(signup.status_code,201)
     csrf=(await c.get('/v1/auth/session')).json()['csrf_token'];h.update({'X-PetSense-CSRF':csrf,'X-Storage-Consent':'true'})
     pet=(await c.post('/v1/me/pets',headers=h,json={'name':'dog'})).json()['id'];jobs=JobStore(td+'/db');raw=wav();job=jobs.enqueue(c.cookies.get('__Host-petsense_session'),pet,'api-measurement-job-01',raw);claim=jobs.claim();jobs.finish(claim,{**result(raw),'execution_kind':'synthetic_fixture','duration_seconds':1.})
     body={'job_id':job['id'],'device_id':'phone','condition':'unknown','same_dog_confirmed':True}
     self.assertEqual((await c.post('/v1/me/observations',headers=h,json=body)).status_code,403)
     h['X-Observation-Consent']='model-metadata-v1'
     self.assertEqual((await c.post('/v1/me/observations',headers={k:v for k,v in h.items() if k!='X-PetSense-CSRF'},json=body)).status_code,403)
     for change in ({'same_dog_confirmed':False},{'execution_kind':'pretrained_model'}):
      self.assertEqual((await c.post('/v1/me/observations',headers=h,json={**body,**change})).status_code,422)
     saved=await c.post('/v1/me/observations',headers=h,json=body);self.assertEqual(saved.status_code,201,saved.text);ident=saved.json()['id']
     self.assertEqual((await c.post('/v1/me/observations/'+ident+'/feedback',headers=h,json={'reason':'noise','status':'approved'})).status_code,422)
     report=await c.get('/v1/me/observations',params={'pet_id':pet,'device_id':'phone','condition':'unknown','source_kind':'synthetic_fixture'});self.assertEqual(report.headers['cache-control'],'no-store');self.assertEqual(len(report.json()['items']),1)
     self.assertEqual((await c.delete('/v1/me/observations/'+ident,headers=h)).status_code,400)
     self.assertEqual((await c.delete('/v1/me/observations/'+ident,headers={**h,'X-Delete-Confirm':'delete-observation'})).status_code,204)
   asyncio.run(scenario())

