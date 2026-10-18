"""Exercise review UI in real Chromium using a local synthetic video."""
import json
from pathlib import Path
import subprocess
import sys
import time
from playwright.sync_api import expect
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from training.video_review import Review


def run_review_smoke(page,base_url,directory):
    root=Path(directory)
    video=root/'review.webm'
    subprocess.run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i','color=c=blue:s=64x64:r=10:d=5',
        '-c:v','libvpx','-threads','1','-y',str(video)],check=True,timeout=20,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    proposal=dict(proposal_id='a'*64,source_id='abcdefghijk',species='dog',analyzed_at=int(time.time())-5,
        observation=dict(kind='observation',text='<img src=x onerror=alert(1)> Dog sits.',start_seconds=1,
                         end_seconds=3,confidence=.8))
    requests=[];errors=[]
    page.on('request',lambda r:requests.append(r))
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base_url+'/review')
    file=lambda value:dict(name='proposals.json',mimeType='application/json',buffer=json.dumps(value).encode())
    page.locator('#proposals').set_input_files(file([{**proposal,'species':'cat'}]))
    expect(page.locator('#status')).to_contain_text('파일을 열지 못했습니다')
    page.locator('#proposals').set_input_files(file([proposal]))
    expect(page.locator('#count')).to_have_text('후보 1 · 승인 0')
    expect(page.locator('#observation')).to_contain_text('<img')
    assert page.locator('#observation img').count()==0
    expect(page.locator('#approve')).to_be_disabled()
    page.locator('#video-file').set_input_files(str(video))
    expect(page.locator('#play')).to_be_enabled()
    page.locator('#offset').fill('2')
    expect(page.locator('#approve')).to_be_disabled()
    page.locator('#offset').fill('0')
    page.locator('#play').click()
    expect(page.locator('#video-status')).to_have_text('관찰 구간 재생 중')
    expect(page.locator('#video-status')).to_have_text('관찰 구간 재생 완료',timeout=10000)
    expect(page.locator('#video')).to_have_js_property('paused',True)
    page.locator('#label').select_option('sitting')
    for key,value in dict(animal_id='dog-1',recording_group='session-1',dataset='owned',reviewer='expert',review_evidence='review-log-1').items():
        page.locator('#'+key).fill(value)
    page.locator('#confirmed').check();page.locator('#approve').click()
    expect(page.locator('#count')).to_have_text('후보 1 · 승인 1')
    with page.expect_download() as download:
        page.locator('#export').click()
    target=root/'reviews.json';download.value.save_as(target)
    rows=json.loads(target.read_text());assert len(rows)==1
    assert Review.model_validate(rows[0]).label=='sitting'
    page.locator('#animal_id').fill('dog-2')
    page.locator('#export').click()
    expect(page.locator('#status')).to_contain_text('변경사항을 승인')
    page.locator('#approve').click()
    page.locator('#remove').click()
    expect(page.locator('#export')).to_be_disabled()
    assert not [r for r in requests if r.method!='GET']
    assert not [r for r in requests if r.url.startswith('http') and not r.url.startswith(base_url+'/')]
    assert not errors,errors
    print('PASS: review JSON validation, local video playback/offset bounds, literal untrusted text, approval/download schema, edit guard, revoke; no media upload')
