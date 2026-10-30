"""Synthetic HTTPS membership → profile/note → queue/worker → recovery/deletion.

The ephemeral certificate is trusted by Chromium's SPKI pin, never by a production
TLS bypass. No credentials, cookies, recovery codes or private screenshots are saved.
"""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
import wave

from playwright.sync_api import sync_playwright, expect
from backend.accounts import Store
from scripts.job_browser_smoke import MOCK_WORKER, stop
from training.pretrained_audio import MODEL, REVISION

ROOT = Path(__file__).resolve().parents[1]


def certificate(folder):
    cert, key = folder / 'test.crt', folder / 'test.key'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
        '-keyout', str(key), '-out', str(cert), '-days', '1', '-subj', '/CN=localhost',
        '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1'], check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pub = subprocess.run(['openssl', 'x509', '-in', str(cert), '-pubkey', '-noout'],
        check=True, capture_output=True).stdout
    der = subprocess.run(['openssl', 'pkey', '-pubin', '-outform', 'DER'],
        input=pub, check=True, capture_output=True).stdout
    return cert, key, base64.b64encode(hashlib.sha256(der).digest()).decode()


def backup(page):
    expect(page.locator('#auth-recovery')).to_be_visible()
    code = page.locator('#auth-recovery-code').input_value()
    assert len(code) == 43
    page.locator('#auth-recovery-ack').check()
    page.locator('#auth-recovery-done').click()
    return code


def login(page, base, email, password):
    page.goto(base + '/auth#login')
    expect(page.locator('#form-login button')).to_be_enabled()
    page.locator('#login-email').fill(email)
    page.locator('#login-password').fill(password)
    page.locator('#form-login button').click()
    page.wait_for_url('**/app')
    expect(page.locator('#web-logout')).to_be_visible()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real-ast', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        raise FileExistsError('Use fresh evidence output')
    with tempfile.TemporaryDirectory() as td:
        folder = Path(td)
        cert, key, pin = certificate(folder)
        db = folder / 'private.sqlite3'
        store = Store(db)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        base = f'https://localhost:{port}'
        env = {**os.environ, 'PETSENSE_ACCOUNT_DB': str(db),
            'PETSENSE_ENABLE_WEB_AUTH': 'true', 'PETSENSE_PUBLIC_ORIGIN': base,
            'PETSENSE_OPERATOR_NAME': 'Synthetic test operator',
            'PETSENSE_PRIVACY_CONTACT': 'privacy@example.invalid',
            'PETSENSE_TERMS_VERSION': 'test-v1', 'PETSENSE_PRIVACY_VERSION': 'test-v1',
            'PETSENSE_ENABLE_AST_JOBS': 'true', 'PETSENSE_ENABLE_AST': 'false',
            'PETSENSE_ENABLE_CLOUD': 'false', 'PETSENSE_ENABLE_KNOWLEDGE': 'false'}
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app',
            '--host', '127.0.0.1', '--port', str(port), '--ssl-certfile', str(cert),
            '--ssl-keyfile', str(key)], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        command = [sys.executable, '-m', 'backend.job_worker', '--db', str(db), '--watch'] if args.real_ast else [sys.executable, '-c', MOCK_WORKER, str(db)]
        worker = subprocess.Popen(command, cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            trust = ssl.create_default_context(cafile=str(cert))
            for _ in range(100):
                try:
                    with urllib.request.urlopen(base + '/healthz', context=trust, timeout=.3):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('HTTPS test server unavailable')
            raw = io.BytesIO()
            with wave.open(raw, 'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(44100)
                wav.writeframes(bytes(88200))
            email = 'synthetic@example.invalid'
            password, new_password = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
            with sync_playwright() as pw:
                browser = pw.chromium.launch(args=['--ignore-certificate-errors-spki-list=' + pin])
                try:
                    context = browser.new_context()
                    # Fail immediately if membership reads or writes legacy shared history.
                    context.add_init_script("""(() => {
                        window.memberStorageViolations=[];
                        const get=Storage.prototype.getItem, set=Storage.prototype.setItem;
                        Storage.prototype.getItem=function(key){if(key==='petsense.observations.v1'){memberStorageViolations.push('read');throw new Error('Legacy history read')}return get.call(this,key)};
                        Storage.prototype.setItem=function(key,value){if(key==='petsense.observations.v1'){memberStorageViolations.push('write');throw new Error('Legacy history write')}return set.call(this,key,value)};
                    })()""")
                    page = context.new_page(); errors = []; forbidden_headers = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('request', lambda req: forbidden_headers.append(True) if '/v1/' in req.url and 'x-petsense-session' in req.headers else None)
                    page.goto(base + '/auth#signup')
                    expect(page.locator('#form-signup button')).to_be_enabled()
                    page.locator('#signup-email').fill(email)
                    page.locator('#signup-password').fill(password)
                    page.locator('#signup-confirm').fill(password)
                    page.locator('#signup-terms').check(); page.locator('#signup-privacy').check()
                    page.locator('#form-signup button').click()
                    recovery = backup(page)
                    page.wait_for_url('**/app')
                    expect(page.locator('#web-logout')).to_be_visible()
                    cookies = [c for c in context.cookies() if c['name'] == '__Host-petsense_session']
                    assert len(cookies) == 1 and cookies[0]['httpOnly'] and cookies[0]['secure'] and cookies[0]['sameSite'] == 'Strict'
                    assert '__Host-petsense_session' not in page.evaluate('document.cookie')
                    expect(page.locator('#development-session')).to_be_hidden()
                    expect(page.locator('#history')).to_be_hidden()
                    assert page.evaluate('memberStorageViolations.length') == 0
                    page.locator('#notes-consent').check()
                    page.locator('#profile-name').fill('합성 검사용 반려견')
                    page.locator('#profile-create').click()
                    expect(page.locator('#profile-list article')).to_have_count(1)
                    page.locator('#context').fill('실제 행동 정답이 아닌 합성 브라우저 검증')
                    page.locator('#notes-save').click()
                    expect(page.locator('#notes-list article')).to_have_count(1)
                    page.locator('#audio').set_input_files({'name': 'synthetic.wav', 'mimeType': 'audio/wav', 'buffer': raw.getvalue()})
                    page.locator('#consent').check(); page.locator('#job-consent').check()
                    started = time.monotonic(); page.locator('#job-submit').click()
                    expect(page.locator('#jobs-list strong')).to_contain_text('완료', timeout=90000)
                    seconds = time.monotonic() - started
                    job = page.evaluate("async()=>{const r=await fetch('/v1/me/audio-jobs');if(!r.ok)throw new Error('Job lookup failed');return (await r.json()).items[0]}")
                    result = job['result']
                    assert job['status'] == 'succeeded' and result['decision'] == 'abstain' and len(result['dog_event_scores']) == 7
                    if args.real_ast:
                        assert result['model'] == MODEL and result['revision'] == REVISION
                    page.locator('#web-logout').click()
                    expect(page.locator('#web-logout')).to_be_hidden()
                    assert page.locator('#audio').input_value() == ''
                    assert page.locator('#pet').input_value() == '' and page.locator('#context').input_value() == ''
                    for selector in ['#profile-list article', '#notes-list article', '#jobs-list article']:
                        expect(page.locator(selector)).to_have_count(0)
                    login(page, base, email, password)
                    page.locator('#profile-load').click()
                    expect(page.locator('#profile-list article')).to_have_count(1)
                    page.locator('#notes-load').click()
                    expect(page.locator('#notes-list article')).to_have_count(1)
                    page.locator('#jobs-refresh').click()
                    expect(page.locator('#jobs-list strong')).to_contain_text('완료')
                    page.locator('#web-logout').click()
                    expect(page.locator('#web-logout')).to_be_hidden()
                    page.goto(base + '/auth#recover')
                    expect(page.locator('#form-recover button')).to_be_enabled()
                    page.locator('#recover-email').fill(email); page.locator('#recover-code').fill(recovery)
                    page.locator('#recover-password').fill(new_password); page.locator('#recover-confirm').fill(new_password)
                    page.locator('#form-recover button').click()
                    assert backup(page) != recovery
                    login(page, base, email, new_password)
                    page.goto(base + '/auth#account')
                    expect(page.locator('#form-delete button')).to_be_enabled()
                    page.locator('#delete-password').fill(new_password); page.locator('#delete-confirm').check()
                    page.locator('#form-delete button').click()
                    expect(page.locator('#auth-status')).to_contain_text('삭제했습니다')
                    with store.connect() as conn:
                        for table in ['members', 'sessions', 'pets', 'notes', 'audio_jobs', 'audio_usage']:
                            assert conn.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0
                    storage = page.evaluate('JSON.stringify([localStorage,sessionStorage])')
                    assert all(value not in storage for value in [password, new_password, recovery, email, cookies[0]['value']])
                    assert not errors, errors
                    assert not forbidden_headers, 'Raw session sent by JavaScript'
                    if args.output:
                        args.output.parent.mkdir(parents=True, exist_ok=True)
                        with args.output.open('x') as out:
                            json.dump({'synthetic_input': True, 'real_ast': args.real_ast,
                                'https_signup_login_recovery_deletion': True, 'cookie_flags_verified': True,
                                'javascript_session_header_absent': True, 'account_data_erased': True,
                                'model': result.get('model'), 'revision': result.get('revision'),
                                'input_sha256': result.get('input_sha256'), 'queue_result_seconds': seconds,
                                'physical_device': False, 'scope': 'One synthetic HTTPS Chromium run; not email verification, dog behavior accuracy or production security audit.'}, out, indent=2)
                    print('HTTPS membership smoke passed: signup, secure cookie, profile/note, queue worker, logout/login, recovery and password-confirmed deletion; AST ' + ('real pinned weights.' if args.real_ast else 'mocked.'))
                finally:
                    browser.close()
        finally:
            stop(worker); stop(server)


if __name__ == '__main__':
    main()
