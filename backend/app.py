from fastapi import FastAPI, Request

app = FastAPI(title='PetSense AI', version='0.1.0')


@app.get('/healthz')
async def health() -> dict:
    return {'status': 'ok', 'model_ready': False}


@app.post('/v1/vision/observe')
async def vision(request: Request):
    import os
    import secrets
    import httpx
    from fastapi import HTTPException
    from pydantic import ValidationError
    from backend.vlm import VisionInput, observe, VLMError

    if os.getenv('PETSENSE_ENABLE_CLOUD', 'false').lower() != 'true':
        raise HTTPException(503, 'Cloud observation is disabled')
    token = os.getenv('PETSENSE_API_TOKEN', '')
    if not token:
        raise HTTPException(503, 'Cloud observation is not configured')
    if not secrets.compare_digest(request.headers.get('authorization', ''), f'Bearer {token}'):
        raise HTTPException(401, 'Authentication required')
    key, model = os.getenv('OPENAI_API_KEY', ''), os.getenv('PETSENSE_VLM_MODEL', '')
    if not key or not model:
        raise HTTPException(503, 'Cloud observation is not configured')
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 750000:
            raise HTTPException(413, 'Image request too large')
    try:
        payload = VisionInput.model_validate_json(body)
    except ValidationError:
        # Do not echo image data in validation error details.
        raise HTTPException(422, 'Invalid image request') from None
    if not payload.consent:
        raise HTTPException(403, 'Explicit sharing consent required')
    try:
        async with httpx.AsyncClient() as client:
            result = await observe(payload, client, key, model)
    except VLMError:
        raise HTTPException(502, 'Cloud observation unavailable') from None
    return {'observation': result.model_dump(), 'confidence_kind': 'uncalibrated',
            'notice': 'Behavioral observations only; not translation or diagnosis. '
                      'For urgent health concerns, contact a veterinarian.'}


from backend.realtime import Admission, router as realtime_router

app.state.audio_admission = Admission()
app.include_router(realtime_router)

from backend.knowledge import router as knowledge_router

app.include_router(knowledge_router)

from backend.review import router as review_router

app.include_router(review_router)

# Whole-clip research scoring is isolated from the one-second streaming protocol.
import asyncio
from backend.audio_events import router as audio_events_router
app.state.ast_lock = asyncio.Lock()
app.include_router(audio_events_router)

from backend.product_app import router as product_app_router
app.include_router(product_app_router)

from backend.accounts import router as accounts_router
app.include_router(accounts_router)
from backend.pets import router as pets_router
app.include_router(pets_router)

@app.middleware('http')
async def private_account_responses(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/v1/me/'):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
    return response
