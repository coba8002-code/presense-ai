"""Validate approved local audio and partitions without fitting a model."""
import argparse
from collections import Counter
import json
from pathlib import Path

from training.audio import features, FEATURE_VERSION
from training.data import fingerprint, load_records, split_records
from training.grouping import animal_groups


def check(manifest: str | Path, registry: str | Path, species: str, seed: int = 42) -> dict:
    rows, policies = load_records(manifest, registry, species)
    partitions = split_records(rows, seed)
    root = Path(manifest).parent
    for row in rows:
        features(root / row['path'])
    return {
        'status': 'passed', 'species': species, 'seed': seed,
        'feature_version': FEATURE_VERSION,
        'synthetic': all(policy.get('synthetic') is True for policy in policies.values()),
        'record_count': len(rows),
        'animal_count': len({row['animal_id'] for row in rows}),
        'connected_group_count': len(set(animal_groups(rows).values())),
        'grouping_field_coverage': {key:sum(key in r for r in rows) for key in
                                    ('household_id','recording_group','source_id','duplicate_group')},
        'manifest_fingerprint': fingerprint(rows),
        'datasets': sorted(policies),
        'partitions': {
            name: {'records': len(part), 'animals': len({r['animal_id'] for r in part}),
                   'class_counts': dict(sorted(Counter(r['label'] for r in part).items()))}
            for name, part in partitions.items()
        },
        'notice': 'Structural validation only; no model trained or legal rights independently verified.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--registry', default='datasets/registry.json')
    parser.add_argument('--species', choices=['dog'], required=True)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    try:
        result = check(**vars(args))
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Preflight blocked: {exc}\n')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
