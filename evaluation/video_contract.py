"""Validate locked, independently reviewed dog-video reference annotations offline."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import time
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from knowledge.models import StrictModel
from training.data import approve_dataset

LABELS = ('standing', 'sitting', 'lying', 'walking', 'unknown')
Label = Literal['standing', 'sitting', 'lying', 'walking', 'unknown']
Identity = Annotated[str, Field(min_length=1, max_length=160)]
Digest = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]


class HumanReview(StrictModel):
    reviewer: Identity
    label: Label
    reviewed_at: int = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=1200)
    model_output_seen: Literal[False]

    @field_validator('model_output_seen', mode='before')
    @classmethod
    def blind(cls, value):
        if value is not False:raise ValueError('Explicit false required for blind human review')
        return value

    @field_validator('reviewer', 'evidence')
    @classmethod
    def explicit(cls, value):
        if value != value.strip() or value.lower() in {'unknown', 'pending', 'none', 'null'}:
            raise ValueError('Explicit human identity and review evidence required')
        return value


class Segment(StrictModel):
    clip_id: Identity
    dataset: Identity
    species: Literal['dog']
    animal_id: Identity
    household_id: Identity
    session_id: Identity
    source_id: Identity
    subject_reference: str = Field(min_length=1, max_length=500)
    path: str = Field(min_length=1, max_length=500)
    sha256: Digest
    split: Literal['train', 'validation', 'test']
    duration_seconds: float = Field(gt=0, le=600, allow_inf_nan=False)
    start_seconds: float = Field(ge=0, allow_inf_nan=False)
    end_seconds: float = Field(gt=0, allow_inf_nan=False)
    label: Label
    unknown_reason: Literal['occluded', 'offscreen', 'ambiguous', 'out_of_scope'] | None = None
    reviews: list[HumanReview] = Field(min_length=1, max_length=2)
    adjudication: str | None = Field(default=None, min_length=1, max_length=1200)

    @field_validator('clip_id', 'dataset', 'animal_id', 'household_id', 'session_id', 'source_id', 'subject_reference')
    @classmethod
    def known(cls, value):
        if value != value.strip() or value.lower() in {'unknown', 'pending', 'none', 'null'}:
            raise ValueError('Known global identities and target dog required')
        return value

    @field_validator('path')
    @classmethod
    def relative_path(cls, value):
        if '\\' in value or ':' in value or value.startswith('/') or '..' in PurePosixPath(value).parts:
            raise ValueError('Relative local media path required')
        return value

    @model_validator(mode='after')
    def temporal_review(self):
        if not .1 <= self.end_seconds - self.start_seconds or self.end_seconds > self.duration_seconds:
            raise ValueError('Reference interval must be within the video and at least 0.1 seconds')
        if (self.label == 'unknown') != (self.unknown_reason is not None):
            raise ValueError('Only unknown references require an unknown reason')
        if len({r.reviewer for r in self.reviews}) != len(self.reviews):
            raise ValueError('Independent reviewers must be different people')
        disagreement = any(r.label != self.label for r in self.reviews)
        if disagreement and (len(self.reviews) != 2 or not self.adjudication or self.adjudication.strip().lower() in {'', 'pending', 'unknown', 'none', 'null'}):
            raise ValueError('Disagreement requires two reviews and documented adjudication')
        return self


class Contract(StrictModel):
    schema_version: Literal[1]
    synthetic: bool
    locked_at: int = Field(gt=0)
    records: list[Segment] = Field(min_length=1, max_length=10000)


def validate_contract(document, registry, media_root=None, now=None):
    """Metadata assertions are not proof of rights, identity or expert credentials."""
    contract = Contract.model_validate(document)
    now = time.time() if now is None else now
    if not math.isfinite(now) or not 0 < contract.locked_at <= now:
        raise ValueError('Reference lock time must not be in the future')
    groups = {key: {} for key in ('animal_id', 'household_id', 'session_id', 'source_id', 'sha256')}
    seen = set(); sources = {}; intervals = {}; policies = {}
    root = Path(media_root).resolve() if media_root is not None else None
    for row in contract.records:
        if row.clip_id in seen:
            raise ValueError('Duplicate clip identity')
        seen.add(row.clip_id)
        if any(r.reviewed_at > contract.locked_at for r in row.reviews):
            raise ValueError('All human reviews must precede the reference lock')
        if row.dataset not in policies:policies[row.dataset] = approve_dataset(registry, row.dataset)
        policy = policies[row.dataset]
        if bool(policy.get('synthetic', False)) != contract.synthetic:
            raise ValueError('Synthetic and real reference provenance cannot be mixed')
        if policy.get('media_acquisition_allowed') is not True:
            raise ValueError('Authorized media acquisition evidence required')
        for key, assignment in groups.items():
            value = getattr(row, key)
            if value in assignment and assignment[value] != row.split:
                raise ValueError('Animal, household, session, source or content leaks across splits')
            assignment[value] = row.split
        source = (row.sha256, row.duration_seconds, row.session_id, row.household_id)
        if row.source_id in sources and sources[row.source_id] != source:
            raise ValueError('Conflicting source provenance')
        sources[row.source_id] = source
        key = (row.sha256, row.animal_id)
        intervals.setdefault(key, []).append((row.start_seconds, row.end_seconds))
        if root is not None:
            path = (root / row.path).resolve()
            if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > 2_000_000_000:
                raise ValueError('Missing, escaped or oversized local video')
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != row.sha256:
                raise ValueError('Local media hash mismatch')
    for spans in intervals.values():
        ordered = sorted(spans)
        if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
            raise ValueError('Overlapping reference intervals for the same dog and content')
    if set(r.split for r in contract.records) != {'train', 'validation', 'test'} or len(groups['animal_id']) < 5:
        raise ValueError('All three splits and at least five globally identified dogs required')
    canonical = json.dumps(contract.model_dump(), sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return {'schema_version': 1, 'contract_sha256': hashlib.sha256(canonical.encode()).hexdigest(),
        'policy_sha256': hashlib.sha256(json.dumps(policies, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest(),
        'status': 'reference_contract_validated', 'evaluation_ready': False,
        'synthetic': contract.synthetic, 'local_hashes_verified': root is not None,
        'counts': {part: sum(r.split == part for r in contract.records) for part in ('train', 'validation', 'test')},
        'double_reviewed': sum(len(r.reviews) == 2 for r in contract.records),
        'adjudicated': sum(any(v.label != r.label for v in r.reviews) for r in contract.records),
        'unit': 'one target dog in a fixed half-open [start,end) reference window',
        'prediction_match': 'exact clip_id + source SHA256 + start/end; one prediction or explicit abstention per window',
        'remaining': ['decode and frame/time alignment verification', 'independent expert and identity evidence review',
            'model predictions bound to this locked contract', 'held-out metrics and uncertainty reporting']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', required=True, type=Path)
    p.add_argument('--registry', required=True, type=Path)
    p.add_argument('--media-root', type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    try:
        if args.output.exists():raise FileExistsError('Preserve previous evidence; choose a new output')
        if args.manifest.stat().st_size > 8_000_000:raise ValueError('Reference manifest too large')
        result = validate_contract(json.loads(args.manifest.read_text()), args.registry, args.media_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as out:json.dump(result, out, indent=2)
    except (OSError, ValueError):
        p.exit(2, 'Reference contract blocked: check permissions, global identities, reviews, intervals, local hashes and a fresh output path.\n')
    print('Reference contract validated. No model inference or dog behavior accuracy measured.')


if __name__ == '__main__':main()
