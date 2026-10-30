"""Chromium/HTTP/storage smoke; synthetic WAV; optional real AST, never model accuracy."""
import argparse
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import wave
from playwright.sync_api import sync_playwright,expect
from backend.accounts import Store

ROOT=Path(__file__).resolve().parents[1]

def failure_recovery(page,data,response):
    """Controlled browser failures; no physical-device/network reliability claim."""
    page.locator('#pet').fill('복구 검사')
    page.locator('#audio').set_input_files({'name':'test.wav','mimeType':'audio/wav','buffer':data})
    page.locator('summary').click();page.locator('#token').fill('test-only');page.locator('#consent').check()
    for code,message in [(429,'분석 요청이 많습니다'),(503,'AST 모델 설정')]:
        page.unroute('**/v1/audio/events')
        calls=[]
        def failed(route):
            calls.append(True)
            route.fulfill(status=code,content_type='application/json',body='{}')
        page.route('**/v1/audio/events',failed)
        page.locator('#submit').click()
        expect(page.locator('#status')).to_contain_text(message)
        expect(page.locator('#submit')).to_be_enabled();expect(page.locator('#save')).to_be_hidden()
        assert len(calls)==1
    page.unroute('**/v1/audio/events')
    page.context.set_offline(True)
    try:
        page.locator('#submit').click()
        expect(page.locator('#status')).to_contain_text('서버에 연결하지 못했습니다')
        expect(page.locator('#submit')).to_be_enabled();expect(page.locator('#save')).to_be_hidden()
    finally:page.context.set_offline(False)
    page.route('**/v1/audio/events',response)
    page.locator('#submit').click();expect(page.locator('#save')).to_be_visible()
    page.evaluate("""() => { window.originalSetItem=Storage.prototype.setItem;
        Storage.prototype.setItem=function(){throw new DOMException('test quota','QuotaExceededError')}; }""")
    page.locator('#save').click()
    expect(page.locator('#status')).to_contain_text('브라우저 저장에 실패했습니다')
    expect(page.locator('#count')).to_contain_text('0개');expect(page.locator('#save')).to_be_visible()
    page.evaluate('() => { Storage.prototype.setItem=window.originalSetItem; delete window.originalSetItem; }')
    page.locator('#save').click();expect(page.locator('#count')).to_contain_text('1개')
    page.once('dialog',lambda dialog:dialog.accept());page.locator('#clear').click()
    expect(page.locator('#count')).to_contain_text('0개')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real-ast',action='store_true');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output and args.output.exists():raise FileExistsError('Use a fresh evidence path')
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/'notes.sqlite3';_,session=Store(db).issue()
        data=io.BytesIO()
        with wave.open(data,'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100);w.writeframes(b'\0\0'*44100)
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        real=args.real_ast
        env={**os.environ,'PETSENSE_ACCOUNT_DB':str(db),'PETSENSE_ENABLE_AST':'true' if real else 'false','PETSENSE_API_TOKEN':'test-only','PETSENSE_REQUIRE_ACCOUNT':'true' if real else 'false'}
        server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            base=f'http://127.0.0.1:{port}'
            for _ in range(100):
                try:
                    with urllib.request.urlopen(base+'/healthz',timeout=.2):break
                except OSError:time.sleep(.1)
            else:raise RuntimeError('Server did not become ready')
            with sync_playwright() as pw:
                browser=pw.chromium.launch()
                try:
                    page=browser.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                    converted=[]
                    def response(route):
                        with wave.open(io.BytesIO(route.request.post_data_buffer),'rb') as w:
                            assert (w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())==(16000,1,2,16000)
                        converted.append(True)
                        route.fulfill(status=200,content_type='application/json',body=json.dumps({'decision':'abstain','model':'mock-browser-smoke','dog_event_scores':[{'label':'Bark','score':.7}]}))
                    if not real:page.route('**/v1/audio/events',response)
                    page.goto(base+'/app');page.locator('#pet').fill('테스트개');page.locator('#context').fill('합성 입력·브라우저 검사')
                    page.locator('#audio').set_input_files({'name':'test.wav','mimeType':'audio/wav','buffer':data.getvalue()})
                    page.locator('summary').click();page.locator('#token').fill('test-only');page.locator('#consent').check()
                    if real:
                        page.locator('#auth-mode').select_option('account');page.locator('#notes-session').fill(session)
                    started=time.monotonic()
                    with page.expect_response('**/v1/audio/events',timeout=90000) as observed:page.locator('#submit').click()
                    seconds=time.monotonic()-started
                    payload=observed.value.json()
                    assert payload['decision']=='abstain'
                    if real:
                        from training.pretrained_audio import MODEL,REVISION
                        assert payload['model']==MODEL and payload['revision']==REVISION and payload['production_ready'] is False
                        assert len(payload['dog_event_scores'])==7
                    expect(page.locator('#save')).to_be_visible();page.locator('#save').click();expect(page.locator('#count')).to_contain_text('1개')
                    page.reload();expect(page.locator('#count')).to_contain_text('1개')
                    page.locator('#pet').fill('테스트개');page.locator('#context').fill('상황 메모');page.locator('#notes-session').fill(session);page.locator('#notes-consent').check();page.locator('#notes-save').click()
                    expect(page.locator('#notes-list .record')).to_have_count(1)
                    page.once('dialog',lambda dialog:dialog.accept());page.locator('#notes-delete-account').click();expect(page.locator('#notes-status')).to_contain_text('삭제했습니다')
                    expect(page.locator('#count')).to_contain_text('1개')
                    page.once('dialog',lambda dialog:dialog.accept());page.locator('#clear').click();expect(page.locator('#count')).to_contain_text('0개')
                    if not real:failure_recovery(page,data.getvalue(),response)
                    assert (real or converted) and not errors,errors
                    if args.output:
                        args.output.parent.mkdir(parents=True,exist_ok=True)
                        evidence={'synthetic_input':True,'physical_device':False,'real_ast':real,
                            'browser_to_api_seconds':seconds,'http_status':observed.value.status,
                            'model':payload.get('model'),'revision':payload.get('revision'),
                            'input_sha256':payload.get('input_sha256'),'decision':payload['decision'],
                            'account_notes_and_local_history_deleted':True,
                            'controlled_browser_failures_tested':not real,
                            'scope':'Single synthetic Chromium run; not latency benchmark or dog behavior accuracy.'}
                        with args.output.open('x') as out:json.dump(evidence,out,indent=2)
                    print('Chromium smoke passed: Web Audio, HTTP scoring, history and account deletion; AST '+('real pinned weights in isolated process' if real else 'mocked')+'.')
                    if not real:print('Controlled browser failures passed: 429, 503, offline connection, storage quota and manual recovery.')
                finally:browser.close()
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait()

if __name__=='__main__':main()
