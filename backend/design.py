"""Offline service GUI prototype; no signup or provider API connection."""
from pathlib import Path
from fastapi import APIRouter,HTTPException
from fastapi.responses import Response

router=APIRouter()
FILES={'':('index.html','text/html'),'design.css':('design.css','text/css'),'design.js':('design.js','text/javascript')}

def serve(name):
    if name not in FILES:raise HTTPException(404,'Not found')
    filename,mime=FILES[name]
    return Response((Path(__file__).parent/'static/design'/filename).read_text(),media_type=mime,headers={
        'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
        'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        'Permissions-Policy':'microphone=(), camera=(), geolocation=()'})

@router.get('/design')
async def page():return serve('')

@router.get('/design/{name}')
async def asset(name:str):return serve(name)
