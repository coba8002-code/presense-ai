"""Score predictions bound to a locked observation contract; no inference/training."""
import argparse
import json
import math
from pathlib import Path
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from evaluation.video_contract import Contract,validate_contract

LABELS=['standing','sitting','lying','walking']
class Prediction(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    clip_id:str=Field(min_length=1,max_length=200)
    sha256:str=Field(pattern=r'^[a-f0-9]{64}$')
    start_seconds:float=Field(ge=0,allow_inf_nan=False)
    end_seconds:float=Field(gt=0,allow_inf_nan=False)
    label:Literal['standing','sitting','lying','walking']|None
    latency_seconds:float|None=Field(default=None,ge=0,allow_inf_nan=False)
class Predictions(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    contract_sha256:str=Field(pattern=r'^[a-f0-9]{64}$')
    synthetic:bool
    split:Literal['validation','test']
    model:str=Field(min_length=1,max_length=200)
    revision:str=Field(min_length=1,max_length=200)
    records:list[Prediction]=Field(max_length=10000)


def score(document,registry,predictions):
    contract_check=validate_contract(document,registry)
    contract=Contract.model_validate(document);run=Predictions.model_validate(predictions)
    if run.contract_sha256!=contract_check['contract_sha256'] or run.synthetic!=contract.synthetic:raise ValueError('Unbound predictions')
    reference={r.clip_id:r for r in contract.records if r.split==run.split}
    if not reference:raise ValueError('Empty selected split')
    found={}
    for p in run.records:
        ref=reference.get(p.clip_id)
        if not ref or p.clip_id in found or (p.sha256,p.start_seconds,p.end_seconds)!=(ref.sha256,ref.start_seconds,ref.end_seconds):raise ValueError('Prediction identity or window mismatch')
        found[p.clip_id]=p
    matrix=[[0]*5 for _ in LABELS];unknown=0;unknown_abstained=0;latencies=[];missing=0
    for key,ref in reference.items():
        prediction=found.get(key);label=prediction.label if prediction else None
        if prediction is None:missing+=1
        if prediction and prediction.latency_seconds is not None:latencies.append(prediction.latency_seconds)
        if ref.label=='unknown':
            unknown+=1;unknown_abstained+=int(label is None)
        else:matrix[LABELS.index(ref.label)][LABELS.index(label) if label else 4]+=1
    support=[sum(row) for row in matrix];known=sum(support);correct=sum(matrix[i][i] for i in range(4));accepted=sum(sum(row[:4]) for row in matrix)
    f1=[]
    for i in range(4):
        denominator=support[i]+sum(matrix[j][i] for j in range(4))
        f1.append(2*matrix[i][i]/denominator if denominator else 0.0)
    latencies.sort()
    percentile=lambda fraction:latencies[max(0,math.ceil(len(latencies)*fraction)-1)] if latencies else None
    return {'schema_version':1,'synthetic':run.synthetic,'real_behavior_accuracy_established':False,'contract_sha256':run.contract_sha256,'policy_sha256':contract_check['policy_sha256'],'split':run.split,'model':run.model,'revision':run.revision,'labels':LABELS,'prediction_columns':LABELS+['abstain_or_missing'],'count':len(reference),'known_count':known,'unknown_count':unknown,'missing_predictions':missing,'class_counts':support,'confusion_matrix':matrix,'accuracy_including_abstention':correct/known if known else None,'macro_f1_fixed_four_labels':sum(f1)/4 if known else None,'per_class_f1':f1,'known_coverage':accepted/known if known else None,'selective_known_accuracy':correct/accepted if accepted else None,'unknown_abstention_rate':unknown_abstained/unknown if unknown else None,'dog_count':len({r.animal_id for r in reference.values()}),'household_count':len({r.household_id for r in reference.values()}),'latency_samples':len(latencies),'latency_missing':len(reference)-len(latencies),'latency_p50_seconds':percentile(.5),'latency_p95_seconds':percentile(.95),'limitations':['Supplied predictions only; no model execution or training','Real media decoding/alignment and independent identity/review evidence not verified here','No probability calibration or animal-cluster confidence intervals','Fixed four-label macro F1 includes zero-support labels as zero; inspect support','Missing predictions are abstentions; latency covers supplied timings only']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','registry','predictions','output'):p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args()
    try:
        if a.output.exists() or a.manifest.stat().st_size>8_000_000 or a.predictions.stat().st_size>8_000_000:raise ValueError('Invalid file size or output')
        result=score(json.loads(a.manifest.read_text()),a.registry,json.loads(a.predictions.read_text()))
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('x') as f:json.dump(result,f,indent=2)
    except (ValueError,OSError):p.exit(2,'Scoring blocked: check reference, rights, split, exact windows, prediction binding and fresh output.\n')
    print('Supplied predictions scored; not evidence of training or verified real-world accuracy.')
if __name__=='__main__':main()
