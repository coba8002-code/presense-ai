"""Train-only audio augmentation experiment on verified ESC-10 research sources."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from training.esc10_experiment import load,partition,LABELS,local_file
from training.audio import signal_features,FEATURE_VERSION
from training.pretrained_audio import read_wav
from training.model import fit,probabilities
from evaluation.metrics import classification_metrics


def experiment(rows,x,extra):
    x=np.asarray(x,dtype=float);extra=np.asarray(extra,dtype=float);parts=partition(rows);train=parts['train']
    if x.ndim!=2 or len(x)!=len(rows) or not 1<=x.shape[1]<=100 or extra.shape!=(len(train),x.shape[1]) or not np.isfinite(x).all() or not np.isfinite(extra).all():raise ValueError('One train-only augmentation per training row required')
    y=np.array([r['category']=='dog' for r in rows],dtype=int)
    train_x=np.concatenate([x[train],extra]);train_y=np.tile(y[train],2)
    mean=train_x.mean(axis=0);scale=np.maximum(train_x.std(axis=0),1e-8);z=(train_x-mean)/scale
    groups=[np.flatnonzero(train_y==i) for i in (0,1)];size=max(map(len,groups));balanced=np.concatenate([np.resize(g,size) for g in groups]);candidates=[]
    for penalty in (.001,.01,.1):
        w=fit(z[balanced],train_y[balanced],2,penalty)
        validation=classification_metrics(y[parts['validation']],probabilities((x[parts['validation']]-mean)/scale,w),LABELS)
        candidates.append((validation['macro_f1'],penalty,w,validation))
    _,penalty,w,validation=max(candidates,key=lambda r:(r[0],-r[1]))
    test=classification_metrics(y[parts['test']],probabilities((x[parts['test']]-mean)/scale,w),LABELS)
    report={'scope':'Actual ESC-10 sound-event research; gain/background augmentation only in train', 'production_ready':False,'animal_disjoint_verified':False,'household_disjoint_verified':False,'behavior_accuracy_verified':False,'deployment_decision':'blocked','selection':'fixed source folds; validation chooses penalty; test evaluated once per run, but previously examined in earlier research so exploratory','selected_penalty':penalty,'validation':validation,'exploratory_test':test,'partitions':{k:len(v) for k,v in parts.items()},'original_train_clips':len(train),'augmented_train_views':len(extra),'fit_rows_before_balancing':len(train_x),'limitations':['Unknown animal/household identities','Augmented views are not newly acquired animals or recordings','ESC pretraining overlap with foundation models is not resolved','No event onset/offset, emotion, intent or cause labels','No independent service-level validation; no background-noise robustness claim from clean heldout clips']}
    model={'format':'esc10-augmented-research-only-v1','production_ready':False,'feature_version':FEATURE_VERSION,'class_names':LABELS,'mean':mean.tolist(),'scale':scale.tolist(),'weights':w.tolist()}
    return report,model


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Use new output')
    rows,x,provenance=load(a.source,a.prepared);train=partition(rows)['train'];root=a.prepared.resolve();signals={int(i):read_wav(local_file(root,rows[i]['path']))[0] for i in train};background=[i for i in signals if rows[i]['category']!='dog'];extra=[];lineage=[]
    for number,i in enumerate(train):
        i=int(i);signal=signals[i];j=background[number%len(background)];noise=np.resize(signals[j],len(signal));rms=max(float(np.sqrt(np.mean(noise**2))),1e-8);target=float(np.sqrt(np.mean(signal**2)))
        gain=.5 if number%2 else 1.25
        mixed=np.clip(gain*signal+.1*target*noise/rms,-1,1)
        extra.append(signal_features(mixed));lineage.append({'parent_source_sha256':rows[i]['source_sha256'],'background_source_sha256':rows[j]['source_sha256'],'gain':gain,'relative_noise_rms':.1,'operation':'gain + circular background at .1 source RMS; clip [-1,1]'})
    report,model=experiment(rows,x,np.stack(extra));report['provenance']=provenance;report['augmentation_lineage']=lineage
    a.output.mkdir(parents=True)
    for name,data in [('report.json',report),('research-model.json',model)]:
        (a.output/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    (a.output/'attribution.txt').write_bytes((a.source/'LICENSE').read_bytes())
    print(json.dumps({k:report[k] for k in ['original_train_clips','augmented_train_views','selected_penalty','exploratory_test','production_ready']}))
if __name__=='__main__':main()
