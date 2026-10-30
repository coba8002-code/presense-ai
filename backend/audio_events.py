"""Opt-in local AST WAV event scoring. No media persistence or cloud inference."""
import asyncio
import os
from fastapi import APIRouter, HTTPException, Request
from starlette.requests import ClientDisconnect
from training.pretrained_audio import MAX_BYTES,read_wav_bytes
from backend.audio_process import run_ast,WorkerError,WorkerTimeout
from backend.audio_auth import authorize,revalidate

router=APIRouter()
UPLOAD_TIMEOUT=15
INFERENCE_TIMEOUT=60

async def score_until_disconnect(request,raw):
    async def disconnected():
        while True:
            if (await request.receive())['type']=='http.disconnect':return
    worker=asyncio.create_task(run_ast(raw,timeout=INFERENCE_TIMEOUT))
    watcher=asyncio.create_task(disconnected())
    try:
        done,_=await asyncio.wait({worker,watcher},return_when=asyncio.FIRST_COMPLETED)
        if watcher in done:
            await watcher
            raise HTTPException(499,'Client disconnected; analysis cancelled')
        return await worker
    finally:
        for task in (worker,watcher):
            if not task.done():task.cancel()
        await asyncio.gather(worker,watcher,return_exceptions=True)

@router.post('/v1/audio/events')
async def audio_events(request: Request):
    if os.getenv('PETSENSE_ENABLE_AST','false').lower()!='true':
        raise HTTPException(503,'Local AST event scoring is disabled')
    owner=authorize(request)
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
        if lock.locked():raise HTTPException(429,'AST is busy; retry after completion',headers={'Retry-After':'1'})
        async with lock:
            body=bytearray()
            try:
                async with asyncio.timeout(UPLOAD_TIMEOUT):
                    async for chunk in request.stream():
                        body.extend(chunk)
                        if len(body)>MAX_BYTES:raise HTTPException(413,'Audio too large')
                read_wav_bytes(bytes(body))
            except TimeoutError:
                raise HTTPException(408,'Audio upload deadline exceeded') from None
            except (ValueError,ClientDisconnect):
                raise HTTPException(422,'Invalid bounded 16 kHz PCM16 WAV') from None
            try:
                result=await score_until_disconnect(request,bytes(body))
            except WorkerTimeout:
                raise HTTPException(504,'Inference deadline exceeded; worker terminated') from None
            except WorkerError:
                raise HTTPException(503,'Local AST unavailable; install dependencies and cache pinned weights') from None
            revalidate(request,owner)
            return result
    finally:admission.leave()
