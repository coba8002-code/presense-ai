"""Authenticated local source retrieval; this route never calls an external API."""
from contextlib import closing
import os
from pathlib import Path
import secrets
import sqlite3
from fastapi import APIRouter, HTTPException, Query, Request
from knowledge.worker import load_config
from knowledge.pipeline import search

router = APIRouter()


@router.get('/v1/knowledge/search')
async def knowledge_search(request: Request, q: str = Query(min_length=1,max_length=200)):
    token = os.getenv('PETSENSE_API_TOKEN','')
    if not token:
        raise HTTPException(503,'Knowledge retrieval is not configured')
    if not secrets.compare_digest(request.headers.get('authorization',''), 'Bearer '+token):
        raise HTTPException(401,'Authentication required')
    path = os.getenv('PETSENSE_KNOWLEDGE_DB','')
    config = os.getenv('PETSENSE_KNOWLEDGE_CONFIG','')
    if not path or not config:
        raise HTTPException(503,'Knowledge retrieval is not configured')
    try:
        cfg = load_config(config)
        # URI quoting via as_uri avoids interpreting a filename as query parameters.
        with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory = sqlite3.Row
            hits = search(db,cfg,q)
    except (OSError,ValueError,sqlite3.Error):
        raise HTTPException(503,'Knowledge retrieval unavailable') from None
    return {'matches':hits,'abstained':not hits,
            'notice':'Source-linked machine extractions, not verified behavioral advice or trained model weights.'}
