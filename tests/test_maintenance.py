import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from backend.accounts import Note, Store, RETENTION, SCHEMA_VERSION
from backend.job_store import JobStore
from scripts.privacy_maintenance import cleanup_once, write_status
from test_audio_jobs import wav, result


class PrivacyMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'private.sqlite3';self.now=[1000]
        self.clock=lambda:self.now[0]
        self.store=JobStore(self.path,clock=self.clock)
        self.owner,self.token=self.store.issue(ttl=604800)
        self.pet=self.store.pet_create(self.token,'private-dog')['id']

    def test_idle_server_media_expiry_preserves_fresh_job_and_redacts_report(self):
        first=self.store.enqueue(self.token,self.pet,'first-maintenance-key',wav())
        self.now[0]=1850
        second=self.store.enqueue(self.token,self.pet,'second-maintenance-key',wav())
        self.now[0]=1901
        report=cleanup_once(self.path,clock=self.clock)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT status,media FROM audio_jobs WHERE id=?',(first['id'],)).fetchone()[0],'expired')
            self.assertIsNone(db.execute('SELECT media FROM audio_jobs WHERE id=?',(first['id'],)).fetchone()[0])
            self.assertIsNotNone(db.execute('SELECT media FROM audio_jobs WHERE id=?',(second['id'],)).fetchone()[0])
        self.assertEqual(report['media_cleared'],1)
        for secret in [self.token,self.owner,self.pet,'private-dog',str(self.path)]:self.assertNotIn(secret,json.dumps(report))
        self.assertEqual(cleanup_once(self.path,clock=self.clock)['media_cleared'],0)

    def test_lost_worker_and_revoked_session_prevent_late_result(self):
        self.store.enqueue(self.token,self.pet,'lost-worker-maintenance',wav());claim=self.store.claim()
        self.now[0]+=91;cleanup_once(self.path,clock=self.clock)
        self.assertFalse(self.store.finish(claim,result(wav())))
        job=self.store.enqueue(self.token,self.pet,'revoked-maintenance-key',wav())
        with self.store.connect() as db:db.execute('DELETE FROM sessions WHERE owner=?',(self.owner,))
        cleanup_once(self.path,clock=self.clock)
        with self.store.connect() as db:
            row=db.execute('SELECT status,media FROM audio_jobs WHERE id=?',(job['id'],)).fetchone()
            self.assertEqual(row[0],'cancelled');self.assertIsNone(row[1])

    def test_expired_notes_profiles_sessions_and_security_buckets_are_removed(self):
        self.store.add(self.token,Note(pet='private-dog',pet_id=self.pet,context='private-context'))
        with self.store.connect() as db:
            db.execute('INSERT INTO auth_limits VALUES(?,?,?)',('private-peer-hash',1000,1))
            db.execute('INSERT INTO auth_leases VALUES(?,?)',('private-lease',1045))
        self.now[0]+=RETENTION+1
        report=cleanup_once(self.path,clock=self.clock)
        for table in ['notes','pets','sessions','auth_limits','auth_leases']:
            self.assertEqual(report['remaining'][table],0)
        self.assertEqual(report['removed']['notes'],1)
        output=Path(self.temp.name)/'health.json';write_status(output,report)
        self.assertEqual(json.loads(output.read_text())['status'],'ok')

    def test_refuses_missing_foreign_legacy_or_future_database_without_creation_or_migration(self):
        missing=Path(self.temp.name)/'missing.sqlite3'
        with self.assertRaises(ValueError):cleanup_once(missing)
        self.assertFalse(missing.exists())
        for version in [0,SCHEMA_VERSION-1,SCHEMA_VERSION+1]:
            foreign=Path(self.temp.name)/f'foreign-{version}.sqlite3'
            with sqlite3.connect(foreign) as db:db.execute('PRAGMA user_version='+str(version))
            with self.assertRaises(ValueError):cleanup_once(foreign)
            with sqlite3.connect(foreign) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],version)
