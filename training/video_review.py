"""Export current VLM observations for human review; validate annotation splits.

This does not fetch media, run training, or treat machine output as ground truth.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Literal
from pydantic import Field, field_validator
from knowledge.models import Analysis, StrictModel
from knowledge.pipeline import policy_for
from knowledge.providers import canonical
from knowledge.worker import load_config
from training.data import approve_dataset

LABELS = ('walking','running','sitting','standing','lying','grooming','eating','drinking','approaching','retreating')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def proposals(db, config, now=None):
    now=time.time() if now is None else now
    result=[]
    for row in db.execute('SELECT * FROM videos WHERE analysis IS NOT NULL ORDER BY id LIMIT 500'):
        if (row['model'] != config.gemini_model or now-row['verified'] >= 86400
                or row['analyzed'] is None or now-row['analyzed'] >= config.retention_days*86400
                or not policy_for(config,row['channel_id'],now,'knowledge_allowed')):
            continue
        analysis=Analysis.model_validate_json(row['analysis'])
        if analysis.species != 'dog':
            continue
        for index,entry in enumerate(analysis.entries):
            if entry.kind != 'observation' or entry.end_seconds <= entry.start_seconds or entry.end_seconds > row['duration']:
                continue
            evidence=dict(source_id=row['id'],channel_id=row['channel_id'],species=analysis.species,
                model=row['model'],analyzed_at=row['analyzed'],analysis_sha256=digest(analysis.model_dump()),
                entry_index=index,observation=entry.model_dump())
            result.append(dict(**evidence,proposal_id=digest(evidence),
                citation=canonical(row['id'])+f'&t={entry.start_seconds}s',
                suggested_label=None,training_ready=False,review_status='pending'))
    return result


class Review(StrictModel):
    proposal_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    decision: Literal['approved']
    label: Literal['walking','running','sitting','standing','lying','grooming','eating','drinking','approaching','retreating']
    animal_id: str = Field(min_length=1,max_length=160)
    recording_group: str = Field(min_length=1,max_length=160)
    dataset: str = Field(min_length=1,max_length=160)
    split: Literal['train','validation','test']
    reviewer: str = Field(min_length=1,max_length=160)
    review_evidence: str = Field(min_length=1,max_length=1200)
    reviewed_at: int = Field(gt=0)

    @field_validator('animal_id','recording_group','dataset','reviewer','review_evidence')
    @classmethod
    def known(cls,value):
        if value != value.strip() or value.lower() in ('unknown','none','null','pending') or not value.strip():
            raise ValueError('Explicit identity and review evidence required')
        return value


def validate_reviews(db, config, reviews, registry, now=None):
    now=time.time() if now is None else now
    if not isinstance(reviews,list) or not 1 <= len(reviews) <= 6000:
        raise ValueError('Expected 1–6000 reviewed annotations')
    current={row['proposal_id']:row for row in proposals(db,config,now)}
    records=[]; seen=set(); policies={}
    groups={key:{} for key in ('animal_id','recording_group','source_id')}
    labels={part:set() for part in ('train','validation','test')}
    for raw in reviews:
        review=Review.model_validate(raw)
        item=current.get(review.proposal_id)
        if item is None or review.proposal_id in seen:
            raise ValueError('Duplicate, withdrawn or stale proposal')
        if not item['analyzed_at'] <= review.reviewed_at <= now:
            raise ValueError('Review must follow analysis and cannot be in the future')
        seen.add(review.proposal_id)
        policy=approve_dataset(registry,review.dataset)
        channels=policy.get('video_channels')
        if not isinstance(channels,list) or not all(isinstance(v,str) for v in channels) or item['channel_id'] not in channels:
            raise ValueError('Dataset approval must explicitly cover source channel')
        policies[review.dataset]=policy
        record={**item,**review.model_dump(),'review_status':'approved'}
        for key,assignments in groups.items():
            value=record[key]
            if value in assignments and assignments[value] != review.split:
                raise ValueError('Animal, session or source leaks across partitions')
            assignments[value]=review.split
        labels[review.split].add((item['species'],review.label))
        records.append(record)
    all_labels=set.union(*labels.values())
    if len(groups['animal_id']) < 5 or len(all_labels)<2 or any(value != all_labels for value in labels.values()):
        raise ValueError('Need five animals and all species/labels represented in every partition')
    return dict(schema_version=1,status='annotations_validated_media_pending',training_ready=False,
        counts={part:sum(row['split']==part for row in records) for part in labels},
        records=records,policies=policies,manifest_sha256=digest(records),
        remaining=['authorized local media','media hashes and duplicate detection','decode and temporal alignment','real model evaluation'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',required=True)
    parser.add_argument('--config',required=True)
    parser.add_argument('--reviews')
    parser.add_argument('--registry',default='datasets/registry.json')
    args=parser.parse_args()
    try:
        cfg=load_config(args.config)
        uri=Path(args.db).resolve().as_uri()+'?mode=ro'
        with closing(sqlite3.connect(uri,uri=True)) as db:
            db.row_factory=sqlite3.Row
            if args.reviews:
                path=Path(args.reviews)
                if path.stat().st_size>8_000_000:
                    raise ValueError('Review file too large')
                output=validate_reviews(db,cfg,json.loads(path.read_text()),args.registry)
            else:
                output=proposals(db,cfg)
        print(json.dumps(output,ensure_ascii=False,allow_nan=False))
    except (ValueError,OSError,sqlite3.Error):
        parser.exit(2,'Video review blocked: check current source permissions, review fields and partition isolation.\n')


if __name__=='__main__':
    main()
