"""Explicit local TTL maintenance independent of API traffic or model workers.

Only an existing current-schema PetSense DB is accepted. No migration, model/API
calls, backups, user identifiers or media are emitted by this command.
"""
import argparse
from contextlib import closing
import datetime
import json
import os
from pathlib import Path
import signal
import sqlite3
import tempfile
import threading
import time
from backend.accounts import Store,SCHEMA_VERSION

TABLES=('sessions','notes','pets','audio_jobs','audio_usage','auth_limits','auth_leases','journal_cases','journal_followups','care_shares','care_plans')


def timestamp(clock):
    return datetime.datetime.fromtimestamp(clock(),datetime.timezone.utc).isoformat()


def cleanup_once(path,clock=time.time):
    path=Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError('An existing private PetSense database is required')
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        names={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if db.execute('PRAGMA user_version').fetchone()[0]!=SCHEMA_VERSION or not set(TABLES+('members',)).issubset(names):
            raise ValueError('Initialize the current PetSense schema before maintenance')
    store=Store(path,clock=clock)
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        before={table:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in TABLES}
        media=db.execute('SELECT count(*) FROM audio_jobs WHERE media IS NOT NULL').fetchone()[0]
        store._purge(db)
        remaining={table:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in TABLES}
        cleared=media-db.execute('SELECT count(*) FROM audio_jobs WHERE media IS NOT NULL').fetchone()[0]
    return {'status':'ok','observed_at_utc':timestamp(clock),'schema':SCHEMA_VERSION,
        'removed':{table:before[table]-remaining[table] for table in TABLES},
        'remaining':remaining,'media_cleared':cleared,
        'scope':'Local current DB TTL cleanup; no backup, swap, powered-off disk or operating-system deletion guarantee.'}


def write_status(path,report):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,prefix='.petsense-maintenance-',delete=False) as out:
            temporary=Path(out.name);json.dump(report,out,indent=2)
            out.flush();os.fsync(out.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',required=True,type=Path)
    parser.add_argument('--watch',action='store_true')
    parser.add_argument('--interval',default=30,type=float)
    parser.add_argument('--status-file',type=Path)
    args=parser.parse_args()
    if not 5<=args.interval<=300:parser.error('Interval must be between 5 and 300 seconds')
    if args.status_file and (args.status_file.resolve()==args.db.resolve() or args.status_file.exists() and args.db.exists() and args.status_file.samefile(args.db)):
        parser.error('Status output must differ from database')
    stopped=threading.Event()
    for name in ('SIGTERM','SIGINT'):
        if hasattr(signal,name):signal.signal(getattr(signal,name),lambda *_:stopped.set())
    while not stopped.is_set():
        code=0
        try:
            report=cleanup_once(args.db)
            if args.status_file:write_status(args.status_file,report)
        except (OSError,sqlite3.Error,ValueError):
            code=1;report={'status':'error','observed_at_utc':timestamp(time.time),'notice':'Maintenance failed; check private DB access, schema and status output. No private details logged.'}
            if args.status_file:
                try:write_status(args.status_file,report)
                except OSError:pass
        print(json.dumps(report),flush=True)
        if not args.watch:raise SystemExit(code)
        stopped.wait(args.interval)


if __name__=='__main__':main()
