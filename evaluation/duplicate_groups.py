"""Convert an existing audio audit into conservative, unapproved review groups."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from training.grouping import Groups, valid_identity


def review_groups(audit):
    files=audit['files']
    if not isinstance(files,list) or not 1<=len(files)<=500:raise ValueError('Bounded audit files required')
    indexed={valid_identity(r['id']):r for r in files}
    if len(indexed)!=len(files):raise ValueError('Duplicate audit identities')
    for row in files:
        if not re.fullmatch('[a-f0-9]{64}',row.get('raw_sha256','')):raise ValueError('Original hash required')
    graph=Groups(indexed)
    pairs=list(audit['raw_equal_pairs'])+list(audit['canonical_equal_pairs'])+[r['ids'] for r in audit['similarity_candidates']]
    if len(pairs)>125000:raise ValueError('Too many edges')
    for pair in pairs:
        if not isinstance(pair,list) or len(pair)!=2 or any(not isinstance(v,str) or v not in indexed for v in pair):
            raise ValueError('Unknown audit edge')
        graph.join(*pair)
    clusters={}
    for key in sorted(indexed):clusters.setdefault(graph.find(key),[]).append(key)
    groups=[];unlinked=[]
    for members in clusters.values():
        if len(members)==1:unlinked.extend(members);continue
        binding=[(key,indexed[key]['raw_sha256']) for key in members]
        group_id='candidate-'+hashlib.sha256(json.dumps(binding,separators=(',',':')).encode()).hexdigest()
        labels=sorted({indexed[key].get('category') for key in members if indexed[key].get('category')})
        groups.append({'duplicate_group':group_id,'members':members,'source_hashes':dict(binding),
                       'publisher_labels':labels,'label_conflict':len(labels)>1,'review_status':'pending',
                       'same_animal_verified':False,'training_approved':False,
                       'disposition':'keep together if later admitted; do not use as an independent holdout'})
    return {'groups':groups,'unlinked_files':unlinked,'training_approved':False,'independence_verified':False,
            'notice':'Candidate edges conservatively link records; not verified shared origin, animal identity or label truth. Unlinked files are not proven independent.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--audit',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    if a.audit.stat().st_size>8_000_000:raise ValueError('Audit too large')
    data=a.audit.read_bytes();result=review_groups(json.loads(data));result['audit_sha256']=hashlib.sha256(data).hexdigest()
    with a.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({'groups':len(result['groups']),'linked_files':sum(len(g['members']) for g in result['groups']),
                      'label_conflict_groups':sum(g['label_conflict'] for g in result['groups']),'training_approved':False}))


if __name__=='__main__':main()
