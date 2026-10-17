"""Bounded, stateless near-real-time audio API for local development."""
import asyncio
from collections import deque
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import secrets
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
import numpy as np
from starlette.requests import ClientDisconnect

from training.audio import pcm_features
from training.model import predict

router = APIRouter()


class Admission:
    """Single-process shared-token development limits; not a distributed limiter."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.arrivals = deque()
        self.active = 0

    def enter(self):
        now = self.clock()
        while self.arrivals and self.arrivals[0] <= now - 1:
            self.arrivals.popleft()
        if self.active >= 2 or len(self.arrivals) >= 5:
            raise ValueError('Audio request limit reached')
        self.arrivals.append(now)
        self.active += 1

    def leave(self):
        self.active -= 1


class AudioEngine:
    def __init__(self, artifact: dict):
        if not isinstance(artifact, dict):
            raise ValueError('Invalid audio model')
        if (artifact.get('format_version') != 1 or artifact.get('synthetic') is not False
                or artifact.get('species') != 'dog'):
            raise ValueError('Only reviewed non-synthetic dog models can serve live audio')
        labels = artifact.get('labels')
        threshold = artifact.get('threshold')
        if (not isinstance(labels, list) or not 2 <= len(labels) <= 100
                or any(not isinstance(label, str) or not 1 <= len(label) <= 100 for label in labels)
                or len(set(labels)) != len(labels)
                or type(threshold) not in (int, float) or not math.isfinite(threshold)
                or not 0 <= threshold <= 1):
            raise ValueError('Invalid labels or abstention threshold')
        try:
            predict(artifact, np.zeros((1, 34)))
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError('Invalid audio model parameters') from exc
        self.artifact = artifact


@lru_cache(maxsize=1)
def load_engine(path: str) -> AudioEngine:
    """Trusted operator path only. Restart the process after replacing a model."""
    with Path(path).open('rb') as stream:
        raw = stream.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError('Audio model too large')
    return AudioEngine(json.loads(raw))


def analyze_pcm(raw: bytes, species: str, sequence: int, engine: AudioEngine | None) -> dict:
    started = time.perf_counter()
    vector = pcm_features(raw)
    rms = float(vector[-2])
    active = rms >= .02
    result = dict(sequence=sequence, audio_ms=len(raw) / 32, rms=rms,
                  sound_activity=active, detector='rms_threshold_v1',
                  status='quiet' if not active else 'model_unavailable',
                  model_ready=engine is not None, prediction=None, confidence=None,
                  confidence_kind='uncalibrated', abstained=True,
                  notice='Sound activity is not bark recognition or a veterinary diagnosis.')
    if active and engine is not None:
        artifact = engine.artifact
        if artifact['species'] != species:
            result['status'] = 'species_mismatch'
        else:
            probabilities = predict(artifact, vector[None, :])[0]
            index = int(probabilities.argmax())
            confidence = float(probabilities[index])
            accepted = confidence >= artifact['threshold']
            result.update(status='predicted' if accepted else 'low_confidence',
                          prediction=artifact['labels'][index] if accepted else None,
                          confidence=confidence, abstained=not accepted)
    result['processing_ms'] = round((time.perf_counter() - started) * 1000, 3)
    return result


@router.post('/v1/audio/chunks')
async def audio_chunk(request: Request):
    if os.getenv('PETSENSE_ENABLE_AUDIO', 'false').lower() != 'true':
        raise HTTPException(503, 'Live audio is disabled')
    token = os.getenv('PETSENSE_API_TOKEN', '')
    if not token:
        raise HTTPException(503, 'Live audio is not configured')
    if not secrets.compare_digest(request.headers.get('authorization', ''), f'Bearer {token}'):
        raise HTTPException(401, 'Authentication required')
    if request.headers.get('x-audio-consent') != 'true':
        raise HTTPException(403, 'Explicit audio sharing consent required')
    if request.headers.get('content-type') != 'application/octet-stream':
        raise HTTPException(415, 'Expected raw mono PCM16')
    species = request.headers.get('x-audio-species')
    sequence = request.headers.get('x-audio-sequence', '')
    if species != 'dog' or not sequence.isascii() or not sequence.isdecimal() or len(sequence) > 9:
        raise HTTPException(422, 'Dog-only MVP: invalid species or sequence')
    admission = request.app.state.audio_admission
    try:
        admission.enter()
    except ValueError:
        raise HTTPException(429, 'Audio request limit reached', headers={'Retry-After': '1'}) from None
    try:
        body = bytearray()
        try:
            async with asyncio.timeout(3):
                async for chunk in request.stream():
                    if len(body) + len(chunk) > 32000:
                        raise HTTPException(413, 'Audio chunk exceeds one second')
                    body.extend(chunk)
        except TimeoutError:
            raise HTTPException(408, 'Audio upload timed out') from None
        except ClientDisconnect:
            raise HTTPException(400, 'Audio upload disconnected') from None
        if len(body) % 2 or len(body) < 3200:
            raise HTTPException(422, 'Expected 0.1–1 s of mono 16 kHz PCM16')
        engine = None
        path = os.getenv('PETSENSE_AUDIO_MODEL', '')
        if path and os.getenv('PETSENSE_AUDIO_MODEL_APPROVED', 'false').lower() == 'true':
            try:
                engine = load_engine(path)
            except (ValueError, OSError):
                raise HTTPException(503, 'Audio model unavailable') from None
        return analyze_pcm(bytes(body), species, int(sequence), engine)
    finally:
        admission.leave()


ASSETS = {'': ('index.html', 'text/html'), 'client.js': ('client.js', 'text/javascript'),
          'capture.js': ('capture.js', 'text/javascript')}


def asset_response(name: str):
    if name not in ASSETS:
        raise HTTPException(404, 'Not found')
    file, media_type = ASSETS[name]
    return Response((Path(__file__).parent / 'static' / file).read_text(), media_type=media_type,
                    headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                             'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'",
                             'Permissions-Policy': 'microphone=(self), camera=()'})


@router.get('/realtime')
async def realtime_demo():
    return asset_response('')


@router.get('/realtime/{name}')
async def realtime_asset(name: str):
    return asset_response(name)
