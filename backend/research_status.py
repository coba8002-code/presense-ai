"""Authenticated read-only discovery status; never starts providers or approves data."""
import os
from pathlib import Path
import sqlite3
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from backend.accounts import access
from knowledge.source_automation import status

router = APIRouter()

@router.get('/v1/me/research-status')
async def research_status(request: Request):
    access(request)
    path = os.getenv('PETSENSE_KNOWLEDGE_DB', '')
    if not path:
        return JSONResponse({'configured': False, 'status': 'not_configured', 'links': [], 'training_ready': False}, headers={'Cache-Control': 'no-store'})
    try:
        with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=2) as db:
            report = status(db)
    except (OSError, ValueError, sqlite3.Error):
        raise HTTPException(503, 'Discovery status unavailable') from None
    return JSONResponse({'configured': True, **report}, headers={'Cache-Control': 'no-store'})
