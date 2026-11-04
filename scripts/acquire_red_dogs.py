"""Acquire bounded CC0 archival dog-effect MP3s for input QA, not emotion truth."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

ITEM='Red_Library_Animals_Dogs'

def entries(metadata):
    m=metadata.get('metadata',{})
    if m.get('identifier')!=ITEM or m.get('licenseurl')!='https://creativecommons.org/publicdomain/zero/1.0/':raise ValueError('Expected fixed CC0 source')
    selected=[f for f in metadata['files'] if f['name'].endswith('.mp3')]
    if not selected or len(selected)>100:raise ValueError('Bounded source list required')
    names=set()
    for f in selected:
        n=f['name']
        if Path(n).name!=n or '\\' in n or n in names or not n.startswith('R') or not 1<=int(f['size'])<=10_000_000 or len(f['md5'])!=32:raise ValueError('Unsafe source entry')
        names.add(n)
    if sum(int(f['size']) for f in selected)>100_000_000:raise ValueError('Source budget exceeded')
    return selected

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--metadata',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.metadata.stat().st_size>4_000_000:raise ValueError('Metadata too large')
    raw=a.metadata.read_bytes();metadata=json.loads(raw);selected=entries(metadata);a.output.mkdir(parents=True,exist_ok=False)
    def acquire(f):
        url='https://archive.org/download/'+ITEM+'/'+urllib.parse.quote(f['name'],safe='')
        with urllib.request.urlopen(url,timeout=45) as r:b=r.read(int(f['size'])+1)
        if len(b)!=int(f['size']) or hashlib.md5(b).hexdigest()!=f['md5'] or hashlib.sha1(b).hexdigest()!=f['sha1']:raise ValueError('Published file checksum mismatch')
        (a.output/f['name']).write_bytes(b)
        return {'path':f['name'],'original_wav':f.get('original'),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'source_url':url,'publisher_description':f['name'],'animal_id':None,'household_id':None,'training_approved':False}
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(acquire,selected))
    report={'source':'https://archive.org/details/'+ITEM,'license':'CC0 1.0','metadata_sha256':hashlib.sha256(raw).hexdigest(),'files':rows,'count':len(rows),'complete':True,'training_performed':False,'scope':'Archival sound effects; pipeline QA only. Descriptive filenames are not verified emotion, breed, age or independent animal labels.'}
    (a.output/'inventory.json').write_text(json.dumps(report,indent=2)+'\n');(a.output/'ATTRIBUTION.txt').write_text('Red Library: Animals Dogs. USC sound effect archive, digitized by Craig Smith. CC0 1.0. '+report['source']+'\nMP3 derivatives; original WAV filename recorded per file.\n');print(json.dumps({'files':len(rows),'bytes':sum(r['bytes'] for r in rows),'training_performed':False}))
if __name__=='__main__':main()
