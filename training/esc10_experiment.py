"""Actual ESC-10 acoustic baseline research, explicitly outside production promotion.

Unknown animal/household IDs stay unknown. Fixed source folds support a limited
sound-event experiment, not animal-disjoint service or behavior evaluation.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.acquire_esc10 import REVISION
from training.audio import FEATURE_VERSION,features
from training.model import fit,probabilities
from evaluation.metrics import classification_metrics

LABELS=['background','dog_sound']

def partition(rows):
    parts={name:[] for name in ('train','validation','test')}
    owners={key:{} for key in ('source_group','sha256')}
    for i,row in enumerate(rows):
        fold=str(row['fold'])
        if fold not in ('1','2','3','4','5'):
            raise ValueError('Official source fold required')
        part='train' if fold in ('1','2','3') else 'validation' if fold=='4' else 'test'
        for key,seen in owners.items():
            value=row[key]
            if not isinstance(value,str) or not value.strip():raise ValueError('Source lineage required')
            if value in seen and seen[value]!=part:raise ValueError('Recording/content leakage')
            seen[value]=part
        parts[part].append(i)
    if any({rows[i]['category']=='dog' for i in ids}!={False,True} for ids in parts.values()):
        raise ValueError('Both classes required in every partition')
    return {k:np.array(v,dtype=int) for k,v in parts.items()}

def experiment(rows,x):
    x=np.asarray(x,dtype=np.float64)
    if x.ndim!=2 or len(x)!=len(rows) or not 1<=x.shape[1]<=100 or not np.isfinite(x).all():
        raise ValueError('Bounded finite features required')
    parts=partition(rows);y=np.array([r['category']=='dog' for r in rows],dtype=int)
    train=parts['train'];mean=x[train].mean(axis=0);scale=np.maximum(x[train].std(axis=0),1e-8)
    z=(x-mean)/scale
    # Balance only training examples; no held-out statistics or labels in fitting.
    groups=[train[y[train]==label] for label in (0,1)];size=max(map(len,groups))
    balanced=np.concatenate([np.resize(g,size) for g in groups])
    candidates=[]
    for penalty in (.001,.01,.1):
        w=fit(z[balanced],y[balanced],2,penalty)
        validation=classification_metrics(y[parts['validation']],probabilities(z[parts['validation']],w),LABELS,.7)
        candidates.append((validation['macro_f1'],penalty,w,validation))
    _,penalty,weights,validation=max(candidates,key=lambda item:(item[0],-item[1]))
    test=classification_metrics(y[parts['test']],probabilities(z[parts['test']],weights),LABELS,.7)
    majority=int(np.bincount(y[train],minlength=2).argmax())
    baseline=np.zeros((len(parts['test']),2));baseline[:,majority]=1
    cm=np.array(test['confusion_matrix']);tp,fp,fn=int(cm[1,1]),int(cm[0,1]),int(cm[1,0])
    event_metrics={'dog_precision':tp/(tp+fp) if tp+fp else 0.,'dog_recall':tp/(tp+fn),
                   'background_false_positive_rate':fp/int(cm[0].sum())}
    report={'scope':'ESC-10 dog sound versus background research only','production_ready':False,
        'animal_disjoint_verified':False,'household_disjoint_verified':False,'behavior_accuracy_verified':False,
        'deployment_decision':'blocked','selected_penalty':penalty,'validation':validation,'heldout_test':test,
        'heldout_event_metrics':event_metrics,
        'training_majority_baseline':classification_metrics(y[parts['test']],baseline,LABELS,.7),
        'partitions':{k:{'count':len(ids),'dog_clips':int(y[ids].sum()),
            'source_groups':sorted({rows[i]['source_group'] for i in ids}),
            'content_sha256':sorted({rows[i]['sha256'] for i in ids})} for k,ids in parts.items()},
        'selection':'folds1-3 train; fold4 selects penalty; fold5 evaluated once; fixed argmax/0.7 abstention threshold',
        'limitations':['Animal and household identities unknown; overlap may exist across folds',
            'Only40 dog clips; background collection is narrow and class imbalanced',
            'Dataset category dog is not a validated event-boundary, emotion, intent or causal label',
            'Raw probabilities are uncalibrated; no real-world phone or service accuracy established',
            'Research artifact only; production animal-disjoint quality gate is not waived']}
    model={'format':'esc10-research-only-v1','feature_version':FEATURE_VERSION,
        'class_names':LABELS,'mean':mean.tolist(),'scale':scale.tolist(),'weights':weights.tolist(),
        'production_ready':False,'selected_penalty':penalty}
    return report,model

def bounded_json(path):
    if path.stat().st_size>4_000_000:raise ValueError('Bounded local metadata required')
    return json.loads(path.read_text())

def local_file(root,name):
    if not isinstance(name,str) or ':' in name or '\\' in name or Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('Relative local file required')
    path=(root/name).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size>2_000_000:
        raise ValueError('Escaping/oversized file')
    return path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(source,prepared):
    source=source.resolve(strict=True);prepared=prepared.resolve(strict=True)
    inventory=bounded_json(source/'inventory.json');manifest=bounded_json(prepared/'prepared.json')
    if inventory.get('source_revision',inventory.get('revision'))!=REVISION:raise ValueError('Pinned source revision required')
    official={r['filename']:r for r in csv.DictReader((source/'meta/esc50.csv').read_text().splitlines()) if r['esc10']=='True'}
    originals={Path(r['path']).name:r for r in inventory['files']}
    if len(official)!=400 or len(originals)!=400 or len(manifest['files'])!=400:
        raise ValueError('Complete400-file ESC-10 inventory required')
    rows=[];seen=set();x=[]
    for row in manifest['files']:
        name=row['path']
        if name in seen or name not in official or name not in originals:raise ValueError('Duplicate/non-ESC10 clip')
        seen.add(name);entry=official[name];original=originals[name]
        if row['category']!=entry['category'] or str(row['fold'])!=entry['fold'] or row['source_group']!=entry['src_file']:
            raise ValueError('Source label/fold lineage mismatch')
        if any(row.get(k) is not None for k in ('animal_id','household_id')):raise ValueError('Do not fabricate animal identity')
        raw=local_file(source,original['path']);wav=local_file(prepared,name)
        if sha(raw)!=original['sha256'] or row['source_sha256']!=original['sha256'] or sha(wav)!=row['sha256']:
            raise ValueError('Source/preprocessing hash mismatch')
        rows.append(row);x.append(features(wav))
    if sum(r['category']=='dog' for r in rows)!=40:raise ValueError('Expected40 dog clips')
    license_path=source/'LICENSE'
    if not license_path.is_file() or license_path.stat().st_size>500000:raise ValueError('Attribution record required')
    return rows,np.stack(x),{'source_revision':REVISION,'source_url':f'https://github.com/karolpiczak/ESC-50/tree/{REVISION}',
        'license':'ESC-10 subset CC BY; original per-clip attribution retained in attribution.txt',
        'attribution_sha256':sha(license_path),'original_inventory_sha256':sha(source/'inventory.json'),
        'preprocessing_manifest_sha256':sha(prepared/'prepared.json')}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rows,x,provenance=load(a.source,a.prepared);report,model=experiment(rows,x)
    a.output.mkdir(parents=True,exist_ok=False)
    report['provenance']=provenance
    for name,value in [('report.json',report),('research-model.json',model)]:
        (a.output/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    (a.output/'attribution.txt').write_bytes((a.source/'LICENSE').read_bytes())
    print(json.dumps({'clips':len(rows),'dog_clips':40,'heldout':report['heldout_test'],
                      'production_ready':False,'animal_disjoint_verified':False},allow_nan=False))

if __name__=='__main__':main()
