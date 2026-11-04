"""Consented plan API; completed means guardian-confirmed with a linked followup."""
import sqlite3
from typing import Literal
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field,AwareDatetime,field_validator,model_validator
from datetime import timezone
from backend.accounts import access
from backend.journal import payload,operation
from backend.plan_store import PlanStore
router=APIRouter()
CONSENT='care-plan-storage-v1'
class PlanInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    case_id:str=Field(min_length=36,max_length=36)
    goal:str=Field(min_length=1,max_length=200)
    due_at:AwareDatetime
    @field_validator('goal')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('Goal required')
        return value.strip()
    @field_validator('due_at')
    @classmethod
    def utc(cls,value):return value.astimezone(timezone.utc)
class Transition(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    status:Literal['completed','cancelled']
    followup_id:str|None=Field(default=None,max_length=36)
    @model_validator(mode='after')
    def matching(self):
        if (self.status=='completed' and not self.followup_id) or (self.status=='cancelled' and self.followup_id is not None):raise ValueError('Followup required only for completion')
        return self

def account(request):
    store,_,token=access(request)
    try:return PlanStore(store.path),token
    except (OSError,sqlite3.Error):raise HTTPException(503,'Plans unavailable') from None

@router.get('/v1/me/care-plans')
async def listing(request:Request,case_id:str):
    store,token=account(request)
    return {'items':operation(store.list_plans,token,case_id)}
@router.post('/v1/me/care-plans',status_code=201)
async def create(request:Request):
    store,token=account(request);data=await payload(request,PlanInput,CONSENT)
    return operation(store.create_plan,token,data,request.headers.get('idempotency-key',''))
@router.patch('/v1/me/care-plans/{plan_id}')
async def transition(plan_id:str,request:Request):
    store,token=account(request);data=await payload(request,Transition,CONSENT)
    return operation(store.transition,token,plan_id,data)
@router.delete('/v1/me/care-plans/{plan_id}',status_code=204)
async def delete(plan_id:str,request:Request):
    store,token=account(request)
    if request.headers.get('x-delete-confirm')!='delete-plan':raise HTTPException(400,'Plan deletion confirmation required')
    operation(store.delete_plan,token,plan_id)
