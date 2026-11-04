"""Acquire corrected CC-BY play-pant source version, never raw43GB recording ZIP."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import time
import urllib.request

RECORD=23806945
NAMES=['07 Readme.txt','05 Metadata.csv','04 Annotations.zip','03 Play session recordings.zip']

def fetch_file(entry,target):
    size=entry['size'];url=entry['links']['self']
    if not 0<size<=400_000_000 or not url.startswith(f'https://zenodo.org/api/records/{RECORD}/files/'):raise ValueError('Expected bounded version-pinned source')
    deadline=time.monotonic()+600;md5=hashlib.md5();sha=hashlib.sha256();partial=target.with_suffix(target.suffix+'.partial')
    if size<1_000_000:
        with urllib.request.urlopen(url,timeout=30) as r:data=r.read(size+1)
        if len(data)!=size:raise ValueError('Truncated source')
        partial.write_bytes(data);md5.update(data);sha.update(data)
    else:
        chunk=8*1024*1024
        with tempfile.TemporaryDirectory(dir=target.parent) as directory:
            parts=Path(directory)
            def piece(index):
                if time.monotonic()>deadline:raise TimeoutError('Download deadline exceeded')
                start=index*chunk;end=min(start+chunk,size)-1
                request=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'})
                with urllib.request.urlopen(request,timeout=60) as r:
                    if r.status!=206 or r.headers.get('Content-Range')!=f'bytes {start}-{end}/{size}':raise ValueError('Exact HTTP206 source required')
                    data=r.read(end-start+2)
                if len(data)!=end-start+1:raise ValueError('Truncated range')
                (parts/f'{index:04d}').write_bytes(data)
            with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(piece,range((size+chunk-1)//chunk)))
            with partial.open('xb') as stream:
                for path in sorted(parts.iterdir()):
                    data=path.read_bytes();stream.write(data);md5.update(data);sha.update(data)
    if partial.stat().st_size!=size or 'md5:'+md5.hexdigest()!=entry['checksum']:raise ValueError('Complete original checksum mismatch')
    partial.rename(target);return {'path':target.name,'bytes':size,'sha256':sha.hexdigest(),'publisher_checksum':entry['checksum']}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    with urllib.request.urlopen(f'https://zenodo.org/api/records/{RECORD}',timeout=30) as r:raw=r.read(4_000_001)
    if len(raw)>4_000_000:raise ValueError('Metadata too large')
    metadata=json.loads(raw)
    if metadata.get('id')!=RECORD or metadata['metadata'].get('license',{}).get('id')!='cc-by-4.0':raise ValueError('Corrected CC-BY metadata required')
    (a.output/'record.json').write_bytes(raw);files={f['key']:f for f in metadata['files']};receipts=[]
    names=NAMES+(['01 Samples of play sessions.zip'] if a.samples else [])
    for name in names:
        receipts.append(fetch_file(files[name],a.output/name))
        if name=='07 Readme.txt':
            text=(a.output/name).read_text()
            if 'CC BY 4.0' not in text or 'noncommercial' in ''.join(c for c in text.lower() if c.isalpha()):raise ValueError('README license conflict')
    (a.output/'acquisition-receipt.json').write_text(json.dumps({'record':RECORD,'source_metadata_sha256':hashlib.sha256(raw).hexdigest(),'files':receipts,'training_performed':False},indent=2)+'\n')
    print(json.dumps({'files':len(receipts),'bytes':sum(r['bytes'] for r in receipts),'training_performed':False}))
if __name__=='__main__':main()
