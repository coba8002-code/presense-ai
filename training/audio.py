"""Bounded PCM16 WAV spectral features; sample rate must be explicitly 16 kHz."""
from pathlib import Path
import wave
import numpy as np

MAX_BYTES = 2_000_000
FEATURE_VERSION = 'pcm16-16khz-logbands-v1'


def features(path: str | Path) -> np.ndarray:
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Audio file exceeds 2 MB')
    try:
        with wave.open(str(path), 'rb') as stream:
            if (stream.getsampwidth() != 2 or stream.getframerate() != 16000
                    or stream.getnchannels() not in (1, 2)
                    or not 1600 <= stream.getnframes() <= 160000):
                raise ValueError('Expected 0.1–10 s, 16 kHz, mono/stereo PCM16 WAV')
            channels, frames = stream.getnchannels(), stream.getnframes()
            raw = stream.readframes(frames)
            if len(raw) != frames * channels * 2:
                raise ValueError('Truncated audio')
    except (wave.Error, EOFError) as exc:
        raise ValueError('Invalid WAV') from exc
    signal = np.frombuffer(raw, dtype='<i2').reshape(-1, channels).mean(axis=1) / 32768
    return signal_features(signal)


def pcm_features(raw: bytes) -> np.ndarray:
    """Features for a bounded live mono PCM16 chunk, using training preprocessing."""
    if len(raw) % 2 or not 3200 <= len(raw) <= 32000:
        raise ValueError('Expected 0.1–1 s of mono 16 kHz PCM16')
    signal = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768
    return signal_features(signal)


def signal_features(signal: np.ndarray) -> np.ndarray:
    windows = np.lib.stride_tricks.sliding_window_view(signal, 512)[::256]
    power = np.abs(np.fft.rfft(windows * np.hanning(512), axis=1)) ** 2
    bands = np.array_split(power, 16, axis=1)
    log_bands = np.stack([np.log1p(band.mean(axis=1)) for band in bands], axis=1)
    return np.concatenate([log_bands.mean(axis=0), log_bands.std(axis=0),
                           [np.sqrt(np.mean(signal**2)), np.mean(np.diff(np.signbit(signal))) ]])
