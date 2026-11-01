"""Synthetic Chromium → persistent queue → separate worker → result/delete smoke."""
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
from training.pretrained_audio import MODEL,REVISION

ROOT=Path(__file__).resolve().parents[1]
MOCK_WORKER='''
import asyncio,hashlib,sys
import backend.job_worker as worker
from backend.job_store import JobStore
from training.pretrained_audio import MODEL,REVISION,DOG_LABELS
async def mock(raw,timeout):
 return dict(execution_kind='synthetic_fixture',duration_seconds=1.,model=MODEL,revision=REVISION,input_sha256=hashlib.sha256(raw).hexdigest(),decision='abstain',production_ready=False,species_verified=False,dog_event_scores=[dict(label=x,score=.1) for x in DOG_LABELS],runtime='synthetic-test-double')
worker.run_ast=mock
asyncio.run(worker.serve(JobStore(sys.argv[1]),True))
'''

def stop(proc):
    if proc.poll() is not None:return
    proc.terminate()
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:proc.kill();proc.wait()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--real-ast',action='store_true');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output and args.output.exists():raise FileExistsError('Use fresh output')
    with tempfile.TemporaryDirectory() as td:
        db=Path(td)/'private.sqlite3';store=Store(db);_,token=store.issue();_,other=store.issue();pet=store.pet_create(token,'queue-test')
        env={**os.environ,'PETSENSE_ENABLE_WEB_AUTH':'false','PETSENSE_ACCOUNT_DB':str(db),'PETSENSE_ENABLE_AST_JOBS':'true','PETSENSE_ENABLE_AST':'false'}
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        command=[sys.executable,'-m','backend.job_worker','--db',str(db),'--watch'] if args.real_ast else [sys.executable,'-c',MOCK_WORKER,str(db)]
        worker=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        base=f'http://127.0.0.1:{port}'
        try:
            for _ in range(100):
                try:
                    with urllib.request.urlopen(base+'/healthz',timeout=.2):break
                except OSError:time.sleep(.1)
            else:raise RuntimeError('Server unavailable')
            raw=io.BytesIO()
            with wave.open(raw,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100);w.writeframes(bytes(88200))
            with sync_playwright() as pw:
                browser=pw.chromium.launch()
                try:
                    page=browser.new_page();errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
                    page.goto(base+'/app');page.locator('#notes-session').fill(token);page.locator('#profile-load').click()
                    expect(page.locator('#profile-select option')).to_have_count(2)
                    page.locator('#profile-select').select_option(pet['id'])
                    page.locator('#audio').set_input_files({'name':'synthetic.wav','mimeType':'audio/wav','buffer':raw.getvalue()})
                    page.locator('#consent').check();page.locator('#job-consent').check()
                    started=time.monotonic();page.locator('#job-submit').click()
                    expect(page.locator('#jobs-list strong')).to_contain_text('완료',timeout=90000)
                    seconds=time.monotonic()-started
                    response=page.request.get(base+'/v1/me/audio-jobs',headers={'X-PetSense-Session':token})
                    assert response.status==200
                    job=response.json()['items'][0];result=job['result']
                    assert job['status']=='succeeded' and result['decision']=='abstain'
                    assert len(result['dog_event_scores'])==7
                    if args.real_ast:assert result['model']==MODEL and result['revision']==REVISION
                    page.once('dialog',lambda dialog:dialog.accept());page.locator('#jobs-list button').click()
                    expect(page.locator('#jobs-list strong')).to_contain_text('취소됨')
                    erased=page.request.get(base+'/v1/me/audio-jobs/'+job['id'],headers={'X-PetSense-Session':token}).json()
                    assert erased['result'] is None
                    stop(worker)
                    page.locator('#job-submit').click()
                    expect(page.locator('#jobs-list strong').filter(has_text='대기 중')).to_have_count(1)
                    page.once('dialog',lambda dialog:dialog.accept());page.locator('#jobs-list button').click()
                    expect(page.locator('#jobs-list strong').filter(has_text='취소됨')).to_have_count(2)
                    page.locator('#notes-session').fill(other);expect(page.locator('#jobs-list article')).to_have_count(0)
                    page.locator('#jobs-refresh').click();expect(page.locator('#jobs-status')).to_contain_text('0개')
                    persisted=page.evaluate('JSON.stringify(localStorage)');assert token not in persisted and other not in persisted
                    assert not errors,errors
                    if args.output:
                        args.output.parent.mkdir(parents=True,exist_ok=True)
                        with args.output.open('x') as out:json.dump({'synthetic_input':True,'real_ast':args.real_ast,
                            'model':result.get('model'),'revision':result.get('revision'),'input_sha256':result.get('input_sha256'),
                            'browser_to_queue_result_seconds':seconds,'result_erased':True,'queued_cancelled':True,
                            'account_isolation':True,'physical_device':False,
                            'scope':'Single synthetic Chromium run; not dog behavior accuracy or latency distribution.'},out,indent=2)
                    print('Queue Chromium smoke passed: consent/profile/upload, separate worker, result, completed/queued deletion and owner isolation; AST '+('real pinned weights' if args.real_ast else 'mocked')+'.')
                finally:browser.close()
        finally:stop(worker);stop(server)

if __name__=='__main__':main()
