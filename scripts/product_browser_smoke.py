"""Chromium/HTTP/storage smoke; synthetic WAV and mocked AST response, not model accuracy."""
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

def main():
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/'notes.sqlite3';_,session=Store(db).issue()
        data=io.BytesIO()
        with wave.open(data,'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100);w.writeframes(b'\0\0'*44100)
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        env={**os.environ,'PETSENSE_ACCOUNT_DB':str(db),'PETSENSE_ENABLE_AST':'false'}
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
                    page.route('**/v1/audio/events',response)
                    page.goto(base+'/app');page.locator('#pet').fill('테스트개');page.locator('#context').fill('합성 입력·브라우저 검사')
                    page.locator('#audio').set_input_files({'name':'test.wav','mimeType':'audio/wav','buffer':data.getvalue()})
                    page.locator('summary').click();page.locator('#token').fill('test-only');page.locator('#consent').check();page.locator('#submit').click()
                    expect(page.locator('#save')).to_be_visible();page.locator('#save').click();expect(page.locator('#count')).to_contain_text('1개')
                    page.reload();expect(page.locator('#count')).to_contain_text('1개')
                    page.locator('#pet').fill('테스트개');page.locator('#context').fill('상황 메모');page.locator('#notes-session').fill(session);page.locator('#notes-consent').check();page.locator('#notes-save').click()
                    expect(page.locator('#notes-list .record')).to_have_count(1)
                    page.once('dialog',lambda dialog:dialog.accept());page.locator('#notes-delete-account').click();expect(page.locator('#notes-status')).to_contain_text('삭제했습니다')
                    expect(page.locator('#count')).to_contain_text('1개')
                    page.once('dialog',lambda dialog:dialog.accept());page.locator('#clear').click();expect(page.locator('#count')).to_contain_text('0개')
                    assert converted and not errors,errors
                    print('Chromium smoke passed: real Web Audio conversion, browser storage, real note API; AST mocked.')
                finally:browser.close()
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait()

if __name__=='__main__':main()
