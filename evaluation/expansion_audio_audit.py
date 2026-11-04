"""Audit cached expansion audio against old originals; never labels or trains."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from evaluation.audio_duplicates import compare,contained,decode
from evaluation.duplicate_groups import review_groups

FOCUS=('zenodo-extra','red-library')

def retain_prior(audit,prior):
    indexed={(r['dataset'],r['raw_sha256']):r['id'] for r in audit['files']}
    mapping={}
    for r in prior['files']:
        key=(r['dataset'],r['raw_sha256'])
        if key not in indexed:raise ValueError('Prior audit source is not hash-bound to current originals')
        mapping[r['id']]=indexed[key]
    for field in ('raw_equal_pairs','canonical_equal_pairs'):
        audit[field].extend([[mapping[v] for v in pair] for pair in prior[field]])
    audit['similarity_candidates'].extend([{**r,'ids':[mapping[v] for v in r['ids']],'retained_from_prior':True} for r in prior['similarity_candidates']])
    audit['retained_prior_candidate_count']=len(prior['similarity_candidates'])
    return audit

def inventory(root):
    root=Path(root).resolve(strict=True);p=root/'inventory.json'
    if p.stat().st_size>4_000_000:raise ValueError('Bounded cached inventory required')
    data=p.read_bytes();return root,json.loads(data),hashlib.sha256(data).hexdigest()

def row(root,relative,entry,dataset,category,media_format='wav',**provenance):
    audio=contained(root,relative);result=decode(audio,entry['sha256'],media_format=media_format)
    result.update(id=dataset+':'+relative,dataset=dataset,category=category,animal_id=None,household_id=None,
                  source_sha256=entry['sha256'],relative_path=relative,**provenance)
    return result

def load_inputs(extra,red,esc,bark):
    roots={};reports={};hashes={}
    for name,path in [('extra',extra),('red',red),('esc',esc),('bark',bark)]:
        roots[name],reports[name],hashes[name]=inventory(path)
    if any(len(reports[k][field])!=n for k,field,n in [('extra','recordings',113),('red','files',31),('esc','files',400),('bark','dog_recordings',46)]):raise ValueError('Expected complete original inventories')
    if reports['red'].get('license')!='CC0 1.0' or reports['red'].get('source')!='https://archive.org/details/Red_Library_Animals_Dogs':raise ValueError('Unexpected source conditions')
    if reports['extra'].get('source')!='https://zenodo.org/records/20571465':raise ValueError('Unexpected expansion source')
    base=[];esc_rows=[]
    for e in reports['bark']['dog_recordings']:
        base.append(row(roots['bark'],'dog-audio/'+e['path'],e,'barkmeow',e['source_label'],source_recording_id=e['source_recording_id'],source_url='https://zenodo.org/records/3563990'))
    known={r['raw_sha256']:r['id'] for r in base};focus=[];omitted=[]
    for e in reports['extra']['recordings']:
        # Verify all113 original hashes, including the46 known raw duplicates.
        audio=contained(roots['extra'],e['path'])
        if audio.stat().st_size>20_000_000 or hashlib.sha256(audio.read_bytes()).hexdigest()!=e['sha256']:raise ValueError('Expansion original changed')
        if e['sha256'] in known:
            omitted.append({'archive_member':e['archive_member'],'sha256':e['sha256'],'same_bytes_as':known[e['sha256']]});continue
        focus.append(row(roots['extra'],e['path'],e,'zenodo-extra',e['publisher_event_label'],source_recording_id=e['archive_member'],source_url=reports['extra']['source']))
    if len(focus)!=67 or len(omitted)!=46:raise ValueError('Raw addition scope changed; re-audit inventory')
    for e in reports['red']['files']:
        focus.append(row(roots['red'],e['path'],e,'red-library',e['publisher_description'],media_format='mp3',source_url=e['source_url'],source_recording_id=e.get('original_wav')))
    for e in reports['esc']['files']:
        esc_rows.append(row(roots['esc'],e['path'],e,'esc10',e['category'],source_url=e.get('source_url'),source_group=e.get('src_file')))
    return focus,esc_rows,base,omitted,hashes

def queue(audit):
    files=audit['files'];indexed={r['id']:r for r in files}
    if not 1<=len(files)<=600 or len(indexed)!=len(files):raise ValueError('Bounded unique audit files required')
    focus={r['id'] for r in files if r['dataset'] in FOCUS}
    edges=audit['raw_equal_pairs']+audit['canonical_equal_pairs']+[r['ids'] for r in audit['similarity_candidates']]
    linked={i for pair in edges for i in pair}
    if not linked<=set(indexed):raise ValueError('Unknown audit edge')
    scoped={**audit,'files':[r for r in files if r['id'] in focus|linked]}
    groups=review_groups(scoped);membership={i:g for g in groups['groups'] for i in g['members']}
    entries=[]
    for key in sorted(focus):
        r=indexed[key];group=membership.get(key)
        entries.append({'recording_id':key,'raw_sha256':r['raw_sha256'],'canonical_sha256':r['canonical_sha256'],
          'source_url':r.get('source_url'),'source_recording_id':r.get('source_recording_id'),'publisher_label':r['category'],
          'reviewed_event_label':None,'events':[],'animal_id':None,'household_id':None,'speaker_verified':False,
          'duplicate_group':group['duplicate_group'] if group else None,'linked_records':group['members'] if group else [],
          'publisher_label_disagreement':group['label_conflict'] if group else False,'reviewer':None,'review_evidence':None,
          'rights_review':'pending member provenance review; record-level licensing only','training_approved':False,
          'disposition':'review linked sources and labels; do not use as independent holdout' if group else 'no candidate does not establish independence'})
    return {'entries':entries,'candidate_groups':groups['groups'],'unlinked_focus_records':sorted(focus-linked),
            'reference_only_unlinked_omitted':len(set(indexed)-focus-linked),'training_performed':False,'training_approved':False,
            'limitations':['Groups bind original hashes; no animal identity or source ownership inferred','Literal publisher-label disagreement may be synonyms, not a proven label error','No new learning or production approval; unknown IDs remain null']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('extra','red','esc','bark'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--prior-audit',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Use new output')
    focus,esc,bark,omitted,hashes=load_inputs(a.extra,a.red,a.esc,a.bark)
    # Keep each batch <=500; never repeat old-old or focus-focus pairs in batch2.
    first=compare(focus+esc,focus_datasets=FOCUS);second=compare(focus+bark,focus_datasets=FOCUS,include_within_focus=False)
    result={**first,'files':[{k:v for k,v in r.items() if k!='signal'} for r in focus+esc+bark],
      'compared_file_pairs':first['compared_file_pairs']+second['compared_file_pairs'],
      'raw_equal_pairs':first['raw_equal_pairs']+second['raw_equal_pairs'],
      'canonical_equal_pairs':first['canonical_equal_pairs']+second['canonical_equal_pairs'],
      'similarity_candidates':first['similarity_candidates']+second['similarity_candidates'],
      'focus_counts':{'zenodo-extra':67,'red-library':31},'reference_counts':{'esc10':400,'barkmeow':46},
      'known_raw_duplicates_excluded_from_recomparison':omitted,'inventory_sha256':hashes,'numpy_version':np.__version__,
      'ffmpeg_version':subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0],
      'scope':'New-new and new-reference pairs only; previous reference-reference audit not repeated',
      'training_performed':False,'new_downloads':0}
    if a.prior_audit.stat().st_size>8_000_000:raise ValueError('Prior audit too large')
    prior_bytes=a.prior_audit.read_bytes();result=retain_prior(result,json.loads(prior_bytes));result['prior_audit_sha256']=hashlib.sha256(prior_bytes).hexdigest()
    reviewed=queue(result);a.output.mkdir(parents=True)
    for name,value in [('audit.json',result),('review-queue.json',reviewed)]:
        (a.output/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'focus_files':98,'reference_files':446,'compared_pairs':result['compared_file_pairs'],
      'raw_pairs':len(result['raw_equal_pairs']),'canonical_pairs':len(result['canonical_equal_pairs']),
      'candidate_pairs':len(result['similarity_candidates']),'review_groups':len(reviewed['candidate_groups']),
      'unlinked_focus':len(reviewed['unlinked_focus_records']),'training_performed':False}))
if __name__=='__main__':main()
