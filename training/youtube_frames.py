"""Reviewed YouTube observations + authorized local originals -> posture frames.

No downloader, provider call or automatic label generation. Prepare exact PNGs,
then revalidate source/rights/media and bind human frame reviews to their hashes.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import struct
import subprocess
import tempfile
import time
from typing import Literal
from pydantic import Field, field_validator
from knowledge.models import StrictModel
from knowledge.worker import load_config
from training.video_media import validate_media, read_json, file_hash, MAX_FILE
from training.video_review import Review, digest
from training.small_vlm import load_manifest


class FrameReview(StrictModel):
    candidate_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    label: Literal['standing','sitting','lying','unknown']
    household_id: str = Field(min_length=1,max_length=160)
    reviewer: str = Field(min_length=1,max_length=160)
    review_evidence: str = Field(min_length=1,max_length=1200)
    reviewed_at: int = Field(gt=0,strict=True)
    frame_inspected: Literal[True]

    @field_validator('frame_inspected', mode='before')
    @classmethod
    def inspected(cls,value):
        if value is not True: raise ValueError('Exact extracted frame inspection required')
        return value

    @field_validator('household_id','reviewer','review_evidence')
    @classmethod
    def known(cls,value): return Review.known(value)


def extract_frame(source, seconds, target):
    subprocess.run(['ffmpeg','-v','error','-nostdin','-protocol_whitelist','file',
        '-format_whitelist','mov,matroska,webm,avi','-threads','1','-i',str(source),
        '-ss',str(seconds),'-map','0:v:0','-frames:v','1','-an','-sn','-dn',
        '-vf','scale=640:640:force_original_aspect_ratio=decrease','-threads','1',
        '-f','image2',str(target)],check=True,timeout=30,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if not target.is_file() or not 0<target.stat().st_size<=8*1024*1024:
        raise ValueError('Missing or oversized frame')
    # These pixels were just encoded by FFmpeg. Keep preparation independent of
    # optional Pillow/Torch packages; the actual trainer decodes with Pillow.
    with target.open('rb') as stream: header=stream.read(33)
    if len(header)!=33 or header[:8]!=b'\x89PNG\r\n\x1a\n' or header[12:16]!=b'IHDR':
        raise ValueError('Invalid generated PNG')
    width,height=struct.unpack('>II',header[16:24])
    if not 1<=width<=640 or not 1<=height<=640: raise ValueError('Generated frame dimensions exceeded')


def export_frames(db,config,reviews,registry,bindings,media_root,output,frame_reviews=None,now=None,config_loader=None):
    clock=lambda: time.time() if now is None else now
    output=Path(output)
    if output.exists(): raise ValueError('New output directory required')
    receipt=validate_media(db,config,reviews,registry,bindings,media_root,clock())
    if len(receipt['records'])>200: raise ValueError('Frame preparation limited to 200 reviewed observations')
    root=Path(media_root).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='petsense-yt-frames-') as temporary:
        stage=Path(temporary)/'result';stage.mkdir();(stage/'frames').mkdir()
        snapshots={}
        for media in receipt['media']:
            source=(root/media['path']).resolve(strict=True)
            if not source.is_relative_to(root): raise ValueError('Escaping source')
            snapshot=Path(temporary)/(media['source_id']+source.suffix)
            with source.open('rb') as src,snapshot.open('xb') as dst:
                size=0
                while chunk:=src.read(1024*1024):
                    size+=len(chunk)
                    if size>MAX_FILE: raise ValueError('Source size exceeded')
                    dst.write(chunk)
            if file_hash(snapshot)!=media['sha256']: raise ValueError('Changed original')
            snapshots[media['source_id']]=snapshot
        candidates=[]
        for n,row in enumerate(receipt['records']):
            seconds=(row['local_start_seconds']+row['local_end_seconds'])/2
            target=stage/'frames'/f'{n:04d}.png'
            extract_frame(snapshots[row['source_id']],seconds,target)
            candidate={key:row[key] for key in ('proposal_id','source_id','channel_id','animal_id',
                'recording_group','dataset','split','citation','media_sha256')}
            candidate.update(path='frames/'+target.name,sha256=file_hash(target),species='dog',
                local_seconds=seconds,source_seconds=(row['observation']['start_seconds']+row['observation']['end_seconds'])/2,
                observation_reviewed_at=row['reviewed_at'],label=None,
                input_receipt_sha256=receipt['manifest_sha256'])
            candidate['candidate_id']=digest(candidate)
            candidates.append(candidate)
        rows=[]
        if frame_reviews is not None:
            if not isinstance(frame_reviews,list) or len(frame_reviews)!=len(candidates):
                raise ValueError('Exactly one frame review per candidate required')
            parsed=[FrameReview.model_validate(r) for r in frame_reviews]
            indexed={r.candidate_id:r for r in parsed}
            if len(indexed)!=len(parsed) or set(indexed)!={r['candidate_id'] for r in candidates}:
                raise ValueError('Duplicate, changed or unreviewed frame')
            homes={}
            for candidate in candidates:
                review=indexed[candidate['candidate_id']]
                if not candidate['observation_reviewed_at']<=review.reviewed_at<=clock():
                    raise ValueError('Frame review must follow observation review and not be in future')
                if review.household_id in homes and homes[review.household_id]!=candidate['split']:
                    raise ValueError('Household leaks across partitions')
                homes[review.household_id]=candidate['split']
                rows.append({**candidate,**review.model_dump(),'reviewed_at':str(review.reviewed_at)})
            (stage/'frames.json').write_text(json.dumps(rows,indent=2))
            load_manifest(stage/'frames.json',registry)
        fresh=validate_media(db,config_loader() if config_loader else config,reviews,registry,bindings,media_root,clock())
        if fresh['manifest_sha256']!=receipt['manifest_sha256']:
            raise ValueError('Source, review or policy changed during extraction')
        result={'schema_version':1,'status':'reviewed_posture_manifest' if rows else 'frame_review_required',
                'manifest_ready':bool(rows),'training_performed':False,'production_ready':False,
                'candidates':candidates,'input_receipt_sha256':receipt['manifest_sha256'],
                'scope':'single-frame dog posture; no audio, temporal action, intent or emotion labels',
                'limitations':['Human rights/alignment/review assertions are not independently verified',
                               'Byte hashes do not detect all near-duplicates',
                               'No source video downloaded; no model called or trained']}
        (stage/'receipt.json').write_text(json.dumps(result,indent=2))
        if frame_reviews is None:
            templates=[{'candidate_id':c['candidate_id'],'label':None,'household_id':None,'reviewer':None,
                        'review_evidence':None,'reviewed_at':None,'frame_inspected':False} for c in candidates]
            (stage/'frame-reviews.template.json').write_text(json.dumps(templates,indent=2))
        output.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(stage,output)  # refuses an existing destination
        return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('db','config','reviews','registry','bindings','media-root','output'):
        p.add_argument('--'+name,required=True)
    p.add_argument('--frame-reviews',help='Completed exact-frame review template; omission only prepares candidates')
    args=p.parse_args()
    try:
        with closing(sqlite3.connect(Path(args.db).resolve().as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row
            result=export_frames(db,load_config(args.config),read_json(args.reviews),args.registry,
                read_json(args.bindings),args.media_root,args.output,
                read_json(args.frame_reviews) if args.frame_reviews else None,
                config_loader=lambda:load_config(args.config))
        print(json.dumps({'status':result['status'],'frames':len(result['candidates']),
                          'manifest_ready':result['manifest_ready'],'training_performed':False}))
    except (ValueError,OSError,sqlite3.Error,subprocess.SubprocessError):
        p.exit(2,'Frame export blocked: check current permissions, media, exact-frame reviews and independent splits.\n')


if __name__=='__main__':main()
