"""Replay AST score files into threshold-free public sound-event metrics."""
import argparse
import json
import math
from pathlib import Path
from training.pretrained_audio import DOG_LABELS,MODEL,REVISION


def ranking_metrics(labels,scores):
    if len(labels)!=len(scores) or not labels or any(type(x) is not int or x not in (0,1) for x in labels):
        raise ValueError('Binary labels and equal nonempty scores required')
    if any(not isinstance(x,(int,float)) or not math.isfinite(x) or not 0<=x<=1 for x in scores):
        raise ValueError('Finite [0,1] scores required')
    positives=sum(labels);negatives=len(labels)-positives
    if not positives or not negatives:raise ValueError('Both classes required')
    ordered=sorted(zip(scores,labels),reverse=True)
    tp=fp=0;ap=auc_pairs=0.;i=0
    while i<len(ordered):
        j=i
        while j<len(ordered) and ordered[j][0]==ordered[i][0]:j+=1
        group=ordered[i:j];p=sum(y for _,y in group);n=len(group)-p
        auc_pairs+=p*(negatives-fp-n)+.5*p*n
        tp+=p;fp+=n;ap+=(p/positives)*(tp/(tp+fp));i=j
    return {'auroc':auc_pairs/(positives*negatives),'average_precision':ap,'positive_clips':positives,'negative_clips':negatives}


def report(folder):
    rows=[];seen=set();hashes=set()
    for path in sorted(Path(folder).glob('[0-9][0-9][0-9][0-9].json')):
        data=json.loads(path.read_text());sample,result=data['sample'],data['result']
        if sample['path'] in seen or sample['sha256'] in hashes:raise ValueError('Duplicate sample path or bytes')
        seen.add(sample['path']);hashes.add(sample['sha256'])
        if result.get('model')!=MODEL or result.get('revision')!=REVISION or result.get('decision')!='abstain' or result.get('input_sha256')!=sample['sha256']:
            raise ValueError('Unexpected model, decision or input provenance')
        events=result['dog_event_scores']
        if len(events)!=7 or {x['label'] for x in events}!=set(DOG_LABELS):raise ValueError('Expected seven original dog labels')
        scores=[x['score'] for x in events]
        if any(not isinstance(x,(int,float)) or not math.isfinite(x) or not 0<=x<=1 for x in scores):raise ValueError('Invalid event score')
        rows.append({'path':sample['path'],'category':sample['category'],'fold':sample['fold'],'source_group':sample['source_group'],'dog_score':max(scores),'sha256':sample['sha256']})
    if len(rows)!=400 or sum(x['category']=='dog' for x in rows)!=40:raise ValueError('Expected complete 400-clip ESC-10 replay')
    metrics=ranking_metrics([int(x['category']=='dog') for x in rows],[x['dog_score'] for x in rows])
    return {'task':'ESC-10 dog versus nine other sound categories','model':MODEL,'revision':REVISION,'score':'max of seven original dog-event sigmoid scores',
        'metrics':metrics,'clips':rows,'training_performed':False,'threshold_selected':False,'production_ready':False,
        'limitations':['No emotion, intent or clinical labels','Animal identities unknown; not animal-disjoint evaluation','Public-source overlap with pretraining cannot be excluded','No operating threshold, false-alert/hour or field accuracy established','Not a phone benchmark; audio is 5-second public clips']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    result=report(a.input);out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(result['metrics']))

if __name__=='__main__':main()
