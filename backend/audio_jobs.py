"""Opt-in account-owned persistent audio jobs, with separate temporary-storage consent."""
import asyncio
import os
import re
import sqlite3
from fastapi import APIRouter, HTTPException, Request
from starlette.requests import ClientDisconnect
from backend.accounts import access
from backend.job_store import JobStore, Conflict, Capacity
from training.pretrained_audio import MAX_BYTES,read_wav_bytes

router=APIRouter()

def queue_access(request):
    if os.getenv('PETSENSE_ENABLE_AST_JOBS','false').lower()!='true':raise HTTPException(503,'Audio jobs disabled')
    store,_,token=access(request)
    try:return JobStore(store.path),token
    except (OSError,sqlite3.Error):raise HTTPException(503,'Job store unavailable') from None

def operation(fn,*args):
    try:return fn(*args)
    except PermissionError:raise HTTPException(401,'Session expired or revoked') from None
    except KeyError:raise HTTPException(404,'Job or pet not found') from None
    except Conflict:raise HTTPException(409,'Idempotency key reused with different content') from None
    except Capacity:raise HTTPException(429,'Job quota reached',headers={'Retry-After':'60'}) from None
    except ValueError:raise HTTPException(422,'Invalid job input') from None
    except sqlite3.Error:raise HTTPException(503,'Job store unavailable') from None

@router.post('/v1/me/audio-jobs',status_code=202)
async def create_job(request:Request):
    store,token=queue_access(request)
    if request.headers.get('x-audio-consent')!='true' or request.headers.get('x-job-storage-consent')!='true':
        raise HTTPException(403,'Analysis and temporary media-storage consent required')
    if request.headers.get('x-audio-species')!='dog':raise HTTPException(422,'Only dog observations supported')
    if request.headers.get('content-type')!='audio/wav':raise HTTPException(415,'Expected audio/wav')
    key=request.headers.get('idempotency-key','');pet_id=request.headers.get('x-petsense-pet-id','')
    if not re.fullmatch(r'[A-Za-z0-9._-]{16,128}',key) or len(pet_id)!=36:raise HTTPException(422,'Job key and dog profile required')
    admission=request.app.state.audio_admission
    try:admission.enter()
    except ValueError:raise HTTPException(429,'Upload busy',headers={'Retry-After':'1'}) from None
    try:
        body=bytearray()
        try:
            async with asyncio.timeout(15):
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body)>MAX_BYTES:raise HTTPException(413,'Audio too large')
            read_wav_bytes(bytes(body))
        except TimeoutError:raise HTTPException(408,'Audio upload deadline exceeded') from None
        except (ValueError,ClientDisconnect):raise HTTPException(422,'Invalid bounded PCM16 WAV') from None
        return operation(store.enqueue,token,pet_id,key,bytes(body))
    finally:admission.leave()

@router.get('/v1/me/audio-jobs')
async def list_jobs(request:Request):
    store,token=queue_access(request)
    return {'items':operation(store.list_jobs,token),'raw_retention_seconds':900,'result_retention_seconds':86400}

@router.get('/v1/me/audio-jobs/{job_id}')
async def get_job(job_id:str,request:Request):
    store,token=queue_access(request)
    return operation(store.get,token,job_id)

@router.delete('/v1/me/audio-jobs/{job_id}')
async def cancel_job(job_id:str,request:Request):
    store,token=queue_access(request)
    if request.headers.get('x-delete-confirm')!='cancel-job':raise HTTPException(400,'Cancellation confirmation required')
    return operation(store.cancel,token,job_id)
