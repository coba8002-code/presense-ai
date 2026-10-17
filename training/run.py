import argparse
import json
from pathlib import Path
import numpy as np
from training.audio import features, FEATURE_VERSION
from training.data import load_records, split_records, fingerprint
from training.model import fit, probabilities
from evaluation.metrics import classification_metrics


def run(manifest: str | Path, registry: str | Path, species: str,
        output: str | Path, seed: int = 42, threshold: float = .7) -> dict:
    if not 0 <= threshold <= 1:
        raise ValueError('Threshold must be in [0, 1]')
    rows, policies = load_records(manifest, registry, species)
    splits = split_records(rows, seed)
    labels = sorted({row['label'] for row in rows})
    root = Path(manifest).parent
    x = {key: np.stack([features(root / r['path']) for r in part]) for key, part in splits.items()}
    y = {key: np.array([labels.index(r['label']) for r in part]) for key, part in splits.items()}
    mean = x['train'].mean(axis=0)
    scale = x['train'].std(axis=0)
    scale[scale < 1e-8] = 1
    standardized = {key: (value - mean) / scale for key, value in x.items()}
    candidates = []
    for penalty in (0.0, .01, .1):
        weights = fit(standardized['train'], y['train'], len(labels), penalty)
        validation = classification_metrics(y['validation'], probabilities(standardized['validation'], weights), labels, threshold)
        candidates.append((validation['macro_f1'], penalty, weights, validation))
    _, penalty, weights, validation = max(candidates, key=lambda item: item[0])
    test_probs = probabilities(standardized['test'], weights)
    metrics = classification_metrics(y['test'], test_probs, labels, threshold)
    model = dict(format_version=1, feature_version=FEATURE_VERSION, species=species,
                 labels=labels, mean=mean.tolist(), scale=scale.tolist(), weights=weights.tolist(),
                 seed=seed, penalty=penalty, threshold=threshold, manifest_fingerprint=fingerprint(rows),
                 test_paths=[r['path'] for r in splits['test']],
                 synthetic=all(p.get('synthetic') is True for p in policies.values()))
    report = dict(synthetic=model['synthetic'], baseline='NumPy spectral softmax v1',
                  seed=seed, penalty=penalty, validation=validation, test=metrics,
                  rights=policies, manifest_fingerprint=model['manifest_fingerprint'],
                  failure_cases=[{'path': r['path'], 'expected': r['label'],
                                  'predicted': labels[int(p.argmax())]}
                                 for r, p in zip(splits['test'], test_probs)
                                 if labels[int(p.argmax())] != r['label']])
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, value in [('model', model), ('metrics', report), ('splits', splits)]:
        (output / f'{name}.json').write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description='Train a rights-gated dog/cat audio baseline')
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--registry', default='datasets/registry.json')
    parser.add_argument('--species', choices=['dog', 'cat'], required=True)
    parser.add_argument('--output', required=True, help='New directory; never overwrite prior runs')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--threshold', type=float, default=.7)
    args = parser.parse_args()
    try:
        result = run(**vars(args))
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Training blocked: {exc}\n')
    print(json.dumps({'synthetic': result['synthetic'], 'test': result['test']}, indent=2))


if __name__ == '__main__':
    main()
