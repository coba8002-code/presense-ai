import unittest,tempfile,os
from pathlib import Path
from backend.accounts import Store
from backend.signup_policy import permitted,policy
from scripts.beta_preflight import inspect

class PreflightTests(unittest.TestCase):
    def test_signup_modes_and_malformed_policy(self):
        self.assertTrue(permitted({},'test@example.invalid'))
        self.assertFalse(permitted({'PETSENSE_SIGNUP_MODE':'closed'},'test@example.invalid'))
        env={'PETSENSE_SIGNUP_MODE':'allowlist','PETSENSE_SIGNUP_ALLOWLIST':'Test@example.invalid'}
        self.assertTrue(permitted(env,'test@example.invalid'));self.assertFalse(permitted(env,'other@example.invalid'))
        for invalid in [{'PETSENSE_SIGNUP_MODE':'oops'},{'PETSENSE_SIGNUP_MODE':'allowlist'},{'PETSENSE_SIGNUP_ALLOWLIST':'bad'}]:
            with self.assertRaises(ValueError):policy(invalid)
    def test_configuration_and_private_schema_fail_closed_without_values(self):
        import json
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'private.db';Store(db)
            env={'PETSENSE_ACCOUNT_DB':str(db),'PETSENSE_ENABLE_WEB_AUTH':'true','PETSENSE_PUBLIC_ORIGIN':'https://pets.example.kr','PETSENSE_OPERATOR_NAME':'Private operator','PETSENSE_PRIVACY_CONTACT':'private@example.kr','PETSENSE_TERMS_VERSION':'v1','PETSENSE_PRIVACY_VERSION':'v1','PETSENSE_SIGNUP_MODE':'closed','PETSENSE_REQUIRE_ACCOUNT':'true'}
            report=inspect(env);self.assertTrue(report['configuration_ready_for_private_beta'])
            for secret in [str(db),'private@example.kr','Private operator']:self.assertNotIn(secret,json.dumps(report))
            for key,value in [('PETSENSE_PUBLIC_ORIGIN','http://pets.example.kr'),('PETSENSE_SIGNUP_MODE','open'),('PETSENSE_ENABLE_CLOUD','true'),('PETSENSE_REQUIRE_ACCOUNT','false')]:
                self.assertFalse(inspect({**env,key:value})['configuration_ready_for_private_beta'])
            with Store(db).connect() as conn:conn.execute('PRAGMA user_version=999')
            self.assertFalse(inspect(env)['configuration_ready_for_private_beta'])
            if os.name=='posix':
                db.chmod(0o644);self.assertFalse(inspect(env)['configuration_ready_for_private_beta'])

class EnrollmentApiTests(unittest.TestCase):
    def test_closed_allowlist_and_invalid_policy_reject_before_account_creation(self):
        import asyncio,httpx
        from unittest.mock import patch
        from backend.app import app
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':td+'/db','PETSENSE_ENABLE_WEB_AUTH':'true','PETSENSE_PUBLIC_ORIGIN':'https://test','PETSENSE_OPERATOR_NAME':'test','PETSENSE_PRIVACY_CONTACT':'test@example.invalid','PETSENSE_TERMS_VERSION':'v1','PETSENSE_PRIVACY_VERSION':'v1','PETSENSE_SIGNUP_ALLOWLIST':''}):
            async def run():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                    for mode,allow,status in [('closed','',403),('allowlist','allowed@example.invalid',403),('bad','',503)]:
                        with patch.dict(os.environ,{'PETSENSE_SIGNUP_MODE':mode,'PETSENSE_SIGNUP_ALLOWLIST':allow}):
                            result=await client.post('/v1/auth/signup',headers={'Origin':'https://test','X-PetSense-Request':'web'},json={'email':'outsider@example.invalid','password':'synthetic-password-12345','accept_terms':True,'accept_privacy':True,'terms_version':'v1','privacy_version':'v1'})
                            self.assertEqual(result.status_code,status)
                            self.assertNotIn('allowed@example.invalid',result.text)
                    self.assertFalse(Path(td+'/db').exists())
            asyncio.run(run())
