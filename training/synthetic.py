"""Generate owned sine-wave fixtures to exercise plumbing, NOT animal performance."""
import argparse
import json
from pathlib import Path
import wave
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--species', required=True, choices=['dog'])
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    policy = dict(status='approved', training_allowed=True, commercial_allowed=True,
                  source='generated sine-wave fixture; no animals', version='1', license='CC0-1.0',
                  rights_evidence='generated locally by training.synthetic', consent='no personal data',
                  reviewer='synthetic fixture generator', reviewed_at='2026-10-17', synthetic=True)
    (root / 'registry.json').write_text(json.dumps({'synthetic': policy}, indent=2))
    rows = []
    for animal in range(9):
        for label, frequency in [('low', 250), ('high', 2000)]:
            name = f'{animal}-{label}.wav'
            signal = .3 * np.sin(2 * np.pi * (frequency + animal) * np.arange(8000) / 16000)
            with wave.open(str(root / name), 'wb') as stream:
                stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                stream.writeframes((signal * 32767).astype('<i2').tobytes())
            rows.append(dict(path=name, animal_id=f'synthetic-{animal}', species=args.species,
                             label=label, dataset='synthetic'))
    (root / 'manifest.json').write_text(json.dumps(rows, indent=2))
    print('Generated synthetic fixtures only; no real animal audio or behavioral labels.')


if __name__ == '__main__':
    main()
