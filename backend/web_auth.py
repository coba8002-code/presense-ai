"""Opt-in first-party beta membership. Email is an unverified login identifier."""
import asyncio
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import JSONResponse,Response
from pydantic import BaseModel,ConfigDict,Field,ValidationError,field_validator
from starlette.requests import ClientDisconnect
from backend.accounts import access
from backend.auth_store import AuthStore,AuthLimit,AuthBusy,SESSION_TTL,email_value,password_value
from backend.web_security import COOKIE,settings,transport,origin,csrf_value

router=APIRouter()

class Credentials(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    email:str=Field(max_length=254)
    password:str=Field(min_length=15,max_length=128)
    @field_validator('email')
    @classmethod
    def email_check(cls,value):return email_value(value)
    @field_validator('password')
    @classmethod
    def password_check(cls,value):return password_value(value)

class Signup(Credentials):
    accept_terms:bool
    accept_privacy:bool
    terms_version:str=Field(min_length=1,max_length=100)
    privacy_version:str=Field(min_length=1,max_length=100)

class Recover(Credentials):
    recovery_code:str=Field(pattern=r'^[A-Za-z0-9_-]{43}$')

class Password(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    password:str=Field(min_length=15,max_length=128)
    @field_validator('password')
    @classmethod
    def check(cls,value):return password_value(value)

class Change(Password):
    new_password:str=Field(min_length=15,max_length=128)
    @field_validator('new_password')
    @classmethod
    def new_check(cls,value):return password_value(value)

def configured(request,write=False):
    config=settings()
    if config is None:raise HTTPException(503,'Web accounts disabled')
    transport(request,config)
    if write:
        origin(request,config)
        if request.headers.get('x-petsense-request')!='web':raise HTTPException(403,'Explicit web request required')
    return config

def store():
    path=os.getenv('PETSENSE_ACCOUNT_DB','')
    if not path:raise HTTPException(503,'Account store not configured')
    try:return AuthStore(path)
    except (OSError,sqlite3.Error):raise HTTPException(503,'Account store unavailable') from None

async def payload(request,model):
    data=bytearray()
    try:
        async with asyncio.timeout(10):
            async for chunk in request.stream():
                data.extend(chunk)
                if len(data)>4096:raise HTTPException(413,'Account request too large')
        if request.headers.get('content-type','').split(';')[0]!='application/json':raise HTTPException(415,'Expected application/json')
        return model.model_validate_json(data)
    except TimeoutError:raise HTTPException(408,'Account upload deadline exceeded') from None
    except (ValidationError,ClientDisconnect):raise HTTPException(422,'Invalid account fields') from None

async def password_action(db,request,email,kind,fn):
    try:lease=db.reserve(request.client.host if request.client else 'unknown',email,kind)
    except AuthBusy:raise HTTPException(429,'Password service busy',headers={'Retry-After':'1'}) from None
    except AuthLimit:raise HTTPException(429,'Account request limit reached',headers={'Retry-After':'900'}) from None
    except sqlite3.Error:raise HTTPException(503,'Account service unavailable') from None
    pool=None
    try:
        pool=ThreadPoolExecutor(max_workers=1)
        work=pool.submit(fn)
        while not work.done():await asyncio.sleep(.02)
        return work.result()
    except PermissionError:raise HTTPException(401,'Invalid or expired account credentials') from None
    except sqlite3.Error:raise HTTPException(503,'Account service unavailable') from None
    finally:
        # Keep the DB lease until an already-started KDF finishes, even on cancellation.
        if pool is not None:pool.shutdown(wait=True,cancel_futures=False)
        db.release(lease)

def response_with_session(token,data,status_code=200):
    response=JSONResponse(data,status_code=status_code)
    response.set_cookie(COOKIE,token,max_age=SESSION_TTL,path='/',secure=True,httponly=True,samesite='strict')
    return response

def clear_cookie(response):
    response.delete_cookie(COOKIE,path='/',secure=True,httponly=True,samesite='strict')
    return response

def member_access(request):
    _,_,token=access(request);db=store()
    try:member=db.member(token)
    except PermissionError:raise HTTPException(401,'Web login required') from None
    return db,token,member

@router.get('/v1/auth/config')
async def config(request:Request):
    config=settings()
    if config is None:return {'enabled':False}
    transport(request,config)
    return {'enabled':True,**config,'email_verified':False,'recovery_method':'one_time_offline_code',
        'audio_jobs_enabled':os.getenv('PETSENSE_ENABLE_AST_JOBS','false').lower()=='true'}

@router.post('/v1/auth/signup')
async def signup(request:Request):
    config=configured(request,True);data=await payload(request,Signup)
    if not data.accept_terms or not data.accept_privacy:raise HTTPException(403,'Terms and privacy consent required')
    if data.terms_version!=config['terms_version'] or data.privacy_version!=config['privacy_version']:raise HTTPException(409,'Policy version changed; reload before consenting')
    db=store()
    try:member=await password_action(db,request,data.email,'signup',lambda:db.register(data.email,data.password,config['terms_version'],config['privacy_version']))
    except ValueError:raise HTTPException(409,'Account registration unavailable; check existing login') from None
    return response_with_session(member['token'],{'recovery_code':member['recovery_code'],'email_verified':False},201)

@router.post('/v1/auth/login')
async def login(request:Request):
    configured(request,True);data=await payload(request,Credentials);db=store()
    _,token=await password_action(db,request,data.email,'login',lambda:db.login(data.email,data.password))
    return response_with_session(token,{'email_verified':False})

@router.get('/v1/auth/session')
async def current_session(request:Request):
    configured(request);db,token,member=member_access(request)
    return {**member,'csrf_token':csrf_value(token)}

@router.post('/v1/auth/logout',status_code=204)
async def logout(request:Request):
    configured(request,True);db,token,_=member_access(request);db.logout(token)
    return clear_cookie(Response(status_code=204))

@router.post('/v1/auth/recover')
async def recover(request:Request):
    configured(request,True);data=await payload(request,Recover);db=store()
    code=await password_action(db,request,data.email,'recover',lambda:db.recover(data.email,data.recovery_code,data.password))
    return clear_cookie(JSONResponse({'recovery_code':code,'login_required':True}))

@router.post('/v1/auth/password')
async def change_password(request:Request):
    configured(request,True);db,token,member=member_access(request);data=await payload(request,Change)
    token,code=await password_action(db,request,member['email'],'change',lambda:db.change(token,data.password,data.new_password))
    return response_with_session(token,{'recovery_code':code})

@router.post('/v1/auth/delete',status_code=204)
async def delete_member(request:Request):
    configured(request,True);db,token,member=member_access(request);data=await payload(request,Password)
    await password_action(db,request,member['email'],'delete',lambda:db.delete_member(token,data.password))
    return clear_cookie(Response(status_code=204))
