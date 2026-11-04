import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
import asyncio
import os
from unittest.mock import patch
import httpx
import threading
import time
from types import SimpleNamespace
from backend.app import app

from backend.auth_store import AuthStore,AuthLimit,AuthBusy
from backend.accounts import Note

PASSWORD='canine-owner-password-2026'
NEXT_PASSWORD='different-canine-password-2026'

class WebAuthStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'accounts.sqlite3';self.now=[1000000]
        self.store=AuthStore(self.path,clock=lambda:self.now[0])

    def register(self,email='guardian@example.com'):
        return self.store.register(email,PASSWORD,'test-terms-v1','test-privacy-v1')

    def test_register_hashes_password_recovery_and_session_and_normalizes_email(self):
        member=self.register('Guardian@Example.com')
        raw=self.path.read_bytes()
        for secret in [PASSWORD,member['recovery_code'],member['token']]:self.assertNotIn(secret.encode(),raw)
        self.assertEqual(self.store.member(member['token'])['email'],'guardian@example.com')
        self.assertFalse(self.store.member(member['token'])['email_verified'])
        with self.assertRaises(ValueError):self.register('guardian@example.com')

    def test_login_uses_existing_owner_and_rejects_wrong_or_unknown_credentials(self):
        first=self.register();owner,token=self.store.login('guardian@example.com',PASSWORD)
        self.assertEqual(owner,first['owner']);self.assertNotEqual(token,first['token'])
        for email,password in [('guardian@example.com',NEXT_PASSWORD),('absent@example.com',PASSWORD)]:
            with self.assertRaises(PermissionError):self.store.login(email,password)

    def test_recovery_rotates_code_and_revokes_all_sessions(self):
        first=self.register();_,other=self.store.login('guardian@example.com',PASSWORD)
        fresh=self.store.recover('guardian@example.com',first['recovery_code'],NEXT_PASSWORD)
        self.assertNotEqual(fresh,first['recovery_code'])
        self.assertIsNone(self.store.authenticate(first['token']));self.assertIsNone(self.store.authenticate(other))
        with self.assertRaises(PermissionError):self.store.login('guardian@example.com',PASSWORD)
        self.assertEqual(self.store.login('guardian@example.com',NEXT_PASSWORD)[0],first['owner'])
        with self.assertRaises(PermissionError):self.store.recover('guardian@example.com',first['recovery_code'],PASSWORD)

    def test_password_change_needs_current_password_and_rotates_session(self):
        first=self.register()
        with self.assertRaises(PermissionError):self.store.change(first['token'],NEXT_PASSWORD,PASSWORD)
        token,code=self.store.change(first['token'],PASSWORD,NEXT_PASSWORD)
        self.assertIsNone(self.store.authenticate(first['token']));self.assertEqual(self.store.authenticate(token),first['owner'])
        self.assertNotEqual(code,first['recovery_code'])

    def test_account_delete_needs_password_and_removes_owned_records_only(self):
        a=self.register();b=self.register('another@example.com')
        pet=self.store.pet_create(a['token'],'dog')
        self.store.add(a['token'],Note(pet='dog',pet_id=pet['id'],context='private'))
        with self.assertRaises(PermissionError):self.store.delete_member(a['token'],NEXT_PASSWORD)
        self.store.delete_member(a['token'],PASSWORD)
        self.assertIsNone(self.store.authenticate(a['token']));self.assertEqual(self.store.authenticate(b['token']),b['owner'])
        with self.store.connect() as db:
            for table in ['members','pets','notes','sessions','audio_jobs','audio_usage']:
                self.assertEqual(db.execute('SELECT count(*) FROM '+table+' WHERE owner=?',(a['owner'],)).fetchone()[0],0)

    def test_rate_limit_and_global_kdf_lease_are_persistent(self):
        lease=self.store.reserve('127.0.0.1','guardian@example.com','login')
        other=AuthStore(self.path,clock=lambda:self.now[0])
        with self.assertRaises(AuthBusy):other.reserve('127.0.0.2','another@example.com','login')
        self.store.release(lease)
        for _ in range(9):
            lease=self.store.reserve('127.0.0.1','guardian@example.com','login');self.store.release(lease)
        with self.assertRaises(AuthLimit):self.store.reserve('127.0.0.1','guardian@example.com','login')
        self.now[0]+=901;lease=other.reserve('127.0.0.1','guardian@example.com','login');other.release(lease)

    def test_validation_and_logout(self):
        for email,password in [('not-email',PASSWORD),('guardian@example.com','short'),('guardian@example.com','x'*129)]:
            with self.assertRaises(ValueError):self.store.register(email,password,'v1','v1')
        first=self.register();self.store.logout(first['token']);self.assertIsNone(self.store.authenticate(first['token']))

    def test_cancelled_request_holds_lease_until_password_work_finishes(self):
        from backend.web_auth import password_action
        started=threading.Event();finished=threading.Event()
        def work():started.set();time.sleep(.1);finished.set()
        async def scenario():
            req=SimpleNamespace(client=SimpleNamespace(host='127.0.0.1'))
            task=asyncio.create_task(password_action(self.store,req,'guardian@example.com','login',work))
            while not started.is_set():await asyncio.sleep(.005)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
            self.assertTrue(finished.is_set())
            with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM auth_leases').fetchone()[0],0)
        asyncio.run(scenario())

    def test_v3_upgrade_preserves_operator_profiles_without_email_claim(self):
        owner,token=self.store.issue();pet=self.store.pet_create(token,'legacy')
        with self.store.connect() as db:
            for table in ['members','auth_limits','auth_leases']:db.execute('DROP TABLE '+table)
            db.execute('PRAGMA user_version=3')
        upgraded=AuthStore(self.path,clock=lambda:self.now[0])
        self.assertEqual(upgraded.authenticate(token),owner);self.assertEqual(upgraded.pet_list(token)[0]['id'],pet['id'])
        with upgraded.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM members').fetchone()[0],0)


class WebAuthApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'accounts.sqlite3'
        env=patch.dict(os.environ,{'PETSENSE_ACCOUNT_DB':str(self.path),'PETSENSE_ENABLE_WEB_AUTH':'true',
            'PETSENSE_PUBLIC_ORIGIN':'https://test','PETSENSE_OPERATOR_NAME':'Test operator',
            'PETSENSE_PRIVACY_CONTACT':'support@example.test','PETSENSE_TERMS_VERSION':'test-v1','PETSENSE_PRIVACY_VERSION':'test-v1'})
        env.start();self.addCleanup(env.stop)

    def signup(self):return {'email':'guardian@example.com','password':PASSWORD,'accept_terms':True,'accept_privacy':True,'terms_version':'test-v1','privacy_version':'test-v1'}
    def headers(self):return {'Origin':'https://test','X-PetSense-Request':'web'}

    def test_secure_cookie_csrf_and_linked_private_apis(self):
        async def scenario():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                response=await client.post('/v1/auth/signup',headers=self.headers(),json=self.signup())
                self.assertEqual(response.status_code,201,response.text)
                cookie=response.headers['set-cookie'].lower()
                for value in ['httponly','secure','samesite=strict','path=/']:self.assertIn(value,cookie)
                self.assertEqual(response.headers['cache-control'],'no-store')
                self.assertNotIn('token',response.json());self.assertIn('recovery_code',response.json())
                session=await client.get('/v1/auth/session');self.assertEqual(session.status_code,200)
                csrf=session.json()['csrf_token'];headers={**self.headers(),'X-PetSense-CSRF':csrf,'X-Storage-Consent':'true'}
                self.assertEqual((await client.post('/v1/me/pets',json={'name':'dog'})).status_code,403)
                created=await client.post('/v1/me/pets',headers=headers,json={'name':'dog'})
                self.assertEqual(created.status_code,201,created.text)
                self.assertEqual(len((await client.get('/v1/me/pets')).json()['items']),1)
                self.assertEqual((await client.delete('/v1/me/account',headers={**headers,'X-Delete-Confirm':'delete-account'})).status_code,403)
                self.assertEqual((await client.post('/v1/auth/logout',headers=headers)).status_code,204)
                self.assertEqual((await client.get('/v1/me/pets')).status_code,401)
        asyncio.run(scenario())

    def test_rejects_cross_origin_http_missing_consent_stale_policy_and_injection(self):
        async def scenario():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                for headers,body,expected in [({**self.headers(),'Origin':'https://evil.test'},self.signup(),403),
                    ({},self.signup(),403),(self.headers(),{**self.signup(),'accept_terms':False},403),
                    (self.headers(),{**self.signup(),'terms_version':'stale'},409),
                    (self.headers(),{**self.signup(),'owner':'injected'},422)]:
                    response=await client.post('/v1/auth/signup',headers=headers,json=body)
                    self.assertEqual(response.status_code,expected,response.text)
                self.assertEqual((await client.post('/v1/auth/signup',headers=self.headers(),content=b'x'*4097)).status_code,413)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                self.assertEqual((await client.post('/v1/auth/signup',headers=self.headers(),json=self.signup())).status_code,403)
        asyncio.run(scenario())

    def test_cookie_and_header_conflict_and_password_reauthenticated_deletion(self):
        async def scenario():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                self.assertEqual((await client.post('/v1/auth/signup',headers=self.headers(),json=self.signup())).status_code,201)
                csrf=(await client.get('/v1/auth/session')).json()['csrf_token']
                self.assertEqual((await client.get('/v1/me/pets',headers={'X-PetSense-Session':'another-session'})).status_code,401)
                headers={**self.headers(),'X-PetSense-CSRF':csrf}
                bad=await client.post('/v1/auth/delete',headers=headers,json={'password':NEXT_PASSWORD})
                self.assertEqual(bad.status_code,401)
                good=await client.post('/v1/auth/delete',headers=headers,json={'password':PASSWORD})
                self.assertEqual(good.status_code,204,good.text)
                self.assertEqual((await client.get('/v1/auth/session')).status_code,401)
        asyncio.run(scenario())

    def test_password_and_recovery_rotation_change_csrf_and_reject_reuse(self):
        async def scenario():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                first=(await client.post('/v1/auth/signup',headers=self.headers(),json=self.signup())).json()
                old_csrf=(await client.get('/v1/auth/session')).json()['csrf_token']
                changed=await client.post('/v1/auth/password',headers={**self.headers(),'X-PetSense-CSRF':old_csrf},json={'password':PASSWORD,'new_password':NEXT_PASSWORD})
                self.assertEqual(changed.status_code,200,changed.text)
                csrf=(await client.get('/v1/auth/session')).json()['csrf_token'];self.assertNotEqual(old_csrf,csrf)
                self.assertEqual((await client.post('/v1/me/pets',headers={**self.headers(),'X-PetSense-CSRF':old_csrf,'X-Storage-Consent':'true'},json={'name':'dog'})).status_code,403)
                recovered=await client.post('/v1/auth/recover',headers=self.headers(),json={'email':'guardian@example.com','password':PASSWORD,'recovery_code':changed.json()['recovery_code']})
                self.assertEqual(recovered.status_code,200,recovered.text)
                self.assertEqual((await client.get('/v1/auth/session')).status_code,401)
                self.assertEqual((await client.post('/v1/auth/login',headers=self.headers(),json={'email':'guardian@example.com','password':NEXT_PASSWORD})).status_code,401)
                self.assertEqual((await client.post('/v1/auth/login',headers=self.headers(),json={'email':'guardian@example.com','password':PASSWORD})).status_code,200)
                self.assertEqual((await client.post('/v1/auth/recover',headers=self.headers(),json={'email':'guardian@example.com','password':NEXT_PASSWORD,'recovery_code':first['recovery_code']})).status_code,401)
        asyncio.run(scenario())

    def test_disabled_config_and_validation_never_echo_private_input(self):
        async def scenario():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
                with patch.dict(os.environ,{'PETSENSE_ENABLE_WEB_AUTH':'false'}):
                    self.assertEqual((await client.get('/v1/auth/config')).json(),{'enabled':False})
                    self.assertEqual((await client.post('/v1/auth/signup',headers=self.headers(),json=self.signup())).status_code,503)
                marker='private-short'
                response=await client.post('/v1/auth/signup',headers=self.headers(),json={**self.signup(),'password':marker})
                self.assertEqual(response.status_code,422);self.assertNotIn(marker,response.text)
        asyncio.run(scenario())


if __name__=='__main__':unittest.main()
