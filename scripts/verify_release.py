"""Re-run offline release checks and save observed results, never assumed test counts."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
CHECKS=[('python',[sys.executable,'-m','unittest','discover','-s','tests','-q']),
        ('guardian-ui',['node','tests/test_product_app.cjs']),
        ('audio',['node','tests/test_mobile_audio.cjs']),
        ('account-ui',['node','tests/test_account_notes.cjs']),
        ('compile',[sys.executable,'-m','compileall','-q','backend','training','evaluation','scripts','local_pc']),
        ('pinned-skills',[sys.executable,'scripts/verify_skills.py'])]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise FileExistsError('Preserve previous evidence; use a new output name')
    logs=out.with_suffix('.logs');logs.mkdir(exist_ok=False);results=[]
    for name,cmd in CHECKS:
        started=time.monotonic()
        try:
            r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=180)
            text=r.stdout+r.stderr;code=r.returncode
        except subprocess.TimeoutExpired as error:
            def decode(value):return value.decode(errors='replace') if isinstance(value,bytes) else value or ''
            text=decode(error.stdout)+decode(error.stderr)+'\nCHECK TIMEOUT';code=124
        matches=re.findall(r'Ran\s+(\d+)\s+tests?\b',text)
        count=int(matches[-1]) if name=='python' and matches else None
        passed=code==0 and (name!='python' or count is not None and count>0)
        (logs/(name+'.txt')).write_text(text)
        results.append({'name':name,'command':cmd,'passed':passed,'exit_code':code,'seconds':time.monotonic()-started,'test_count':count})
        print(name,'passed' if passed else 'FAILED',flush=True)
    sources={}
    for folder in ['backend','training','evaluation','scripts','tests','local_pc']:
        for path in sorted((ROOT/folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix in {'.py','.js','.cjs','.html','.css'}:
                sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    for path in ROOT.glob('requirements*'):
        if path.is_file():sources[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    payload={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'all_passed':all(r['passed'] for r in results),'checks':results,'source_sha256':sources,'scope':'Offline checks. UI and model boundaries are mocked. Not physical-device or real-weight model accuracy evidence.'}
    with out.open('x') as f:json.dump(payload,f,indent=2)
    raise SystemExit(0 if payload['all_passed'] else 1)

if __name__=='__main__':main()
