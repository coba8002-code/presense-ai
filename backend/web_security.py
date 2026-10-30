"""Fixed-origin HTTPS cookies and session-bound CSRF for first-party beta accounts."""
import hashlib
import os
import re
import secrets
from urllib.parse import urlsplit
from fastapi import HTTPException
from backend.auth_store import email_value

COOKIE='__Host-petsense_session'

def enabled():return os.getenv('PETSENSE_ENABLE_WEB_AUTH','false').lower()=='true'

def settings():
    if not enabled():return None
    try:
        origin=os.environ['PETSENSE_PUBLIC_ORIGIN'].rstrip('/')
        parsed=urlsplit(origin)
        if (len(origin)>300 or parsed.scheme!='https' or not parsed.hostname or parsed.path or parsed.query or parsed.fragment
            or parsed.username or parsed.password or any(c.isspace() for c in origin)):raise ValueError('Invalid origin')
        parsed.port
        origin='https://'+parsed.netloc.lower()
        operator=os.environ['PETSENSE_OPERATOR_NAME'].strip();contact=email_value(os.environ['PETSENSE_PRIVACY_CONTACT'])
        terms=os.environ['PETSENSE_TERMS_VERSION'].strip();privacy=os.environ['PETSENSE_PRIVACY_VERSION'].strip()
        if any(not value or len(value)>100 for value in [operator,terms,privacy]):raise ValueError('Operator and versions required')
        return {'origin':origin,'operator':operator,'contact':contact,'terms_version':terms,'privacy_version':privacy}
    except (KeyError,ValueError):raise HTTPException(503,'Web account configuration incomplete') from None

def transport(request,config):
    if request.url.scheme!='https' or urlsplit(str(request.url)).netloc.lower()!=urlsplit(config['origin']).netloc:
        raise HTTPException(403,'Configured HTTPS origin required')

def origin(request,config):
    transport(request,config)
    if request.headers.get('origin')!=config['origin']:raise HTTPException(403,'Same-origin request required')

def csrf_value(token):return hashlib.sha256(('PetSense-CSRF-v1\0'+token).encode()).hexdigest()

def session_token(request):
    header=request.headers.get('x-petsense-session','')
    if not enabled():return header
    config=settings();cookie=request.cookies.get(COOKIE,'')
    if cookie or header:transport(request,config)
    if cookie:
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',cookie):raise HTTPException(401,'Invalid session')
        if header and not secrets.compare_digest(header,cookie):raise HTTPException(401,'Conflicting credentials')
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin(request,config)
            if not secrets.compare_digest(request.headers.get('x-petsense-csrf',''),csrf_value(cookie)):
                raise HTTPException(403,'CSRF verification failed')
        return cookie
    return header
