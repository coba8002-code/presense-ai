"""Reproducible local QA; synthetic inputs and loopback servers, no paid model calls."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--browser',action='store_true',help='Requires installed Playwright Chromium')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    commands=[('skills',[sys.executable,'scripts/verify_skills.py']),('qa-skills',[sys.executable,'scripts/verify_qa_skills.py']),
              ('python',[sys.executable,'-m','unittest','discover','-s','tests','-v']),
              ('compile',[sys.executable,'-m','compileall','-q','backend','training','evaluation','knowledge','scripts']),
              ('javascript',['node','--test',*[str(p.relative_to(ROOT)) for p in sorted((ROOT/'tests').glob('*.cjs'))]]),
              ('loopback',[sys.executable,'-m','scripts.qa_loopback_load'])]
    if args.browser:
        for module in ['browser_smoke','video_browser_smoke','research_browser_smoke','product_browser_smoke','job_browser_smoke','member_browser_smoke','guide_browser_smoke','design_browser_smoke']:
            command=([sys.executable,'scripts/browser_smoke.py'] if module=='browser_smoke'
                     else [sys.executable,'-m','scripts.'+module])
            if module in ('guide_browser_smoke','design_browser_smoke'):
                command.extend(['--output-dir',str(args.output.resolve()/module)])
            commands.append((module,command))
        commands.extend([('job-mobile',[sys.executable,'-m','scripts.job_browser_smoke','--mobile']),('member-mobile',[sys.executable,'-m','scripts.member_browser_smoke','--mobile'])])
    results=[]
    for name,command in commands:
        started=time.monotonic()
        with (args.output/(name+'.log')).open('w') as log:
            proc=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:code=proc.wait(timeout=300)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                code=124
        row={'check':name,'command':command,'exit_code':code,'seconds':round(time.monotonic()-started,2)}
        results.append(row);print(json.dumps(row),flush=True)
        (args.output/'results.json').write_text(json.dumps({'scope':'local synthetic QA; browser workers mock inference','checks':results},indent=2)+'\n')
    raise SystemExit(1 if any(r['exit_code'] for r in results) else 0)

if __name__=='__main__':main()
