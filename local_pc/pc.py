"""Domestic PC data acquisition and CPU audio baseline tools. No cloud inference."""
import argparse
import csv
import getpass
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while b := f.read(1024 * 1024):
            h.update(b)
    return h.hexdigest()

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)

def doctor(out):
    gpu = {'nvidia_smi_available': False}
    if shutil.which('nvidia-smi'):
        r = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version',
                            '--format=csv,noheader'], capture_output=True, text=True, timeout=20)
        gpu = {'nvidia_smi_available': True, 'query_succeeded': r.returncode == 0,
               'devices': r.stdout.strip().splitlines() if r.returncode == 0 else []}
    save(out, {'os': platform.system(), 'release': platform.release(),
               'python': platform.python_version(), 'cpu_threads': os.cpu_count(),
               'free_disk_gb': round(shutil.disk_usage(ROOT).free / 1e9, 1), 'gpu': gpu,
               'ffmpeg': bool(shutil.which('ffmpeg')), 'aihubshell': bool(shutil.which('aihubshell')),
               'storage_country': 'user reports domestic PC; not geolocated',
               'recommendation': 'CPU AST baseline first; GPU tuning requires measured VRAM and reviewed data'})

def inventory(root, out):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Input directory does not exist')
    rows = []
    for p in sorted(root.rglob('*')):
        if p.is_file() and not p.is_symlink() and p.suffix.lower() in {'.wav','.mp4','.jpg','.jpeg','.png','.json'}:
            rows.append({'path': str(p.relative_to(root)), 'bytes': p.stat().st_size,
                         'sha256': digest(p)})
    save(out, {'files': rows, 'training_approved': False,
               'note': 'Inventory only; species, identity, consent and labels require review.'})

def verify_esc(root):
    root = Path(root).resolve()
    meta = json.loads((root/'inventory.json').read_text(encoding='utf-8'))
    rows = meta['files']
    if len(rows) != 400 or sum(r['category'] == 'dog' for r in rows) != 40:
        raise ValueError('Expected complete acquired ESC-10 subset')
    for r in rows:
        p = (root/r['path']).resolve()
        if not p.is_relative_to(root) or p.is_symlink() or digest(p) != r['sha256']:
            raise ValueError('ESC-10 file path/hash mismatch')
        with wave.open(str(p)) as w:
            if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes()) != (1,2,44100,220500):
                raise ValueError('Unexpected source WAV format')
    return rows

def prepare(root, out):
    rows = verify_esc(root)
    import numpy as np
    from scipy.signal import resample_poly
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    results = []
    for r in rows:
        p = Path(root)/r['path']
        with wave.open(str(p)) as w:
            signal = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64)
        target = np.clip(np.rint(resample_poly(signal,160,441)),-32768,32767).astype('<i2')
        dest = out/p.name
        with wave.open(str(dest),'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(target.tobytes())
        results.append({'path': dest.name, 'source_sha256': r['sha256'], 'sha256': digest(dest),
                        'category': r['category'], 'source_group': r['src_file'], 'fold': r['fold'],
                        'animal_id': None})
    save(out/'prepared.json', {'preprocessing':'scipy resample_poly 160/441; PCM16 mono 16kHz',
         'files': results, 'training_approved':False,
         'limitation':'Source-grouped sound benchmark; animal identities unknown.'})

def score(root, out, limit):
    import time
    sys.path.insert(0,str(ROOT))
    from training.pretrained_audio import ASTDogAudio, read_wav
    root = Path(root).resolve()
    rows = json.loads((root/'prepared.json').read_text(encoding='utf-8'))['files']
    if limit < 0:
        raise ValueError('limit must be zero (all) or positive')
    # Balanced small smoke; no invented classification threshold or accuracy metric.
    if limit:
        positive = [r for r in rows if r['category']=='dog']
        negative = [r for r in rows if r['category']!='dog']
        rows = [x for pair in zip(positive, negative) for x in pair][:limit]
    out = Path(out)
    out.mkdir(parents=True,exist_ok=False)
    model = ASTDogAudio()
    results=[]; start=time.monotonic()
    for r in rows:
        p = (root/r['path']).resolve()
        if not p.is_relative_to(root) or digest(p)!=r['sha256']:
            raise ValueError('Prepared file path/hash mismatch')
        signal,h=read_wav(p)
        result=model.analyze(signal,h)
        results.append({'sample':r,'result':result})
        print(f'Analyzed {len(results)}/{len(rows)}',flush=True)
        save(out/f'{len(results):04}.json', results[-1])
    save(out/'summary.json',{'clips':len(results),'seconds':time.monotonic()-start,
        'dog_accuracy':None,'training_performed':False,'decision':'abstain',
        'note':'Scores only; thresholds and animal-disjoint evaluation not established.'})

def aihub(dataset, filekeys, expected_gb, destination, executable):
    exe = shutil.which(executable)
    if not exe:
        raise ValueError('Install official aihubshell using the linked official guide first')
    dest=Path(destination).resolve();dest.mkdir(parents=True,exist_ok=True)
    cmd=[exe,'-mode','l' if filekeys is None else 'd','-datasetkey',str(dataset)]
    key=''
    if filekeys is not None:
        if not re.fullmatch(r'[0-9]+(,[0-9]+)*',filekeys):
            raise ValueError('Expected reviewed numeric file keys separated by commas')
        if expected_gb is None or not math.isfinite(expected_gb) or expected_gb <= 0:
            raise ValueError('--expected-gb must be the total selected archive size')
        if shutil.disk_usage(dest).free < expected_gb*3*1e9:
            raise ValueError('Need at least 3x selected archive size free space')
        key=getpass.getpass('AI-Hub API key (local input only): ')
        if not key.strip():raise ValueError('API key is empty')
        cmd+=['-filekey',filekeys,'-aihubapikey',key]
    # No shell; redact key from tool output. Official CLI receives key via process argv.
    child=subprocess.Popen(cmd,cwd=dest,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
    for line in child.stdout:
        print(line.replace(key,'[REDACTED]') if key else line,end='',flush=True)
    if child.wait()!=0:raise ValueError('Official AI-Hub CLI failed; check account approval and local network')
    save(dest/('download-receipt.json' if key else 'list-receipt.json'),
         {'dataset':dataset,'filekeys':filekeys,'cli_exit_code':0,'training_approved':False,
          'note':'CLI success only. Run inventory and verify source files/labels before training.'})

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('doctor');a.add_argument('--output',required=True)
    a=sub.add_parser('inventory');a.add_argument('--input',required=True);a.add_argument('--output',required=True)
    a=sub.add_parser('prepare-esc10');a.add_argument('--input',required=True);a.add_argument('--output',required=True)
    a=sub.add_parser('score-esc10');a.add_argument('--input',required=True);a.add_argument('--output',required=True);a.add_argument('--limit',type=int,default=10)
    a=sub.add_parser('aihub');a.add_argument('--dataset',type=int,choices=[59,71878],required=True)
    a.add_argument('--filekeys');a.add_argument('--expected-gb',type=float);a.add_argument('--destination',required=True);a.add_argument('--executable',default='aihubshell')
    args=p.parse_args()
    if args.action=='doctor':doctor(args.output)
    elif args.action=='inventory':inventory(args.input,args.output)
    elif args.action=='prepare-esc10':prepare(args.input,args.output)
    elif args.action=='score-esc10':score(args.input,args.output,args.limit)
    else:aihub(args.dataset,args.filekeys,args.expected_gb,args.destination,args.executable)

if __name__=='__main__':
    try:main()
    except Exception as e:
        print(f'Failed: {e}',file=sys.stderr);sys.exit(1)
