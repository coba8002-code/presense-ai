"""Consent-bound read-only journal sharing; invitation secrets stay in POST bodies."""
import sqlite3
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
from backend.accounts import access
from backend.journal import payload,operation
from backend.care_store import CareStore

router=APIRouter()
CONSENT='care-sharing-v1'
class Invite(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    pet_id:str=Field(pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
    days:Literal[1,7]=1
class Accept(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    code:str=Field(min_length=43,max_length=43)

def account(request):
    store,_,token=access(request)
    try:return CareStore(store.path),token
    except (OSError,sqlite3.Error):raise HTTPException(503,'Sharing unavailable') from None

@router.get('/v1/me/care-shares')
async def listing(request:Request):
    store,token=account(request)
    return operation(store.list_shares,token)

@router.post('/v1/me/care-shares',status_code=201)
async def invite(request:Request):
    store,token=account(request);data=await payload(request,Invite,CONSENT)
    return operation(store.invite,token,data.pet_id,data.days)

@router.post('/v1/me/care-shares/accept')
async def accept(request:Request):
    store,token=account(request);data=await payload(request,Accept,CONSENT)
    return operation(store.accept,token,data.code)

@router.delete('/v1/me/care-shares/{share_id}',status_code=204)
async def revoke(share_id:str,request:Request):
    store,token=account(request)
    if request.headers.get('x-delete-confirm')!='leave-or-revoke':raise HTTPException(400,'Sharing confirmation required')
    operation(store.revoke,token,share_id)

@router.get('/v1/me/care-shares/{share_id}/journal')
async def journal(share_id:str,request:Request,offset:int=0):
    store,token=account(request)
    return operation(store.shared_cases,token,share_id,offset)

@router.get('/v1/me/care-shares/{share_id}/journal/{case_id}')
async def detail(share_id:str,case_id:str,request:Request):
    store,token=account(request)
    return operation(store.shared_case,token,share_id,case_id)
