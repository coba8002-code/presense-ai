"""Expert-source play-call research with participant-disjoint splits; no deployment."""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path,PurePosixPath
import re
import subprocess
import tempfile
import wave
import zipfile
import numpy as np
from training.audio import signal_features,FEATURE_VERSION
from training.data import split_records
from training.model import fit,probabilities
from evaluation.metrics import classification_metrics

LABELS=['Growl','Grunt','Pant']
RECORD=23806945

def usable_events(events,duration):
    parsed=[]
    for r in events:
        start,end=float(r['tmin']),float(r['tmax'])
        if not all(math.isfinite(v) for v in (start,end)) or not 0<=start<end<=duration+.02:raise ValueError('Invalid source annotation clock')
        parsed.append({'start':start,'end':min(end,duration),'label':r['text'].strip(),'tier':r['tier']})
    return [r for r in parsed if r['tier']=='calls' and r['label'] in LABELS and .1<=r['end']-r['start']<=10
            and not any(b['start']<r['end'] and b['end']>r['start'] and (b['tier']!='calls' or b['label']!=r['label']) for b in parsed)]

def partition_events(rows):
    parts=split_records(rows,42);seen={}
    for part,values in parts.items():
        for r in values:
            digest=r['pcm_sha256']
            if digest in seen and seen[digest]!=part:raise ValueError('Exact event PCM overlap across participants/splits')
            seen[digest]=part
    return parts

def validate_source(root):
    meta=root/'record.json'
    if meta.stat().st_size>4_000_000:raise ValueError('Metadata bound exceeded')
    record=json.loads(meta.read_text())
    if record['id']!=RECORD or record['metadata'].get('license',{}).get('id')!='cc-by-4.0':raise ValueError('Corrected CC-BY source version required')
    files={r['key']:r for r in record['files']};digests={}
    for name in ['07 Readme.txt','05 Metadata.csv','04 Annotations.zip','03 Play session recordings.zip']:
        path=root/name;f=files[name]
        if path.stat().st_size!=f['size'] or path.stat().st_size>400_000_000:raise ValueError('Source size mismatch')
        md5=hashlib.md5();sha=hashlib.sha256()
        with path.open('rb') as stream:
            while b:=stream.read(1024*1024):md5.update(b);sha.update(b)
        if 'md5:'+md5.hexdigest()!=f['checksum']:raise ValueError('Published checksum mismatch')
        digests[name]=sha.hexdigest()
    readme=(root/'07 Readme.txt').read_text()
    if 'CC BY 4.0' not in readme or 'noncommercial' in re.sub('[^a-z]','',readme.lower()):raise ValueError('License conflict not resolved')
    return record,digests

def extract(root):
    record,digests=validate_source(root)
    sessions=list(csv.DictReader((root/'05 Metadata.csv').read_text().splitlines(),delimiter=';'))
    if len(sessions)!=30 or len({r['ID_dog'] for r in sessions})!=17:raise ValueError('Expected complete published session/participant metadata')
    output=[];vectors=[];source_hashes={};source_owners={};counts=Counter()
    with zipfile.ZipFile(root/'03 Play session recordings.zip') as audio,zipfile.ZipFile(root/'04 Annotations.zip') as annotations,tempfile.TemporaryDirectory() as temporary:
        audio_index={}
        for item in audio.infolist():
            p=PurePosixPath(item.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in item.filename:raise ValueError('Unsafe archive member')
            if item.filename.startswith('__MACOSX/') or not item.filename.lower().endswith('.wav'):continue
            if p.name in audio_index or item.file_size>200_000_000 or item.external_attr>>16&0o170000==0o120000:raise ValueError('Unsafe audio archive entry')
            audio_index[p.name]=item
        if len(audio_index)!=30 or sum(i.file_size for i in audio_index.values())>2_000_000_000:raise ValueError('Complete bounded session audio required')
        for s in sessions:
            name=s['Audio_file'];participant=s['ID_dog'];match=re.fullmatch(r'P-(\d{2})-[SG]-P_\d\.wav',name)
            if not match or match[1]!=participant or name not in audio_index:raise ValueError('Participant/session mismatch')
            raw=audio.read(audio_index[name]);digest=hashlib.sha256(raw).hexdigest()
            if digest in source_owners and source_owners[digest]!=participant:raise ValueError('Same original audio assigned to different dogs')
            source_owners[digest]=participant;source_hashes[name]=digest
            path=Path(temporary)/'session.wav';path.write_bytes(raw)
            decoded=subprocess.run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file','-format_whitelist','wav','-i',str(path),'-t','900.01','-ac','1','-ar','16000','-f','s16le','pipe:1'],check=True,capture_output=True,timeout=30).stdout
            if not 3200<=len(decoded)<=900*16000*2 or len(decoded)%2:raise ValueError('Bounded session PCM required')
            signal=np.frombuffer(decoded,dtype='<i2').astype(np.float64)/32768;duration=len(signal)/16000
            choices=[n for n in annotations.namelist() if '/SecondLayer/' in n and not n.startswith('__MACOSX/') and PurePosixPath(n).name==name[:-4]+'.Table']
            if len(choices)!=1:raise ValueError('Unique expert second-layer annotation required')
            content=annotations.read(choices[0]);events=list(csv.DictReader(io.StringIO(content.decode('utf-8-sig')),delimiter='\t'));counts['source_intervals']+=len(events)
            accepted=usable_events(events,duration);counts['accepted_before_silence_filter']+=len(accepted)
            for index,event in enumerate(accepted):
                start=round(event['start']*16000);end=round(event['end']*16000);x=signal[start:end]
                if len(x)<1600 or np.sqrt(np.mean(x*x))<1e-5:counts['short_or_near_silent']+=1;continue
                pcm=decoded[start*2:end*2];key=f'{name[:-4]}-{index:05d}'
                output.append({'path':key,'animal_id':'play-pant:'+participant,'source_id':'play-pant:'+name,'label':event['label'],'source_audio_sha256':digest,'annotation_sha256':hashlib.sha256(content).hexdigest(),'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'start':event['start'],'end':event['end'],'feature_row':len(vectors)})
                vectors.append(signal_features(x))
    return output,np.stack(vectors),{'record':RECORD,'source':'https://zenodo.org/records/'+str(RECORD),'license':'CC BY4.0 record and corrected README consistent','source_files_sha256':digests,'session_sha256':source_hashes,'counts':dict(counts),'ffmpeg_version':subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0]}

def train(rows,x):
    parts=partition_events(rows);indices={k:np.array([r['feature_row'] for r in v],dtype=int) for k,v in parts.items()};y=np.array([LABELS.index(r['label']) for r in rows]);tr=indices['train']
    mean=x[tr].mean(axis=0);scale=np.maximum(x[tr].std(axis=0),1e-8);z=(x-mean)/scale;groups=[tr[y[tr]==i] for i in range(len(LABELS))];balanced=np.concatenate([np.resize(g,max(map(len,groups))) for g in groups]);candidates=[]
    for penalty in (.001,.01,.1):
        weights=fit(z[balanced],y[balanced],len(LABELS),penalty);val=classification_metrics(y[indices['validation']],probabilities(z[indices['validation']],weights),LABELS)
        candidates.append((val['macro_f1'],penalty,weights,val))
    _,penalty,weights,validation=max(candidates,key=lambda r:(r[0],-r[1]));test=classification_metrics(y[indices['test']],probabilities(z[indices['test']],weights),LABELS)
    majority=int(np.bincount(y[tr],minlength=3).argmax());baseline=np.zeros((len(indices['test']),3));baseline[:,majority]=1
    report={'scope':'Expert-source Growl/Grunt/Pant within dog-human laboratory play; no emotion/intent labels','production_ready':False,'animal_disjoint_verified':True,'identity_scope':'provided participant IDs in this dataset only','household_disjoint_verified':False,'behavior_accuracy_verified':False,'deployment_decision':'blocked','selected_penalty':penalty,'validation':validation,'heldout_test':test,'majority_baseline':classification_metrics(y[indices['test']],baseline,LABELS),'partitions':{k:{'events':len(v),'animals':sorted({r['animal_id'] for r in v}),'class_counts':dict(Counter(r['label'] for r in v))} for k,v in parts.items()},'limitations':['Single laboratory/young-dog play domain; household IDs unavailable','Source expert labels are not independently reannotated by PetSense','Clip classification on known event boundaries; no event detection, attribution, emotion or cause accuracy','Uncalibrated confidence; only three held-out participants expected','No service model promotion or security-advisory clearance']}
    model={'format':'play-pant-research-only-v1','feature_version':FEATURE_VERSION,'class_names':LABELS,'mean':mean.tolist(),'scale':scale.tolist(),'weights':weights.tolist(),'production_ready':False}
    return report,model

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Use new output')
    rows,x,provenance=extract(a.source);report,model=train(rows,x);report['provenance']=provenance;a.output.mkdir(parents=True)
    for name,value in [('report.json',report),('research-model.json',model),('event-lineage.json',rows)]:
        (a.output/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    meta=json.loads((a.source/'record.json').read_text());authors='; '.join(c['name'] for c in meta['metadata']['creators']);(a.output/'ATTRIBUTION.txt').write_text(authors+'\n'+meta['metadata']['title']+'\nhttps://zenodo.org/records/'+str(RECORD)+'\nCC BY4.0. PCM resampled; selected non-overlapping expert-labeled call intervals, normalization and softmax training.\n')
    print(json.dumps({'events':len(rows),'partitions':report['partitions'],'test':report['heldout_test'],'production_ready':False}))
if __name__=='__main__':main()
