"""Bounded local HTTP reliability probe; not model throughput or production capacity."""
import concurrent.futures
import json
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import time
import urllib.request


def main():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env={**os.environ, 'PETSENSE_ENABLE_WEB_AUTH':'false','PETSENSE_ENABLE_CLOUD':'false',
         'PETSENSE_ENABLE_AST':'false','PETSENSE_ENABLE_AUDIO':'false','PETSENSE_ENABLE_AST_JOBS':'false',
         'PETSENSE_ENABLE_KNOWLEDGE':'false'}
    process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port)],cwd=Path(__file__).resolve().parents[1],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    base=f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(base+'/healthz',timeout=.2):break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Local QA server unavailable')
        def probe(index):
            start=time.monotonic()
            path='/healthz' if index%2==0 else '/app'
            with urllib.request.urlopen(base+path,timeout=5) as response:
                body=response.read(200000)
                assert response.status==200
                if path=='/healthz':assert json.loads(body)=={'status':'ok','model_ready':False}
                else:assert b'<html' in body.lower()
            return (time.monotonic()-start)*1000
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            elapsed=list(pool.map(probe,range(200)))
        elapsed.sort()
        print(json.dumps({'requests':200,'concurrency':4,'successful':len(elapsed),'p50_ms':round(statistics.median(elapsed),3),'p95_ms':round(elapsed[189],3),'max_ms':round(max(elapsed),3),'scope':'loopback health and app HTML only; no inference or production capacity claim'}))
    finally:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()

if __name__=='__main__':main()
