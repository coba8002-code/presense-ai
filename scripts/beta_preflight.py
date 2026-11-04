"""Read-only limited-beta configuration check. Never prints configuration values."""
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit
from backend.accounts import SCHEMA_VERSION
from backend.auth_store import email_value
from backend.signup_policy import policy


def inspect(env):
    checks={}
    origin=env.get('PETSENSE_PUBLIC_ORIGIN','')
    try:
        url=urlsplit(origin)
        checks['https_origin']=bool(url.scheme=='https' and url.hostname and url.hostname not in ('localhost','127.0.0.1','::1') and not url.path.strip('/') and not url.query and not url.fragment and not url.username and not url.password and not any(c.isspace() for c in origin) and url.port in (None,443))
    except ValueError:checks['https_origin']=False
    checks['web_auth']=env.get('PETSENSE_ENABLE_WEB_AUTH','').lower()=='true'
    checks['account_required']=env.get('PETSENSE_REQUIRE_ACCOUNT','').lower()=='true'
    try:
        email_value(env.get('PETSENSE_PRIVACY_CONTACT',''))
        checks['operator_and_policies']=all(0<len(env.get(k,'').strip())<=100 for k in ('PETSENSE_OPERATOR_NAME','PETSENSE_TERMS_VERSION','PETSENSE_PRIVACY_VERSION'))
    except ValueError:checks['operator_and_policies']=False
    try:checks['restricted_signup']=policy(env)[0] in ('closed','allowlist')
    except ValueError:checks['restricted_signup']=False
    checks['external_features_disabled']=all(env.get(k,'false').lower()=='false' for k in ('PETSENSE_ENABLE_CLOUD','PETSENSE_ENABLE_KNOWLEDGE','PETSENSE_ENABLE_AST'))
    raw=env.get('PETSENSE_ACCOUNT_DB','');db=Path(raw)
    checks['private_current_database']=False
    try:
        private=(os.name=='posix' and db.is_absolute() and db.is_file() and not db.is_symlink() and db.stat().st_mode&0o077==0 and db.parent.stat().st_mode&0o077==0 and db.stat().st_uid==os.getuid())
        if private:
            with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)) as conn:
                tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                checks['private_current_database']=conn.execute('PRAGMA user_version').fetchone()[0]==SCHEMA_VERSION and {'members','sessions','care_plans','care_shares','journal_cases','journal_followups','audio_jobs'}.issubset(tables) and conn.execute('PRAGMA quick_check').fetchone()[0]=='ok'
    except (OSError,ValueError,sqlite3.Error):pass
    return {'configuration_ready_for_private_beta':all(checks.values()),'checks':checks,'email_ownership_verified':False,'recovery':'one_time_offline_code','external_checks_pending':['DNS and real HTTPS','model cache and worker readiness','physical phones','backup/deletion recovery drill','independent dog behavior evaluation'],'production_ready':False}

def main():
    report=inspect(os.environ);print(json.dumps(report,indent=2))
    return 0 if report['configuration_ready_for_private_beta'] else 2
if __name__=='__main__':raise SystemExit(main())
