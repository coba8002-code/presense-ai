"""Bounded dog-only ZIP acquisition by validated HTTP ranges; review queue only."""
import argparse
from collections import OrderedDict
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import time
import urllib.request
import zipfile
from scripts.research_acquisition import audio_info

URL='https://zenodo.org/api/records/20571465/files/dataset.zip/content'
SIZE=963585822
SOURCE='https://zenodo.org/records/20571465'
ATTRIBUTION='Yunao Zhang, Sichang Li, Chuyang Zhao, You Wu, Shiyao Wang. Multi-Species Animal Vocalization Raw Dataset for CNN-Transformer Dual Branch Recognition. DOI:10.5281/zenodo.20571465. CC BY 4.0. Original WAV bytes unchanged; dog subset selected.'

class RangeReader(io.RawIOBase):
    def __init__(self,url,size,opener=urllib.request.urlopen):
        self.url=url;self.size=size;self.opener=opener;self.pos=0;self.cache=OrderedDict();self.transferred=0;self.deadline=time.monotonic()+300
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        if whence not in (0,1,2):raise ValueError('Invalid seek')
        pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        if not 0<=pos<=self.size:raise ValueError('Out-of-range seek')
        self.pos=pos;return pos
    def read(self,n=-1):
        n=self.size-self.pos if n<0 else min(n,self.size-self.pos)
        if n>20_000_000:raise ValueError('Read bound exceeded')
        data=bytearray()
        while n>0:
            if time.monotonic()>self.deadline:raise TimeoutError('Acquisition deadline exceeded')
            block=self.pos//131072;start=block*131072;end=min(start+131071,self.size-1)
            if block not in self.cache:
                if self.transferred+end-start+1>200_000_000:raise ValueError('Transfer budget exceeded')
                req=urllib.request.Request(self.url,headers={'Range':f'bytes={start}-{end}'})
                with self.opener(req,timeout=30) as response:
                    if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{self.size}':raise ValueError('Server did not honor exact range')
                    b=response.read(end-start+2)
                if len(b)!=end-start+1:raise ValueError('Truncated range')
                self.transferred+=len(b);self.cache[block]=b
                if len(self.cache)>32:self.cache.popitem(last=False)
            self.cache.move_to_end(block)
            offset=self.pos-start;b=self.cache[block][offset:offset+n]
            data.extend(b);n-=len(b);self.pos+=len(b)
        return bytes(data)

def dog_member(name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name:raise ValueError('Unsafe archive path')
    match=re.fullmatch(r'dataset/dog_(bark|growl|grunt)_(train|test)/[^/]+\.wav',name)
    return match[1] if match else None

def acquire(output):
    output=Path(output)
    if output.exists():raise FileExistsError('Use new output directory')
    output.parent.mkdir(parents=True,exist_ok=True)
    remote=RangeReader(URL,SIZE);rows=[];known={}
    for path in [Path('data/verified-expansion-20261101-v3/dog-audio'),Path('data/acquisition-20261028/esc10')]:
        if path.exists():
            for wav in path.rglob('*.wav'):
                digest=hashlib.sha256(wav.read_bytes()).hexdigest();known.setdefault(digest,[]).append(str(wav))
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        stage=Path(directory)/'result';stage.mkdir();seen=set();total=0
        with zipfile.ZipFile(remote) as archive:
            if len(archive.infolist())>10000:raise ValueError('Too many members')
            for info in archive.infolist():
                label=dog_member(info.filename)
                if label is None:continue
                if info.filename in seen or info.flag_bits&1 or info.external_attr>>16&0o170000==0o120000:raise ValueError('Duplicate/encrypted/link member')
                seen.add(info.filename);total+=info.file_size
                if not 44<=info.file_size<=20_000_000 or total>150_000_000:raise ValueError('Expanded size exceeded')
                data=archive.read(info) # ZIP decoder validates member CRC.
                digest=hashlib.sha256(data).hexdigest();name=f'{len(rows):04d}.wav';(stage/name).write_bytes(data)
                try:
                    channels,rate,frames,encoding=audio_info(data);audio={'channels':channels,'sample_rate':rate,'seconds':frames/rate,'encoding':encoding}
                except ValueError:audio={'parse_status':'unsupported_or_invalid; review required'}
                rows.append({'path':name,'archive_member':info.filename,'sha256':digest,'bytes':len(data),'publisher_event_label':label,'publisher_split':info.filename.split('/')[1].rsplit('_',1)[1],
                    'animal_id':None,'household_id':None,'speaker_verified':False,'events':[],'reviewer':None,'training_approved':False,'raw_hash_matches_existing':known.get(digest,[]),**audio})
        if not rows:raise ValueError('No explicit dog WAVs')
        report={'source':SOURCE,'archive_url':URL,'archive_declared_bytes':SIZE,'archive_complete_downloaded':False,'full_archive_checksum_verified':False,'member_crc_verified':True,'license_record':'CC BY 4.0; member source rights still require audit','transferred_bytes':remote.transferred,'recordings':rows,'count':len(rows),'unique_raw_hashes':len({r['sha256'] for r in rows}),'raw_matches_existing':sum(bool(r['raw_hash_matches_existing']) for r in rows),'training_performed':False,'limitations':['Publisher event labels are unreviewed; no emotion or identity truth','Publisher train/test split not adopted','Raw hash novelty does not prove source/animal independence','Resampling/edit and source-rights review pending']}
        (stage/'inventory.json').write_text(json.dumps(report,indent=2)+'\n');(stage/'ATTRIBUTION.txt').write_text(ATTRIBUTION+'\n'+SOURCE+'\nCC BY 4.0 record-level declaration. See original record authors and metadata. Dog WAV subset only. Original file bytes unchanged.\n')
        stage.rename(output)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);args=p.parse_args();r=acquire(args.output)
    print(json.dumps({k:r[k] for k in ['count','unique_raw_hashes','raw_matches_existing','transferred_bytes','training_performed']}))
if __name__=='__main__':main()
