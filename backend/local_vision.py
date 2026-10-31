"""Account-scoped, explicitly consented local vision research endpoint."""
import asyncio
import os
import httpx
from fastapi import APIRouter,HTTPException,Request
from pydantic import ValidationError
from starlette.requests import ClientDisconnect
from backend.accounts import access
from backend.local_vlm import LocalConfig,observe_local
from backend.vlm import VisionInput,VLMError
router=APIRouter()

async def until_disconnect(request,payload,config):
    async def disconnected():
        while True:
            if (await request.receive())['type']=='http.disconnect':return
    async def infer():
        async with httpx.AsyncClient() as client:return await observe_local(payload,client,config)
    worker=asyncio.create_task(infer());watcher=asyncio.create_task(disconnected())
    try:
        done,_=await asyncio.wait({worker,watcher},return_when=asyncio.FIRST_COMPLETED)
        if watcher in done:raise HTTPException(499,'Client disconnected; response discarded')
        return await worker
    finally:
        for task in (worker,watcher):
            if not task.done():task.cancel()
        await asyncio.gather(worker,watcher,return_exceptions=True)

@router.post('/v1/me/vision/local-observe')
async def local_vision(request:Request):
    if os.getenv('PETSENSE_ENABLE_LOCAL_VLM','false').lower()!='true':raise HTTPException(503,'Local observation disabled')
    _,owner,_=access(request)
    try:config=LocalConfig(os.getenv('PETSENSE_LOCAL_VLM_BASE_URL',''),os.getenv('PETSENSE_LOCAL_VLM_MODEL',''),os.getenv('PETSENSE_LOCAL_VLM_KEY',''))
    except ValueError:raise HTTPException(503,'Local observation not configured') from None
    if request.headers.get('content-type','').split(';')[0]!='application/json':raise HTTPException(415,'Expected application/json')
    lock=request.app.state.local_vision_lock
    if lock.locked():raise HTTPException(429,'Local vision busy',headers={'Retry-After':'1'})
    async with lock:
        body=bytearray()
        try:
            async with asyncio.timeout(15):
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body)>750000:raise HTTPException(413,'Image request too large')
            payload=VisionInput.model_validate_json(body)
        except TimeoutError:raise HTTPException(408,'Image upload deadline exceeded') from None
        except (ValidationError,ClientDisconnect):raise HTTPException(422,'Invalid image request') from None
        if not payload.consent:raise HTTPException(403,'Explicit sharing consent required')
        if access(request)[1]!=owner:raise HTTPException(401,'Session changed')
        try:result=await until_disconnect(request,payload,config)
        except VLMError:raise HTTPException(502,'Local observation unavailable') from None
        if access(request)[1]!=owner:raise HTTPException(401,'Session changed')
        return {'observation':result.model_dump(),'confidence_kind':'uncalibrated','provider':'configured_local_vlm','notice':'Observable dog posture only; not intent translation, diagnosis or independently verified accuracy.'}
