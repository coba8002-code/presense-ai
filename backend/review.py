"""Local review UI assets only; no media upload or annotation persistence."""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router=APIRouter()
ASSETS={'':('index.html','text/html'),'review.js':('review.js','text/javascript'),
        'review.css':('review.css','text/css')}


def asset(name):
    if name not in ASSETS:
        raise HTTPException(404,'Not found')
    filename,mime=ASSETS[name]
    return Response((Path(__file__).parent/'static'/'review'/filename).read_text(),media_type=mime,
        headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
            'Referrer-Policy':'no-referrer',
            'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; media-src blob:; connect-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
            'Permissions-Policy':'camera=(), microphone=()'})


@router.get('/review')
async def review_page():
    return asset('')


@router.get('/review/{name}')
async def review_asset(name:str):
    return asset(name)
