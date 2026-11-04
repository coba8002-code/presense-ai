"""Explicit development-token or owner-session authorization for audio requests."""
import os
from backend.credential_compare import credential_matches
from fastapi import HTTPException
from backend.accounts import access


def authorize(request):
    if os.getenv('PETSENSE_REQUIRE_ACCOUNT','false').lower()=='true' or os.getenv('PETSENSE_ENABLE_WEB_AUTH','false').lower()=='true':
        _,owner,_=access(request)
        return owner
    token=os.getenv('PETSENSE_API_TOKEN','')
    if not token:raise HTTPException(503,'Audio event scoring is not configured')
    if not credential_matches(request.headers.get('authorization',''),f'Bearer {token}'):
        raise HTTPException(401,'Authentication required')
    return None


def revalidate(request,owner):
    if owner is not None:
        _,current,_=access(request)
        if current!=owner:raise HTTPException(401,'Account session changed')
