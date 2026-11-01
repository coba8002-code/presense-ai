"""Real synthetic-video browser extraction; no AI/model or external media calls."""
import argparse
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
from training.av_alignment import align

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--real-models',action='store_true',help='Explicitly run cached local AST + SmolVLM; synthetic media only');parser.add_argument('--real-pose',action='store_true',help='Explicit cached dog detector + AP10K animal keypoints');parser.add_argument('--real-audio',action='store_true',help='Explicit cached AST only');args=parser.parse_args()
    with tempfile.TemporaryDirectory() as td:
        clip=Path(td)/'synthetic.webm'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=320x240:rate=10:duration=2','-f','lavfi','-i','sine=frequency=800:sample_rate=48000:duration=2','-c:v','libvpx','-c:a','libopus',str(clip)],check=True)
        if args.real_models or args.real_audio or args.real_pose:
            from training.av_ast import run
            alignment=run(clip,consent=True,vision=args.real_models,pose=args.real_pose)
        else:alignment=align(clip,consent=True)
        report=Path(td)/'alignment.json';report.write_text(json.dumps(alignment))
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
                page.locator('#alignment').set_input_files(str(report))
                expect(page.locator('#alignment-status')).to_contain_text('동일 파일 해시 확인')
                expect(page.locator('#energy')).to_be_visible()
                if args.real_models:
                    expect(page.locator('#local-model-status')).to_contain_text('SmolVLM2')
                    expect(page.locator('#local-model-status')).to_contain_text('확률·확정 이벤트 아님')
                if args.real_pose:
                    expect(page.locator('#local-model-status')).to_contain_text('RTMPose')
                    expect(page.locator('#local-model-status')).to_contain_text('검출 0개는 강아지 없음의 증거가 아닙니다')
                page.locator('#extract').click();expect(page.locator('#summarize')).to_be_enabled()
                assert page.locator('.frame').count()>1
                bad={**alignment,'source_sha256':'0'*64}
                page.locator('#alignment').set_input_files({'name':'wrong.json','mimeType':'application/json','buffer':json.dumps(bad).encode()})
                expect(page.locator('#alignment-status')).to_contain_text('일치하지 않습니다')
                expect(page.locator('#energy')).to_be_hidden()

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
            print(json.dumps({'synthetic_video':True,'frames':6,'mobile_viewport':True,'model_inference':args.real_models or args.real_audio or args.real_pose,'consent_identity_cancel_conflict_decode_failure':True,'outbound_requests':outbound,'passed':True}))
        finally:stop(server)

if __name__=='__main__':main()
