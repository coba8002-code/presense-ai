"""Opt-in local AST WAV event scoring. No media persistence or cloud inference."""
import asyncio
from functools import lru_cache
import os
import secrets
import threading

from fastapi import APIRouter, HTTPException, Request
from starlette.requests import ClientDisconnect
from training.pretrained_audio import MAX_BYTES, ASTDogAudio, read_wav_bytes

router=APIRouter()
_worker_lock=threading.Lock()
UPLOAD_TIMEOUT=15
INFERENCE_TIMEOUT=60

class InferenceBusy(RuntimeError):
    pass

def infer(signal, digest):
    # A cancelled HTTP request must not allow overlapping worker threads.
    if not _worker_lock.acquire(blocking=False):
        raise InferenceBusy("Inference worker is busy")
    try:
        return get_model().analyze(signal,digest)
    finally:
        _worker_lock.release()


@lru_cache(maxsize=1)
def get_model():
    return ASTDogAudio()

@router.post('/v1/audio/events')
async def audio_events(request: Request):
    if os.getenv('PETSENSE_ENABLE_AST','false').lower()!='true':
        raise HTTPException(503,'Local AST event scoring is disabled')
    token=os.getenv('PETSENSE_API_TOKEN','')
    if not token:
        raise HTTPException(503,'Audio event scoring is not configured')
    if not secrets.compare_digest(request.headers.get('authorization',''),f'Bearer {token}'):
        raise HTTPException(401,'Authentication required')
    if request.headers.get('x-audio-consent')!='true':
        raise HTTPException(403,'Explicit audio consent required')
    if request.headers.get('x-audio-species')!='dog':
        raise HTTPException(422,'Only dog observations are supported')
    if request.headers.get('content-type')!='audio/wav':
        raise HTTPException(415,'Expected audio/wav')
    admission=request.app.state.audio_admission
    try:admission.enter()
    except ValueError:raise HTTPException(429,'Audio request limit reached') from None
    try:
        lock=request.app.state.ast_lock
        if lock.locked():raise HTTPException(429,'AST is busy; retry after completion')
        async with lock:
            body=bytearray()
            try:
                async with asyncio.timeout(UPLOAD_TIMEOUT):
                    async for chunk in request.stream():
                        body.extend(chunk)
                        if len(body)>MAX_BYTES:raise HTTPException(413,'Audio too large')
                signal,digest=read_wav_bytes(bytes(body))
            except TimeoutError:
                raise HTTPException(408,'Audio upload deadline exceeded') from None
            except (ValueError,ClientDisconnect):
                raise HTTPException(422,'Invalid bounded 16 kHz PCM16 WAV') from None
            try:
                # CPU work runs outside the event loop; only one model execution at a time.
                async with asyncio.timeout(INFERENCE_TIMEOUT):
                    result=await asyncio.to_thread(infer,signal,digest)
            except TimeoutError:
                # asyncio cancellation cannot kill a running model thread. The worker lock stays held.
                raise HTTPException(504,'Inference deadline exceeded; worker may still be finishing') from None
            except InferenceBusy:
                raise HTTPException(429,'Inference worker is busy',headers={'Retry-After':'1'}) from None
            except Exception:
                raise HTTPException(503,'Local AST unavailable; install dependencies and cache pinned weights') from None
            return result
    finally:admission.leave()
