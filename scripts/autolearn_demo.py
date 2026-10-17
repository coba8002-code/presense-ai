"""Prepare owned tone fixtures for the recurring trainer, never animal accuracy."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import wave
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    for name in ('train', 'benchmark'):
        folder = root / name
        subprocess.run([sys.executable, '-m', 'training.synthetic', '--species', 'dog',
                        '--output', str(folder)], check=True)
        manifest = folder / 'manifest.json'
        rows = json.loads(manifest.read_text())
        for row in rows:
            row['animal_id'] = name + '-' + row['animal_id']
            row['recording_group'] = row['animal_id'] + '-session'
            if name == 'benchmark':
                # Deliberate amplitude shift exercises generalization, not just replay.
                path = folder / row['path']
                with wave.open(str(path), 'rb') as stream:
                    params = stream.getparams()
                    data = stream.readframes(stream.getnframes())
                with wave.open(str(path), 'wb') as stream:
                    stream.setparams(params)
                    stream.writeframes((np.frombuffer(data, '<i2') // 2).astype('<i2').tobytes())
        manifest.write_text(json.dumps(rows, indent=2))
    registry = json.loads((root / 'train/registry.json').read_text())
    registry['synthetic'].update(acquisition_evidence='generated locally by training.synthetic',
                                 label_review='known generated frequencies; no behavior labels')
    (root / 'registry.json').write_text(json.dumps(registry, indent=2))
    (root / 'inbox').mkdir()
    job = dict(version=1, species='dog', manifest='../train/manifest.json',
               benchmark='../benchmark/manifest.json', registry='../registry.json')
    (root / 'inbox/demo.json').write_text(json.dumps(job, indent=2))
    print(f'Synthetic-only inbox prepared at {root / "inbox"}')


if __name__ == '__main__':
    main()
