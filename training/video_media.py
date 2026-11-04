"""Bind reviewed dog annotations to authorized local videos; never download media."""
import argparse
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
from pydantic import Field, field_validator
from knowledge.models import StrictModel
from knowledge.worker import load_config
from training.video_review import validate_reviews, digest, Review

MAX_FILE=128*1024*1024
MAX_TOTAL=512*1024*1024


class Binding(StrictModel):
    source_id: str = Field(pattern=r'^[A-Za-z0-9_-]{11}$')
    path: str = Field(min_length=1,max_length=1024)
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    source_start_seconds: float = Field(ge=0,le=1800,allow_inf_nan=False)
    acquisition_evidence: str = Field(min_length=1,max_length=1200)
    alignment_reviewer: str = Field(min_length=1,max_length=160)
    alignment_evidence: str = Field(min_length=1,max_length=1200)
    alignment_reviewed_at: int = Field(gt=0)

    @field_validator('acquisition_evidence','alignment_reviewer','alignment_evidence')
    @classmethod
    def evidence(cls,value):
        return Review.known(value)


def file_hash(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            value.update(chunk)
    return value.hexdigest()


def inspect_video(path):
    """Bounded local-file demux and full video decode; no URL/playlist protocols."""
    common=['-v','error','-protocol_whitelist','file','-format_whitelist','mov,matroska,webm,avi']
    try:
        probe=subprocess.run(['ffprobe',*common,'-select_streams','v:0','-show_entries',
            'stream=width,height,avg_frame_rate,duration,start_time:format=duration',
            '-of','json',str(path)],capture_output=True,timeout=15,check=True)
        if len(probe.stdout)>64000:
            raise ValueError('Oversized metadata')
        meta=json.loads(probe.stdout);stream=meta['streams'][0]
        duration=float(stream.get('duration',meta.get('format',{}).get('duration','nan')))
        start=float(stream.get('start_time','nan'))
        numerator,denominator=map(int,stream['avg_frame_rate'].split('/'))
        fps=numerator/denominator
        width,height=int(stream['width']),int(stream['height'])
        if (not math.isfinite(duration) or not 0 < duration <= 1800
                or not math.isfinite(start) or abs(start)>.001 or not 0 < fps <= 60
                or not 1<=width<=1920 or not 1<=height<=1080):
            raise ValueError('Unsupported video dimensions, timing or duration')
        # Null output avoids retaining pixels; progress reports the decoded frame count.
        decoded=subprocess.run(['ffmpeg','-nostdin',*common,'-xerror','-threads','1',
            '-i',str(path),'-map','0:v:0','-an','-sn','-dn','-progress','pipe:1',
            '-nostats','-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            timeout=60,check=True)
        frames=[int(line.split('=',1)[1]) for line in decoded.stdout.decode().splitlines() if line.startswith('frame=')]
        if not frames or frames[-1]<1:
            raise ValueError('No video frames decoded')
        return dict(duration_seconds=duration,width=width,height=height,average_fps=fps,decoded_frames=frames[-1])
    except (OSError,subprocess.SubprocessError,ValueError,KeyError,IndexError,TypeError,ZeroDivisionError):
        raise ValueError('Local video decoding or metadata validation failed') from None


def validate_media(db,config,reviews,registry,bindings,root,now=None):
    live_clock=now is None
    now=time.time() if now is None else now
    annotations=validate_reviews(db,config,reviews,registry,now)
    if not isinstance(bindings,list) or not 1<=len(bindings)<=20:
        raise ValueError('Expected 1–20 media bindings')
    items=[Binding.model_validate(row) for row in bindings]
    indexed={row.source_id:row for row in items}
    sources={row['source_id'] for row in annotations['records']}
    if len(indexed)!=len(items) or set(indexed)!=sources:
        raise ValueError('Need exactly one media binding for each reviewed source')
    for policy in annotations['policies'].values():
        if policy.get('media_acquisition_allowed') is not True:
            raise ValueError('Explicit local media acquisition permission required')
    root=Path(root).resolve(strict=True)
    media=[]; hashes=set(); total=0
    with tempfile.TemporaryDirectory(prefix='petsense-video-') as temporary:
        for item in items:
            related=[row for row in annotations['records'] if row['source_id']==item.source_id]
            if not max(row['analyzed_at'] for row in related)<=item.alignment_reviewed_at<=now:
                raise ValueError('Alignment review must follow analysis and not be in the future')
            relative=Path(item.path)
            if relative.is_absolute() or '..' in relative.parts or ':' in item.path or '\\' in item.path:
                raise ValueError('Only relative local media paths are accepted')
            path=(root/relative).resolve(strict=True)
            if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() not in ('.mp4','.mov','.mkv','.avi'):
                raise ValueError('Invalid or escaping media path')
            size=path.stat().st_size;total+=size
            if not 0<size<=MAX_FILE or total>MAX_TOTAL:
                raise ValueError('Media size budget exceeded')
            snapshot=Path(temporary)/(item.source_id+path.suffix.lower())
            with path.open('rb') as source,snapshot.open('wb') as target:
                copied=0
                while chunk:=source.read(1024*1024):
                    copied+=len(chunk)
                    if copied>size:
                        raise ValueError('Media changed during snapshot')
                    target.write(chunk)
            if copied!=size or file_hash(snapshot)!=item.sha256:
                raise ValueError('Media hash mismatch')
            if item.sha256 in hashes:
                raise ValueError('Duplicate media content across source IDs')
            hashes.add(item.sha256)
            metadata=inspect_video(snapshot)
            source_duration=db.execute('SELECT duration FROM videos WHERE id=?',(item.source_id,)).fetchone()['duration']
            if item.source_start_seconds+metadata['duration_seconds']>source_duration+.1:
                raise ValueError('Local media extends beyond source duration')
            for row in related:
                start=row['observation']['start_seconds']-item.source_start_seconds
                end=row['observation']['end_seconds']-item.source_start_seconds
                if not 0<=start<end<=metadata['duration_seconds']:
                    raise ValueError('Reviewed interval falls outside local video')
                row.update(local_start_seconds=start,local_end_seconds=end,media_sha256=item.sha256,
                           media_path=item.path)
            media.append({**item.model_dump(),**metadata})
    # Detect changed permissions, source evidence or files before emitting the receipt.
    current=validate_reviews(db,config,reviews,registry,time.time() if live_clock else now)
    if current['manifest_sha256']!=annotations['manifest_sha256'] or current['policies']!=annotations['policies']:
        raise ValueError('Source or policy changed during validation')
    for item in items:
        path=(root/item.path).resolve(strict=True)
        if not path.is_relative_to(root) or path.stat().st_size>MAX_FILE or file_hash(path)!=item.sha256:
            raise ValueError('Media changed during validation')
    records=annotations['records']
    return dict(schema_version=1,status='media_validated_model_pending',training_ready=False,
        records=records,media=media,counts=annotations['counts'],policies=annotations['policies'],
        manifest_sha256=digest(dict(records=records,media=media,policies=annotations['policies'])),
        remaining=['perceptual duplicate review','video model and preprocessing integration','real model evaluation'],
        notice='Local decode and second-based bounds verified; source identity/alignment are operator attestations. Revalidate before use.')


def read_json(path):
    path=Path(path)
    if path.stat().st_size>8_000_000:
        raise ValueError('JSON file too large')
    return json.loads(path.read_text())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('db','config','reviews','registry','bindings','media-root'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    try:
        with closing(sqlite3.connect(Path(args.db).resolve().as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row
            result=validate_media(db,load_config(args.config),read_json(args.reviews),args.registry,
                read_json(args.bindings),args.media_root)
        print(json.dumps(result,ensure_ascii=False,allow_nan=False))
    except (ValueError,OSError,sqlite3.Error):
        parser.exit(2,'Video media validation blocked: check permissions, bindings, hashes, timing and FFmpeg.\n')


if __name__=='__main__':
    main()
