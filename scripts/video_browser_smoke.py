"""Real synthetic-video browser extraction; no AI/model or external media calls."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import httpx
from playwright.sync_api import sync_playwright, expect
from scripts.job_browser_smoke import stop

ROOT=Path(__file__).resolve().parents[1]

def main():
    with tempfile.TemporaryDirectory() as td:
        clip=Path(td)/'synthetic.webm'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=320x240:rate=10:duration=2','-c:v','libvpx','-an',str(clip)],check=True)
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env={**os.environ,'PETSENSE_ENABLE_CLOUD':'false','PETSENSE_ENABLE_LOCAL_VLM':'false'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                try:
                    if httpx.get(base+'/healthz',timeout=.2).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.1)
            with sync_playwright() as p:
                b=p.chromium.launch();page=b.new_page(viewport={'width':390,'height':844})
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                outbound=[]
                page.on('request',lambda r:outbound.append(r.url) if not r.url.startswith((base,'blob:','data:')) else None)
                response=page.goto(base+'/video-review')
                assert "connect-src 'none'" in response.headers['content-security-policy']
                expect(page.locator('#clip')).to_be_disabled()
                page.locator('#consent').check();page.locator('#identity').check()
                page.locator('#clip').set_input_files(str(clip));expect(page.locator('#extract')).to_be_enabled()
                page.locator('#extract').click();expect(page.locator('#summarize')).to_be_enabled()
                assert page.locator('.frame').count()==6
                stamps=[float(t.split(' · ')[1].replace('초','')) for t in page.locator('.frame h3').all_text_contents()]
                assert all(a<b for a,b in zip(stamps,stamps[1:]))
                assert all(0<=t<=2 for t in stamps)
                page.locator('#summarize').click();expect(page.locator('#result')).to_contain_text('판단 유보')
                for i in range(6):
                    for key,value in [('visible','clear'),('posture','crouching'),('ears','back'),('tail','tucked')]:page.locator(f'#{key}-{i}').select_option(value)
                page.locator('#summarize').click();expect(page.locator('#result')).to_contain_text('회피 가능성')
                expect(page.locator('#result')).to_contain_text('AI 추론 없음')
                out=ROOT/'artifacts/video-review-synthetic-20261101.png'
                page.screenshot(path=str(out),full_page=True)
                page.locator('#posture-2').select_option('standing');expect(page.locator('#result')).to_contain_text('관찰 변경됨')
                page.locator('#summarize').click();expect(page.locator('#result')).to_contain_text('판단 유보')
                page.locator('#event-start').fill('0.5');page.locator('#event-end').fill('0.8');page.locator('#event-add').click()
                expect(page.locator('#summarize')).to_be_disabled();assert page.locator('.frame').count()==0
                expect(page.locator('#event-status')).to_contain_text('발성 개체 미확인')
                page.locator('#extract').click();expect(page.locator('#summarize')).to_be_enabled()
                assert page.locator('.frame').count()==4
                stamps=[float(t.split(' · ')[1].replace('초','')) for t in page.locator('.frame h3').all_text_contents()]
                assert stamps==[.1,.5,.65,1.2],stamps
                page.locator('#summarize').click();expect(page.locator('#result')).to_contain_text('보호자 표시 소리 1개')
                page.locator('#event-end').fill('0.2');page.locator('#event-add').click()
                expect(page.locator('#event-status')).to_contain_text('시작·종료')
                page.locator('#events-clear').click();expect(page.locator('#summarize')).to_be_disabled()
                page.locator('#identity').uncheck();assert page.locator('.frame').count()==0;expect(page.locator('#clip')).to_be_disabled()
                page.locator('#identity').check();page.locator('#clip').set_input_files(str(clip));expect(page.locator('#extract')).to_be_enabled()
                page.locator('#extract').click();page.locator('#cancel').click()
                expect(page.locator('#summarize')).to_be_disabled();assert page.locator('.frame').count()==0
                page.locator('#clip').set_input_files({'name':'bad.webm','mimeType':'video/webm','buffer':b'not-video'})
                expect(page.locator('#status')).to_contain_text('확인할 수 없습니다')
                page.locator('#consent').uncheck();assert not page.locator('#video').get_attribute('src')
                assert not outbound,outbound
                assert not errors,errors
                assert page.evaluate('localStorage.length')==0
                b.close()
            print(json.dumps({'synthetic_video':True,'frames':6,'mobile_viewport':True,'model_inference':False,'consent_identity_cancel_conflict_decode_failure':True,'outbound_requests':outbound,'passed':True}))
        finally:stop(server)

if __name__=='__main__':main()
