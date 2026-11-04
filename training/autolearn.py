"""Bounded, local, rights-gated recurring training. Never downloads or deploys."""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time

import numpy as np
from training.audio import features
from training.data import load_records, fingerprint, split_records
from training.model import predict
from training.run import run
from evaluation.metrics import classification_metrics

VERSION = 'local-audio-autolearn-v1'
DEFAULT_LIMITS = dict(min_macro_f1=.8, min_coverage=.5, max_ece=.15, min_improvement=.01)
MAX_RECORDS = 2000
MAX_TOTAL_BYTES = 256 * 1024 * 1024


def read_json(path):
    path = Path(path)
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('JSON exceeds 8 MiB limit')
    return json.loads(path.read_text())


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def local_path(root, value):
    if not isinstance(value, str) or not value.strip() or '://' in value:
        raise ValueError('Only local file paths are accepted')
    return (root / value).resolve()


def decide(metrics, incumbent, synthetic, limits):
    if synthetic:
        return 'synthetic_only'
    if (metrics['macro_f1'] < limits['min_macro_f1']
            or metrics['coverage'] < limits['min_coverage']
            or metrics['ece'] > limits['max_ece']):
        return 'rejected'
    if incumbent is None:
        return 'review_required'
    if (metrics['macro_f1'] < incumbent['macro_f1'] + limits['min_improvement']
            or metrics['coverage'] < incumbent['coverage']
            or metrics['ece'] > incumbent['ece']
            or any(a < b for a, b in zip(metrics['per_class_f1'], incumbent['per_class_f1']))):
        return 'rejected'
    return 'candidate'


def lineage(rows):
    from training.grouping import valid_identity
    fields=['animal_id','recording_group','sha256']
    fields += [key for key in ('household_id','source_id','duplicate_group') if any(key in r for r in rows)]
    return {field: sorted({valid_identity(r[field]) for r in rows if field in r}) for field in fields}


def assert_disjoint(first, second):
    if not isinstance(first, dict) or not isinstance(second, dict):
        raise ValueError('Invalid training lineage')
    fields=['animal_id','recording_group','sha256']
    fields += [key for key in ('household_id','source_id','duplicate_group') if key in first or key in second]
    for field in fields:
        if any(not isinstance(item.get(field), list) or not item[field]
                or not all(isinstance(v, str) and v for v in item[field]) for item in (first,second)):
            raise ValueError('Missing incumbent training lineage')
        if set(first[field]) & set(second[field]):
            raise ValueError(f'Training/benchmark overlap: {field}')


def reviewed_rows(manifest, registry, species):
    raw = read_json(manifest)
    if not isinstance(raw, list) or len(raw) > MAX_RECORDS:
        raise ValueError('Manifest exceeds automatic training record limit')
    rows, policies = load_records(manifest, registry, species)
    for policy in policies.values():
        for key in ('acquisition_evidence', 'label_review'):
            if (not isinstance(policy.get(key), str) or not policy[key].strip()
                    or policy[key].strip().lower() in ('unknown', 'pending')):
                raise ValueError(f'Automatic learning requires reviewed {key}')
    for row in rows:
        group = row.get('recording_group')
        if (not isinstance(group, str) or not group.strip() or group != group.strip()
                or group.lower() in ('unknown', 'none', 'null')):
            raise ValueError('Known global recording_group required')
    return rows, policies


def snapshot(manifest, rows, destination):
    destination.mkdir()
    copied = []
    for i, row in enumerate(rows):
        data = (manifest.parent / row['path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Media changed during snapshot')
        name = f'{i:06d}.wav'
        (destination / name).write_bytes(data)
        copied.append({**row, 'path': name})
    write_json(destination / 'manifest.json', copied)
    return destination / 'manifest.json'


def score(model, rows, root, labels, threshold):
    if model.get('format_version') != 1 or model.get('labels') != labels:
        raise ValueError('Incumbent model format or labels differ')
    x = np.stack([features(root / row['path']) for row in rows])
    y = np.array([labels.index(row['label']) for row in rows])
    return classification_metrics(y, predict(model, x), labels, threshold)


def process_job(job_path, output):
    """Operator-owned job files only. A receipt is committed atomically per run."""
    job_path, output = Path(job_path).resolve(), Path(output).resolve()
    spec = read_json(job_path)
    allowed = {'version', 'manifest', 'benchmark', 'registry', 'species', 'incumbent', 'limits'}
    if not isinstance(spec, dict) or set(spec) - allowed or spec.get('version') != 1:
        raise ValueError('Invalid job version or unknown job fields')
    limits = {**DEFAULT_LIMITS, **spec.get('limits', {})} if isinstance(spec.get('limits', {}), dict) else {}
    if set(limits) != set(DEFAULT_LIMITS) or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            or not 0 <= v <= 1 for v in limits.values()):
        raise ValueError('Invalid quality gate limits')
    root = job_path.parent
    manifest, benchmark, registry = [local_path(root, spec.get(k))
                                     for k in ('manifest', 'benchmark', 'registry')]
    # Revalidate rights on every scan, including cached jobs.
    read_json(registry)
    rows, policies = reviewed_rows(manifest, registry, spec.get('species'))
    bench, bench_policies = reviewed_rows(benchmark, registry, spec.get('species'))
    train_lineage, bench_lineage = lineage(rows), lineage(bench)
    assert_disjoint(train_lineage, bench_lineage)
    partitions = list(split_records(rows, 42).values())
    for i, part in enumerate(partitions):
        for other in partitions[i + 1:]:
            assert_disjoint(lineage(part), lineage(other))
    labels = sorted({r['label'] for r in rows})
    if set(labels) != {r['label'] for r in bench}:
        raise ValueError('Benchmark must cover exactly the training classes')
    if len(bench_lineage['animal_id']) < 5:
        raise ValueError('Benchmark requires at least five independent animals')
    total = sum((m.parent / r['path']).stat().st_size for m, part in ((manifest, rows), (benchmark, bench)) for r in part)
    if total > MAX_TOTAL_BYTES:
        raise ValueError('Automatic job media exceeds 256 MiB')
    incumbent = None
    if 'incumbent' in spec:
        incumbent = read_json(local_path(root, spec['incumbent']))
        if not isinstance(incumbent, dict) or incumbent.get('species') != spec['species']:
            raise ValueError('Invalid incumbent species')
        assert_disjoint(incumbent.get('training_lineage', {}), bench_lineage)
    code_root = Path(__file__).resolve().parent.parent
    source_hash = hashlib.sha256(b''.join(
        p.read_bytes() for package in ('training', 'evaluation')
        for p in sorted((code_root / package).glob('*.py')))).hexdigest()
    provenance = dict(engine=VERSION, source_hash=source_hash, numpy_version=np.__version__, job=spec, train=fingerprint(rows), benchmark=fingerprint(bench),
                      policies=policies, benchmark_policies=bench_policies, incumbent=incumbent)
    run_id = hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Another training job holds the output lock') from exc
        target = output / run_id
        if (target / 'result.json').exists():
            return read_json(target / 'result.json')
        with tempfile.TemporaryDirectory(prefix='.pending-', dir=output) as temp:
            stage = Path(temp)
            training_manifest = snapshot(manifest, rows, stage / 'train')
            benchmark_manifest = snapshot(benchmark, bench, stage / 'benchmark')
            # Do not retain source media in model artifacts; operators manage the input store.
            registry_snapshot = stage / 'registry.json'
            write_json(registry_snapshot, {**policies, **bench_policies})
            report = run(training_manifest, registry_snapshot, spec['species'], stage / 'artifact')
            model = read_json(stage / 'artifact/model.json')
            model['training_lineage'] = train_lineage
            # Any synthetic involvement keeps this out of real-data candidate selection.
            synthetic = any(p.get('synthetic') is True for p in [*policies.values(), *bench_policies.values()])
            model['synthetic'] = synthetic
            write_json(stage / 'artifact/model.json', model)
            frozen_bench = read_json(benchmark_manifest)
            metrics = score(model, frozen_bench, benchmark_manifest.parent, labels, model['threshold'])
            old_metrics = None
            if incumbent:
                old_metrics = score(incumbent, frozen_bench, benchmark_manifest.parent, labels, model['threshold'])
                synthetic = synthetic or incumbent.get('synthetic') is not False
            # Catch policy revocation/data changes during the fit before publishing a receipt.
            now_rows, now_policies = reviewed_rows(manifest, registry, spec['species'])
            now_bench, now_bench_policies = reviewed_rows(benchmark, registry, spec['species'])
            if (fingerprint(now_rows) != fingerprint(rows) or fingerprint(now_bench) != fingerprint(bench)
                    or now_policies != policies or now_bench_policies != bench_policies):
                raise ValueError('Inputs or rights changed during training')
            result = dict(status='completed', run_id=run_id, engine=VERSION,
                          decision=decide(metrics, old_metrics, synthetic, limits),
                          synthetic=synthetic, benchmark=metrics, incumbent_benchmark=old_metrics,
                          limits=limits, deployed=False, finished_at=time.time(),
                          notice='Repeated acceptance benchmark; not an unbiased final test. No deployment.')
            write_json(stage / 'artifact/result.json', result)
            write_json(stage / 'artifact/provenance.json', provenance)
            # Original paths are retained so the existing evaluation replay command works.
            model['manifest_fingerprint'] = fingerprint(rows)
            original_splits = split_records(rows, model['seed'])
            model['test_paths'] = [r['path'] for r in original_splits['test']]
            write_json(stage / 'artifact/model.json', model)
            report['manifest_fingerprint'] = fingerprint(rows)
            for failure in report['failure_cases']:
                index = int(Path(failure['path']).stem)
                failure['path'] = rows[index]['path']
            write_json(stage / 'artifact/metrics.json', report)
            write_json(stage / 'artifact/splits.json', original_splits)
            os.replace(stage / 'artifact', target)
            return result


def scan(inbox, output):
    inbox = Path(inbox)
    if not inbox.is_dir():
        raise ValueError('Inbox directory does not exist')
    results = []
    jobs = sorted(inbox.glob('*.json'))
    if len(jobs) > 20:
        raise ValueError('Inbox exceeds 20 jobs; archive completed job specifications')
    for job in jobs:
        try:
            result = process_job(job, output)
            results.append(dict(job=job.name, **result))
        except (ValueError, OSError, KeyError, TypeError) as exc:
            results.append(dict(job=job.name, status='blocked', reason=str(exc)))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inbox', required=True)
    parser.add_argument('--output', default='artifacts/autolearn')
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--interval', type=int, default=300)
    args = parser.parse_args()
    if args.interval < 60:
        parser.error('Interval must be at least 60 seconds')
    try:
        while True:
            results = scan(args.inbox, args.output)
            print(json.dumps(results, allow_nan=False), flush=True)
            if not args.watch:
                if any(r['status'] == 'blocked' for r in results):
                    raise SystemExit(2)
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Automatic learning blocked: {exc}\n')


if __name__ == '__main__':
    main()
