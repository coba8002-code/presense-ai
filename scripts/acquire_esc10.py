"""Fetch only CC BY ESC-10 from a pinned official source; never the NC remainder."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import wave

REVISION='33c8ce9eb2cf0b1c2f8bcf322eb349b6be34dbb6'
BASE=f'https://raw.githubusercontent.com/karolpiczak/ESC-50/{REVISION}/'

def fetch(path,limit):
    with urllib.request.urlopen(BASE+path,timeout=40) as response:
        b=response.read(limit+1)
    if len(b)>limit:raise ValueError('Source exceeds size bound')
    return b

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args()
    root=Path(a.output);root.mkdir(parents=True,exist_ok=False)
    for name in ['README.md','LICENSE','meta/esc50.csv']:
        dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(fetch(name,500000))
    rows=[r for r in csv.DictReader((root/'meta/esc50.csv').read_text().splitlines()) if r['esc10']=='True']
    if len(rows)!=400 or sum(r['category']=='dog' for r in rows)!=40:raise ValueError('Unexpected pinned ESC-10 inventory')
    (root/'audio').mkdir()
    def one(r):
        name=r['filename']
        if Path(name).name!=name or not name.endswith('.wav'):raise ValueError('Invalid source filename')
        b=fetch('audio/'+name,500000)
        with wave.open(io.BytesIO(b)) as w:
            if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())!=(1,2,44100,220500):raise ValueError('Unexpected source audio')
            if len(w.readframes(220500))!=441000:raise ValueError('Truncated audio')
        (root/'audio'/name).write_bytes(b)
        return {**r,'path':'audio/'+name,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'source_url':BASE+'audio/'+name,'animal_id':None}
    with ThreadPoolExecutor(max_workers=6) as pool:files=list(pool.map(one,rows))
    (root/'inventory.json').write_text(json.dumps({'revision':REVISION,'license':'ESC-10 subset CC BY 3.0; per-clip attribution in LICENSE','files':files,'training_ready':False,'limitation':'Original recording identity only; animal identity unknown'},indent=2))
    print('Acquired 400 licensed ESC-10 clips including 40 dog clips; no training performed.')

if __name__=='__main__':main()
