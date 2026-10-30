"""Owner-scoped dog profiles for local operator-issued sessions."""
import asyncio
import sqlite3
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from starlette.requests import ClientDisconnect
from backend.accounts import access

router=APIRouter()

class PetInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    name:str=Field(min_length=1,max_length=40)
    species:Literal['dog']='dog'

    @field_validator('name')
    @classmethod
    def nonempty(cls,value):
        if not value.strip():raise ValueError('Name required')
        return value.strip()

async def payload(request):
    if request.headers.get('x-storage-consent')!='true':raise HTTPException(403,'Explicit storage consent required')
    body=bytearray()
    try:
        async with asyncio.timeout(15):
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body)>4096:raise HTTPException(413,'Profile too large')
        return PetInput.model_validate_json(body)
    except TimeoutError:raise HTTPException(408,'Upload deadline exceeded') from None
    except (ValidationError,ClientDisconnect):raise HTTPException(422,'Invalid dog profile') from None

def operation(fn,*args):
    try:return fn(*args)
    except PermissionError:raise HTTPException(401,'Session expired or revoked') from None
    except KeyError:raise HTTPException(404,'Pet not found') from None
    except ValueError:raise HTTPException(409,'Pet profile limit reached') from None
    except sqlite3.Error:raise HTTPException(503,'Profile store unavailable') from None

@router.get('/v1/me/pets')
async def list_pets(request:Request):
    store,_,token=access(request)
    return {'items':operation(store.pet_list,token),'limit':20,'retention_days':30}

@router.post('/v1/me/pets',status_code=201)
async def create_pet(request:Request):
    store,_,token=access(request);data=await payload(request)
    return operation(store.pet_create,token,data.name)

@router.patch('/v1/me/pets/{pet_id}')
async def update_pet(pet_id:str,request:Request):
    store,_,token=access(request);data=await payload(request)
    return operation(store.pet_update,token,pet_id,data.name)

@router.delete('/v1/me/pets/{pet_id}',status_code=204)
async def delete_pet(pet_id:str,request:Request):
    store,_,token=access(request)
    if request.headers.get('x-delete-confirm')!='delete-pet':raise HTTPException(400,'Pet deletion confirmation required')
    operation(store.pet_delete,token,pet_id)
