"""Offline cached BarkMeow/ESC duplicate triage; never grants training approval."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np

RATE=16000
WINDOW=16000
HOP=4000
SPECTRAL_THRESHOLD=.97
WAVE_THRESHOLD=.90


def sha(b): return hashlib.sha256(b).hexdigest()


def decode(path,expected):
    path=Path(path)
    if not path.is_file() or not 0<path.stat().st_size<=20_000_000: raise ValueError('Invalid source size')
    data=path.read_bytes()
    if sha(data)!=expected: raise ValueError('Source hash mismatch')
    with tempfile.TemporaryDirectory(prefix='petsense-duplicate-') as d:
        source=Path(d)/'source.wav';source.write_bytes(data)
        result=subprocess.run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file',
            '-format_whitelist','wav','-threads','1','-i',str(source),'-map','0:a:0',
            '-t','120.01','-ac','1','-ar',str(RATE),'-f','s16le','pipe:1'],
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True,timeout=20)
    raw=result.stdout
    if not 3200<=len(raw)<=RATE*120*2 or len(raw)%2: raise ValueError('Unsupported audio duration')
    return {'raw_sha256':expected,'canonical_sha256':sha(raw),'signal':np.frombuffer(raw,dtype='<i2').astype(np.float64)/32768}


def windows(signal):
    descriptors=[];starts=[]
    for start in range(0,len(signal)-WINDOW+1,HOP):
        x=signal[start:start+WINDOW]
        if np.sqrt(np.mean(x*x))<1e-5: continue
        frames=np.lib.stride_tricks.sliding_window_view(x,512)[::256]
        power=np.abs(np.fft.rfft(frames*np.hanning(512),axis=1))**2
        bands=np.stack([np.log(np.maximum(b.mean(axis=1),1e-10)) for b in np.array_split(power[:,1:],16,axis=1)],axis=1)
        # Remove fixed band energy: offsets/gain do not define duplicate content.
        bands-=bands.mean(axis=0)
        v=bands.reshape(-1);norm=np.linalg.norm(v)
        if norm<1e-8: continue
        descriptors.append(v/norm);starts.append(start)
    return np.asarray(descriptors),starts


def compare(rows):
    if not 1<=len(rows)<=500 or len({r['id'] for r in rows})!=len(rows): raise ValueError('Bounded unique source list required')
    descriptors=[windows(r['signal']) for r in rows]
    raw_equal=[];canonical_equal=[];candidates=[];compared=0
    for i,a in enumerate(rows):
        for j in range(i+1,len(rows)):
            b=rows[j]
            if 'barkmeow' not in (a['dataset'],b['dataset']): continue
            compared+=1;ids=[a['id'],b['id']]
            if a['raw_sha256']==b['raw_sha256']:raw_equal.append(ids)
            if a['canonical_sha256']==b['canonical_sha256']:canonical_equal.append(ids)
            av,at=descriptors[i];bv,bt=descriptors[j]
            if not len(at) or not len(bt):continue
            scores=av@bv.T
            # At most 8 strongest aligned windows per pair; report one best candidate.
            flat=np.flatnonzero(scores.ravel()>=SPECTRAL_THRESHOLD)
            selected=flat[np.argsort(scores.ravel()[flat],kind='stable')[-8:]]
            best=None
            for index in selected:
                ai,bi=np.unravel_index(index,scores.shape)
                x=a['signal'][at[ai]:at[ai]+WINDOW];y=b['signal'][bt[bi]:bt[bi]+WINDOW]
                x=x-x.mean();y=y-y.mean();den=np.linalg.norm(x)*np.linalg.norm(y)
                correlation=abs(float(x@y/den)) if den>1e-12 else 0.
                if correlation>=WAVE_THRESHOLD:
                    item={'ids':ids,'seconds':[at[ai]/RATE,bt[bi]/RATE],'window_seconds':1,
                          'spectral_cosine':float(scores[ai,bi]),'absolute_waveform_correlation':correlation,
                          'review_status':'pending','same_animal_verified':False,'training_approved':False}
                    if best is None or correlation>best['absolute_waveform_correlation']:best=item
            if best:candidates.append(best)
    return {'compared_file_pairs':compared,'raw_equal_pairs':raw_equal,'canonical_equal_pairs':canonical_equal,
            'similarity_candidates':candidates,'independence_proven':False,'training_approved':False,
            'method':{'sample_rate':RATE,'pcm':'mono signed16','window_seconds':1,'hop_seconds':.25,
                      'spectral_threshold':SPECTRAL_THRESHOLD,'absolute_waveform_threshold':WAVE_THRESHOLD,
                      'top_window_pairs_checked_per_file_pair':8},
            'limitations':['Candidate similarity is not verified shared provenance or animal identity',
                          'Grid alignment can miss arbitrary trims, time stretch, pitch shift, compression and mixing',
                          'Segments shorter than 1 second and near-silence do not enter similarity search',
                          'No match is not evidence of independent animals, households or recordings',
                          'Unknown pretrained corpora not inspected; no independence or accuracy claim']}


def contained(root,relative):
    if not isinstance(relative,str) or Path(relative).is_absolute() or '..' in Path(relative).parts or '\\' in relative or ':' in relative:
        raise ValueError('Relative local source required')
    p=(root/relative).resolve(strict=True)
    if not p.is_relative_to(root):raise ValueError('Escaping source')
    return p


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--barkmeow',required=True,type=Path);p.add_argument('--esc10',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    if args.output.exists():raise ValueError('New output required')
    inventories={};rows=[]
    for dataset,root,key,subdir,expected in [('barkmeow',args.barkmeow,'dog_recordings','dog-audio',46),('esc10',args.esc10,'files','',400)]:
        root=root.resolve(strict=True);path=root/'inventory.json'
        if path.stat().st_size>4_000_000:raise ValueError('Inventory too large')
        content=path.read_bytes();inventory=json.loads(content);files=inventory[key]
        if len(files)!=expected:raise ValueError('Expected complete cached collection')
        inventories[dataset]={'sha256':sha(content),'file_count':len(files),'source_revision':inventory.get('source_revision',inventory.get('revision'))}
        for row in files:
            audio=contained(root,str(Path(subdir)/row['path']))
            item=decode(audio,row['sha256'])
            item.update(id=dataset+':'+row['path'],dataset=dataset,animal_id=None,household_id=None,
                        source_recording_id=row.get('source_recording_id'),source_group=row.get('src_file'),
                        source_url=row.get('source_url'),category=row.get('category',row.get('source_label')))
            rows.append(item)
    result=compare(rows)
    result.update(inventories=inventories,files=[{k:v for k,v in r.items() if k!='signal'} for r in rows],
                  ffmpeg_version=subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0],
                  numpy_version=np.__version__,new_downloads=0,training_performed=False)
    with args.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps({k:(len(result[k]) if isinstance(result[k],list) else result[k]) for k in
                      ['compared_file_pairs','raw_equal_pairs','canonical_equal_pairs','similarity_candidates','training_approved']}))


if __name__=='__main__':main()
