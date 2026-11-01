"""Local dataset policy and manifest boundaries; no dataset downloads."""
import json
from pathlib import Path


def approve_dataset(registry: str | Path, dataset: str) -> dict:
    from training.source_routes import restricted_license
    entries = json.loads(Path(registry).read_text())
    if not isinstance(entries, dict):
        raise ValueError('Dataset registry must be a JSON object')
    policy = entries.get(dataset, {})
    if not isinstance(policy, dict):
        raise ValueError('Dataset policy must be a JSON object')
    if restricted_license(policy) or policy.get('usage_lane', 'commercial_candidate') != 'commercial_candidate':
        raise ValueError('Research/restricted sources cannot enter the commercial training pipeline')
    if 'synthetic' in policy and not isinstance(policy['synthetic'], bool):
        raise ValueError('Synthetic provenance flag must be a boolean')
    required = ('source', 'version', 'license', 'rights_evidence', 'consent',
                'reviewer', 'reviewed_at')
    if (policy.get('status') != 'approved'
            or policy.get('training_allowed') is not True
            or policy.get('commercial_allowed') is not True
            or any(not isinstance(policy.get(key), str) or not policy[key].strip()
                   or policy[key].strip().lower() in ('unknown', 'pending')
                   for key in required)):
        raise ValueError(f'Dataset {dataset!r} is not approved for this training use')
    return policy


def load_records(manifest: str | Path, registry: str | Path, species: str) -> tuple[list, dict]:
    import hashlib
    from training.audio import MAX_BYTES
    if species != 'dog':
        raise ValueError('Dog-only MVP: species must be dog')
    manifest = Path(manifest)
    root = manifest.parent.resolve()
    rows = json.loads(manifest.read_text())
    if not isinstance(rows, list) or not rows or len(rows) > 100000:
        raise ValueError('Manifest must contain 1–100000 records')
    selected, policies, hashes = [], {}, set()
    for raw in rows:
        required = ('path', 'animal_id', 'species', 'label', 'dataset')
        if not isinstance(raw, dict) or any(
            not isinstance(raw.get(key), str) or not raw[key].strip() for key in required
        ):
            raise ValueError('Every record needs path, global animal identity, species, label and dataset')
        if raw['species'] != species:
            continue
        if any(raw[key] != raw[key].strip() for key in required):
            raise ValueError('Manifest fields must not have leading/trailing whitespace')
        if raw['animal_id'].strip().lower() in ('unknown', 'none', 'null'):
            raise ValueError('Unknown animal identity')
        # Authorize before inspecting any media.
        policies[raw['dataset']] = approve_dataset(registry, raw['dataset'])
        if Path(raw['path']).is_absolute():
            raise ValueError('Media paths must be relative to the manifest directory')
        path = (root / raw['path']).resolve()
        if not path.is_relative_to(root) or path == root:
            raise ValueError('Media path escapes manifest directory')
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise ValueError('Missing or oversized media')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in hashes:
            raise ValueError('Duplicate audio content could leak across partitions')
        hashes.add(digest)
        selected.append({**raw, 'sha256': digest})
    if not selected:
        raise ValueError('No records for requested species')
    return sorted(selected, key=lambda row: row['path']), policies


def split_records(rows: list, seed: int) -> dict:
    import random
    from training.grouping import animal_groups
    connected = animal_groups(rows)
    groups = sorted(set(connected.values()))
    if len(groups) < 5:
        raise ValueError('Grouping overlap or insufficient data: at least five connected animal/source/household groups required')
    random.Random(seed).shuffle(groups)
    held_out = max(1, len(groups) // 5)
    memberships = {'test': set(groups[:held_out]),
                   'validation': set(groups[held_out:2 * held_out]),
                   'train': set(groups[2 * held_out:])}
    result = {key: sorted([r for r in rows if connected[r['animal_id']] in animals],
                          key=lambda row: row['path']) for key, animals in memberships.items()}
    labels = {r['label'] for r in rows}
    if len(labels) < 2 or any({r['label'] for r in part} != labels for part in result.values()):
        raise ValueError('Every partition must cover all labels; collect more animals or review the split')
    return result


def fingerprint(rows: list) -> str:
    import hashlib
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
