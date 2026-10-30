"""Public guided-record UI in two languages and screen sizes; no AI or user data."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect
from scripts.job_browser_smoke import stop

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=False)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    env={**os.environ,'PETSENSE_ENABLE_WEB_AUTH':'false'}
    server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(base+'/healthz',timeout=.2):break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Server unavailable')
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            try:
                for language in ['ko','en']:
                    for width in [390,1440]:
                        page=browser.new_page(viewport={'width':width,'height':1000});errors=[];writes=[]
                        page.on('pageerror',lambda error:errors.append(str(error)))
                        page.on('request',lambda req:writes.append(req.method) if req.method not in ('GET','HEAD') else None)
                        page.goto(base+'/understand?lang='+language)
                        expect(page.locator('html')).to_have_attribute('lang',language)
                        page.locator('#behavior').select_option('barking')
                        page.locator('#before').fill('<script>not executable</script>')
                        page.locator('#during').fill('Synthetic observation')
                        page.locator('#case-form button').click()
                        expect(page.locator('#case-card')).to_be_visible()
                        assert page.locator('#case-note script').count()==0
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                        expect(page.locator('#save-case')).to_be_disabled()
                        with page.expect_download() as observed:page.locator('#download').click()
                        download=observed.value
                        report=json.loads(Path(download.path()).read_text())
                        assert report['kind']=='guardian_report' and report['model_analysis'] is False
                        assert '<script>' in report['note']
                        page.screenshot(path=str(args.output_dir/f'{language}-{width}.png'),full_page=True)
                        page.locator('#after').fill('Input changed')
                        expect(page.locator('#case-card')).to_be_hidden()
                        assert not writes and not errors,(writes,errors)
                        page.close()
            finally:browser.close()
        print('Guided-record Chromium passed: Korean/English, 390/1440px, literal input, explicit export, stale-card reset; no AI or server writes in public mode.')
    finally:stop(server)


if __name__=='__main__':main()
