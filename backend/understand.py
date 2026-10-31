"""Bilingual context recording; no inference, external calls or automatic storage."""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter()
HEADERS = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer', 'Permissions-Policy': 'microphone=(), camera=(), geolocation=()',
    'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"}


def asset(name):
    files = {'': ('index.html', 'text/html'), 'case.js': ('case.js', 'text/javascript'),
        'guide.js': ('guide.js', 'text/javascript'), 'journal.js':('journal.js','text/javascript'), 'journal-core.js':('journal-core.js','text/javascript'), 'guide.css': ('guide.css', 'text/css')}
    if name not in files:
        raise HTTPException(404, 'Not found')
    filename, mime = files[name]
    return Response((Path(__file__).parent / 'static/understand' / filename).read_text(),
        media_type=mime, headers=HEADERS)


@router.get('/understand')
async def page():
    return asset('')


@router.get('/understand/{name}')
async def resource(name: str):
    return asset(name)
