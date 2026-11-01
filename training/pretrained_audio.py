"""Optional local AST inference. Dog sound-event scores, not emotion or diagnosis."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import time
import wave
import numpy as np

MODEL = 'MIT/ast-finetuned-audioset-10-10-0.4593'
REVISION = 'f826b80d28226b62986cc218e5cec390b1096902'
DOG_LABELS = ('Dog', 'Bark', 'Yip', 'Howl', 'Bow-wow', 'Growling', 'Whimper (dog)')
MAX_BYTES = 2_000_000


def read_wav(path):
    path = Path(path)
    if not path.is_file() or not 44 <= path.stat().st_size <= MAX_BYTES:
        raise ValueError('Expected local PCM16 WAV under 2 MB')
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Audio too large')
    return read_wav_bytes(data)


def read_wav_bytes(data):
    if not isinstance(data, bytes) or not 44 <= len(data) <= MAX_BYTES:
        raise ValueError('Expected bounded PCM16 WAV bytes')
    try:
        with wave.open(io.BytesIO(data), 'rb') as stream:
            channels, frames = stream.getnchannels(), stream.getnframes()
            if (channels not in (1, 2) or stream.getsampwidth() != 2
                    or stream.getframerate() != 16000 or not 1600 <= frames <= 160000):
                raise ValueError('Expected 0.1–10 s, 16 kHz mono/stereo PCM16 WAV')
            raw = stream.readframes(frames)
            if len(raw) != frames * channels * 2:
                raise ValueError('Truncated WAV')
    except (wave.Error, EOFError) as exc:
        raise ValueError('Invalid WAV') from exc
    signal = np.frombuffer(raw, dtype='<i2').reshape(-1, channels).astype(np.float32).mean(axis=1) / 32768
    return signal, hashlib.sha256(data).hexdigest()


def dog_scores(logits, id2label):
    logits = np.asarray(logits, dtype=np.float64)
    labels = {int(k):v for k,v in id2label.items()}
    if logits.ndim != 1 or not np.all(np.isfinite(logits)) or set(labels) != set(range(len(logits))):
        raise ValueError('Invalid model output or class mapping')
    if any(list(labels.values()).count(name) != 1 for name in DOG_LABELS):
        raise ValueError('Required dog sound labels missing or duplicated')
    # AudioSet is multi-label: never renormalize over dog classes with softmax.
    scores = np.exp(-np.logaddexp(0, -logits))
    return sorted([dict(label=name, score=float(scores[i])) for i,name in labels.items()
                   if name in DOG_LABELS], key=lambda item: (-item['score'], item['label']))


class ASTDogAudio:
    def __init__(self):
        import torch
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        torch.set_num_threads(2)
        self.extractor = AutoFeatureExtractor.from_pretrained(MODEL, revision=REVISION, trust_remote_code=False)
        self.model = AutoModelForAudioClassification.from_pretrained(
            MODEL, revision=REVISION, use_safetensors=True, trust_remote_code=False,
            attn_implementation='eager').eval()
        if self.extractor.sampling_rate != 16000 or self.model.config.num_labels != 527:
            raise ValueError('Unexpected pinned model input/class contract')
        dog_scores(np.zeros(527), self.model.config.id2label)

    def analyze(self, signal, digest):
        import torch
        signal = np.asarray(signal)
        if (signal.ndim != 1 or not 1600 <= len(signal) <= 160000
                or not np.all(np.isfinite(signal)) or np.max(np.abs(signal)) > 1):
            raise ValueError('Expected bounded finite 16 kHz normalized mono samples')
        started = time.monotonic()
        inputs = self.extractor(signal, sampling_rate=16000, return_tensors='pt')
        with torch.inference_mode():
            logits = self.model(**inputs).logits[0].cpu().numpy()
        scores = dog_scores(logits, self.model.config.id2label)
        from training.audio_quality import audio_quality
        quality = audio_quality(signal)
        return dict(execution_kind='pretrained_model', model=MODEL, revision=REVISION, license='bsd-3-clause', input_sha256=digest,
                    sample_rate=16000, duration_seconds=len(signal)/16000,
                    preprocessing_and_inference_seconds=time.monotonic()-started,
                    audio_quality=quality, dog_event_scores=scores, score_type='uncalibrated_independent_sigmoid',
                    decision='abstain', reason='No validated dog-specific decision thresholds',
                    species_verified=False, production_ready=False,
                    limitations=['Clip-level scores, not event timestamps',
                                 'No emotion, intent or diagnosis output',
                                 'Background playback and non-dog false positives are unvalidated'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = Path(args.output)
    if out.exists():
        raise ValueError('Output must not exist')
    signal, digest = read_wav(args.audio)  # Reject invalid audio BEFORE model download.
    result = ASTDogAudio().analyze(signal, digest)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
