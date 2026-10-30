from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
router=APIRouter()
FILES={'':('index.html','text/html'),'app.js':('app.js','text/javascript'),'app.css':('app.css','text/css'),'audio.js':('audio.js','text/javascript'),'notes.js':('notes.js','text/javascript'),'profiles.js':('profiles.js','text/javascript')}

def serve(name):
    if name not in FILES:raise HTTPException(404,'Not found')
    file,mime=FILES[name]
    return Response((Path(__file__).parent/'static/app'/file).read_text(),media_type=mime,headers={
        'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
        'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        'Referrer-Policy':'no-referrer','Permissions-Policy':'microphone=(self), camera=()'})
@router.get('/app')
async def page():return serve('')
@router.get('/app/{name}')
async def asset(name:str):return serve(name)
