import argparse
import json
from pathlib import Path
import numpy as np
from training.audio import features
from training.data import load_records, fingerprint, split_records
from training.model import predict
from evaluation.metrics import classification_metrics


def evaluate(model: str | Path, manifest: str | Path, registry: str | Path) -> dict:
    artifact = json.loads(Path(model).read_text())
    if artifact.get('format_version') != 1:
        raise ValueError('Unsupported model format')
    rows, _ = load_records(manifest, registry, artifact['species'])
    if fingerprint(rows) != artifact['manifest_fingerprint']:
        raise ValueError('Manifest or audio changed since training')
    held_out = split_records(rows, artifact['seed'])['test']
    if [r['path'] for r in held_out] != artifact['test_paths']:
        raise ValueError('Held-out partition changed')
    x = np.stack([features(Path(manifest).parent / r['path']) for r in held_out])
    y = np.array([artifact['labels'].index(r['label']) for r in held_out])
    return classification_metrics(y, predict(artifact, x), artifact['labels'], artifact['threshold'])


def main():
    parser = argparse.ArgumentParser(description='Replay the fixed held-out evaluation')
    parser.add_argument('--model', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--registry', default='datasets/registry.json')
    args = parser.parse_args()
    try:
        result = evaluate(**vars(args))
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Evaluation blocked: {exc}\n')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
