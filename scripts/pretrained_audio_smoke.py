"""Actual pretrained AST forward passes on generated PCM fixtures, not dog accuracy."""
import json
from pathlib import Path
import tempfile
import wave
import numpy as np
from training.pretrained_audio import ASTDogAudio, read_wav, DOG_LABELS


def main():
    output = Path('artifacts/ast-smoke.json')
    if output.exists():
        raise ValueError('Use a fresh smoke output directory')
    model = ASTDogAudio()
    reports = []
    with tempfile.TemporaryDirectory() as directory:
        for name, signal in [('silence', np.zeros(16000)),
                             ('tone440', .1*np.sin(2*np.pi*440*np.arange(16000)/16000))]:
            path = Path(directory)/f'{name}.wav'
            with wave.open(str(path), 'wb') as stream:
                stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(16000)
                stream.writeframes((signal*32767).astype('<i2').tobytes())
            decoded, digest = read_wav(path)
            result = model.analyze(decoded, digest)
            repeat = model.analyze(decoded, digest)
            scores = [s['score'] for s in result['dog_event_scores']]
            assert len(scores) == len(DOG_LABELS) and all(0 <= s <= 1 for s in scores)
            assert result['dog_event_scores'] == repeat['dog_event_scores']
            assert result['decision'] == 'abstain' and not result['production_ready']
            reports.append(dict(fixture=name, synthetic=True, **result))
    output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(synthetic=True, purpose='pretrained_inference_plumbing_only',
                  dog_accuracy=None, deterministic_repeat=True, reports=reports)
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
