"""Real Chromium + fake microphone + actual HTTP server integration check."""
import http.client
import json
import math
import os
import re
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import time
import wave

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory() as directory:
        audio = Path(directory) / 'tone.wav'
        with wave.open(str(audio), 'wb') as stream:
            stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            stream.writeframes(b''.join(struct.pack('<h', int(10000 * math.sin(i * 2 * math.pi * 500 / 16000))) for i in range(16000)))
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        env = {**os.environ, 'PETSENSE_ENABLE_AUDIO': 'true', 'PETSENSE_API_TOKEN': 'browser-test-only',
               'PETSENSE_AUDIO_MODEL': '', 'PETSENSE_AUDIO_MODEL_APPROVED': 'false', 'PETSENSE_ENABLE_CLOUD': 'false'}
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app',
                                   '--host', '127.0.0.1', '--port', str(port)], cwd=ROOT, env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=1)
                try:
                    connection.request('GET', '/healthz')
                    response = connection.getresponse()
                    if response.status == 200:
                        assert json.loads(response.read())['status'] == 'ok'
                        break
                except OSError:
                    if server.poll() is not None:
                        raise RuntimeError('HTTP server exited before becoming ready')
                    time.sleep(.1)
                finally:
                    connection.close()
            else:
                raise RuntimeError('HTTP health smoke timed out')
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(args=[
                    '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
                    f'--use-file-for-fake-audio-capture={audio}', '--autoplay-policy=no-user-gesture-required'])
                try:
                    context = browser.new_context(permissions=['microphone'])
                    page = context.new_page()
                    errors, sequences = [], []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('request', lambda request: sequences.append(request.headers['x-audio-sequence'])
                            if request.url.endswith('/v1/audio/chunks') else None)
                    page.add_init_script('''
                      const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                      navigator.mediaDevices.getUserMedia = async constraints => {
                        const stream = await original(constraints);
                        window.testTracks = stream.getTracks(); return stream;
                      };
                    ''')
                    page.goto(f'http://127.0.0.1:{port}/realtime')
                    assert page.locator('#species option').all_text_contents() == ['강아지']
                    page.locator('#start').click()
                    expect(page.locator('#status')).to_contain_text('동의가 필요')
                    assert not sequences
                    page.locator('#token').fill('browser-test-only')
                    page.locator('#consent').check()
                    page.locator('#start').click()
                    expect(page.locator('#status')).to_contain_text('학습 모델 미연결', timeout=20000)
                    expect(page.locator('#metrics')).to_contain_text('서버 처리')
                    assert sequences
                    page.locator('#consent').uncheck()
                    expect(page.locator('#status')).to_contain_text('동의를 해제')
                    assert page.evaluate('window.testTracks.every(track => track.readyState === "ended")')
                    assert page.locator('#token').input_value() == ''
                    sent = len(sequences)
                    page.wait_for_timeout(1200)
                    assert len(sequences) == sent
                    # Slow responses must not create an unbounded audio upload queue.
                    def slow_response(route):
                        time.sleep(2.3)
                        route.fulfill(status=200, content_type='application/json', body=json.dumps({
                            'status': 'model_unavailable', 'prediction': None, 'processing_ms': 1}))
                    page.route('**/v1/audio/chunks', slow_response)
                    page.locator('#token').fill('browser-test-only')
                    page.locator('#consent').check()
                    page.locator('#start').click()
                    expect(page.locator('#metrics')).to_contain_text(re.compile(r'건너뛴 구간 [1-9]'), timeout=15000)
                    page.locator('#stop').click()
                    assert page.evaluate('window.testTracks.every(track => track.readyState === "ended")')
                    assert not errors, errors
                    from review_browser_smoke import run_review_smoke
                    review_page = context.new_page()
                    run_review_smoke(review_page, f'http://127.0.0.1:{port}', directory)
                    print('PASS: HTTP health, Chromium fake microphone, PCM upload/result, consent stop, track release, no console errors')
                finally:
                    browser.close()
        finally:
            server.terminate()
            server.wait(timeout=10)


if __name__ == '__main__':
    main()
