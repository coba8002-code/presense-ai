"""Local AI-Hub59 label audit to a dog-only review queue, never a training manifest."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time


def summarize(root):
    root=Path(root).resolve();rows=[];excluded=0;actions=Counter();total=0;deadline=time.monotonic()+300
    if not root.is_dir():raise ValueError('Label directory required')
    for path in sorted(root.rglob('*.json')):
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('Linked/outside label rejected')
        if len(rows)+excluded>=100000 or path.stat().st_size>20_000_000 or time.monotonic()>deadline:raise ValueError('Label audit bound exceeded')
        raw=path.read_bytes();total+=len(raw)
        if total>2_000_000_000:raise ValueError('Label byte budget exceeded')
        label=json.loads(raw)
        if not isinstance(label,dict):raise ValueError('Expected AI-Hub59 object')
        species=label.get('species')
        if species in ('cat','고양이'):excluded+=1;continue
        if species not in ('dog','개'):raise ValueError('Unknown species; schema mapping requires review')
        action=label.get('action');annotations=label.get('annotations')
        if not isinstance(action,str) or not action.strip() or len(action)>200 or not isinstance(annotations,list) or len(annotations)>100000 or any(not isinstance(a,dict) for a in annotations):raise ValueError('Unexpected AI-Hub59 annotation schema')
        actions[action]+=1;digest=hashlib.sha256(raw).hexdigest()
        rows.append({'source_label_sha256':digest,'relative_label':str(path.relative_to(root)),'publisher_action':action,'annotation_frames':len(annotations),'frames_with_keypoint_object':sum(isinstance(a.get('keypoints'),dict) for a in annotations),'frames_with_timestamp':sum('timestamp' in a for a in annotations),'timestamp_unit':'unverified','animal_id':None,'household_id':None,'reviewer':None,'training_approved':False})
    return {'dataset':'aihub-59','dog_labels':len(rows),'cat_labels_excluded':excluded,'publisher_action_counts':dict(actions),'review_queue':rows,'training_performed':False,'limitations':['File/seq is not animal identity','Owner/inspect emotion is not exported or used as truth','No timestamp-unit, video pairing, media availability, rights or pose-coordinate validation','71878 has a different schema; do not use this adapter for it']}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=summarize(a.input)
    with Path(a.output).open('x') as f:json.dump(r,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:r[k] for k in ['dog_labels','cat_labels_excluded','training_performed']}))
if __name__=='__main__':main()
