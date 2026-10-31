"""Bounded, consented journal API for guardian observations and followups."""
import asyncio
from datetime import timezone
import sqlite3
from typing import Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import AwareDatetime,BaseModel,ConfigDict,Field,ValidationError,field_validator
from starlette.requests import ClientDisconnect
from backend.accounts import access
from backend.journal_store import CONSENT,JournalStore,JournalConflict,JournalLimit

router=APIRouter()


class TimedInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    observed_at:AwareDatetime

    @field_validator('observed_at')
    @classmethod
    def utc(cls,value):return value.astimezone(timezone.utc)


class CaseInput(TimedInput):
    pet_id:str=Field(pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
    behavior:Literal['barking','whining','pacing','avoidance','jumping','other']
    before:str=Field(default='',max_length=80)
    during:str=Field(default='',max_length=80)
    after:str=Field(default='',max_length=80)
    duration:Literal['unknown','short','medium','long']='unknown'
    change:Literal['unknown','yes','no']='unknown'
    dogs:Literal['unknown','one','multiple']='unknown'
    health_concern:bool=False
    retention_days:Literal[30,90]=30


class FollowupInput(TimedInput):
    action:Literal['observe','give_space','quiet_break','play','consulted_professional','other']
    what_done:str=Field(min_length=1,max_length=300)
    outcome:Literal['unknown','unchanged','settled','more_active','stopped','concern_increased']='unknown'
    note:str=Field(default='',max_length=300)

    @field_validator('what_done')
    @classmethod
    def required(cls,value):
        if not value.strip():raise ValueError('Description required')
        return value.strip()


async def payload(request,model,consent=CONSENT):
    if request.headers.get('x-journal-consent')!=consent:raise HTTPException(403,'Explicit journal storage consent required')
    raw=bytearray()
    try:
        async with asyncio.timeout(15):
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw)>4096:raise HTTPException(413,'Journal request too large')
        if request.headers.get('content-type','').split(';')[0]!='application/json':raise HTTPException(415,'Expected application/json')
        return model.model_validate_json(raw)
    except TimeoutError:raise HTTPException(408,'Upload deadline exceeded') from None
    except (ValidationError,ClientDisconnect):raise HTTPException(422,'Invalid journal fields') from None


def account(request):
    store,_,token=access(request)
    try:return JournalStore(store.path),token
    except (OSError,sqlite3.Error):raise HTTPException(503,'Journal store unavailable') from None


def operation(fn,*args):
    try:return fn(*args)
    except PermissionError:raise HTTPException(401,'Session expired or revoked') from None
    except KeyError:raise HTTPException(404,'Journal or dog not found') from None
    except JournalConflict:raise HTTPException(409,'Idempotency content changed') from None
    except JournalLimit:raise HTTPException(409,'Journal storage limit reached') from None
    except ValueError:raise HTTPException(422,'Invalid journal fields or time') from None
    except sqlite3.Error:raise HTTPException(503,'Journal store unavailable') from None


@router.post('/v1/me/journal',status_code=201)
async def create(request:Request):
    store,token=account(request);data=await payload(request,CaseInput)
    return operation(store.create_case,token,data,request.headers.get('idempotency-key',''))


@router.get('/v1/me/journal')
async def listing(request:Request,pet_id:str|None=None,offset:int=0):
    store,token=account(request)
    return operation(store.list_cases,token,pet_id,offset)


@router.get('/v1/me/journal/summary')
async def summary(request:Request,pet_id:str,days:int=7):
    store,token=account(request)
    return operation(store.summary,token,pet_id,days)


@router.get('/v1/me/journal/report')
async def report(request:Request,pet_id:str,days:int=7):
    from backend.consultation_report import build_report
    store,token=account(request)
    return operation(build_report,store,token,pet_id,days)


@router.get('/v1/me/journal/{case_id}')
async def detail(case_id:str,request:Request):
    store,token=account(request)
    return operation(store.get_case,token,case_id)


@router.post('/v1/me/journal/{case_id}/followups',status_code=201)
async def followup(case_id:str,request:Request):
    store,token=account(request);data=await payload(request,FollowupInput)
    return operation(store.add_followup,token,case_id,data,request.headers.get('idempotency-key',''))


@router.delete('/v1/me/journal/{case_id}',status_code=204)
async def delete(case_id:str,request:Request):
    store,token=account(request)
    if request.headers.get('x-delete-confirm')!='delete-case':raise HTTPException(400,'Journal deletion confirmation required')
    operation(store.delete_case,token,case_id)
