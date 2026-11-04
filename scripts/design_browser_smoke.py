"""Exercise the offline GUI prototype; save six illustrative screens, no signup/AI calls."""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);args=p.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=False)
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        base=f'http://127.0.0.1:{port}'
        for _ in range(100):
            try:
                with urllib.request.urlopen(base+'/healthz',timeout=.2):break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Server unavailable')
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            try:
                page=browser.new_page(viewport={'width':1440,'height':1150});errors=[];calls=[]
                page.on('pageerror',lambda err:errors.append(str(err)))
                page.on('request',lambda req:calls.append(req.url) if '/v1/' in req.url else None)
                page.goto(base+'/design');expect(page.locator('#design-signup')).to_be_disabled()
                expect(page.locator('#design-email')).to_have_attribute('readonly','')
                page.locator('#design-terms').check();expect(page.locator('#design-signup')).to_be_disabled()
                page.locator('#design-privacy').check();page.locator('#design-signup').click()
                expect(page.locator('#screen-profile')).to_be_visible();expect(page.locator('#design-register')).to_be_disabled()
                page.locator('#design-pet-name').fill('보리');page.locator('#design-profile-consent').check();page.locator('#design-register').click()
                expect(page.locator('#screen-home')).to_be_visible()
                page.locator('.steps button[data-screen="request"]').click()
                expect(page.locator('#design-request')).to_be_disabled()
                page.locator('#design-file').click();page.locator('#design-analysis-consent').check()
                expect(page.locator('#design-request')).to_be_disabled()
                page.locator('#design-storage-consent').check();page.locator('#design-context').fill('<img src=x onerror=alert(1)>')
                page.locator('#design-request').click();expect(page.locator('#screen-processing')).to_be_visible()
                page.locator('#design-show-result').click()
                expect(page.locator('#design-result-context')).to_have_text('<img src=x onerror=alert(1)>')
                assert page.locator('#design-result-context img').count()==0
                page.locator('#design-save').click();page.locator('.steps button[data-screen="home"]').click()
                expect(page.locator('#design-count')).to_have_text('1')
                assert page.evaluate('localStorage.length')==0 and not calls and not errors
                page.reload();expect(page.locator('#design-count')).to_have_text('0')
                for width in (390,1440):
                    page.set_viewport_size({'width':width,'height':1150 if width==1440 else 920})
                    for index,name in enumerate(['signup','profile','home','request','processing','result'],1):
                        page.locator('.steps button[data-screen="'+name+'"]').click()
                        expect(page.locator('#screen-'+name)).to_be_visible()
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,name)
                        if width==390:page.locator('.device').screenshot(path=str(args.output_dir/f'{index:02d}-{name}.png'))
                    if width==1440:page.screenshot(path=str(args.output_dir/'desktop-design.png'),full_page=True)
                assert not errors,errors
                print('GUI prototype passed: six responsive screens, explicit demo/consent gates, safe text, ephemeral memory and zero API calls. Screens are illustrative, not production signup/inference.')
            finally:browser.close()
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait()

if __name__=='__main__':main()
