"""Opt-in local/company OpenAI-compatible VLM transport; never cloud fallback."""
import asyncio
import base64
from dataclasses import dataclass,field
import ipaddress
import json
from urllib.parse import urlsplit
import httpx
from backend.vlm import VisionInput,VisionResult,VLMError,SYSTEM

@dataclass(frozen=True)
class LocalConfig:
    base_url:str
    model:str
    api_key:str=field(default='',repr=False)
    def __post_init__(self):
        parsed=urlsplit(self.base_url)
        try:loopback=ipaddress.ip_address(parsed.hostname or '').is_loopback
        except ValueError:loopback=parsed.hostname=='localhost'
        if parsed.scheme not in ('http','https') or not parsed.hostname or (parsed.scheme=='http' and not loopback) or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path.rstrip('/')!='/v1' or any(c.isspace() for c in self.base_url):raise ValueError('Invalid local server configuration')
        parsed.port
        if not self.model.strip() or len(self.model)>200 or any(ord(c)<32 for c in self.model+self.api_key):raise ValueError('Invalid model configuration')
        object.__setattr__(self,'base_url',self.base_url.rstrip('/'))

async def observe_local(payload:VisionInput,client:httpx.AsyncClient,config:LocalConfig,deadline=20):
    if not payload.consent:raise VLMError('Explicit local sharing consent required')
    raw=base64.b64decode(payload.image_base64);mime='image/png' if raw.startswith(b'\x89PNG') else 'image/jpeg'
    body={'model':config.model,'stream':False,'max_tokens':600,'temperature':0,
        'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':[{'type':'image_url','image_url':{'url':f'data:{mime};base64,{payload.image_base64}'}}]}],
        'response_format':{'type':'json_schema','json_schema':{'name':'pet_observation','strict':True,'schema':VisionResult.model_json_schema()}}}
    headers={'Authorization':'Bearer '+config.api_key} if config.api_key else {}
    try:
        async with asyncio.timeout(deadline):
            async with client.stream('POST',config.base_url+'/chat/completions',json=body,headers=headers,timeout=deadline,follow_redirects=False) as response:
                if response.status_code!=200:raise VLMError('Local observation unavailable')
                content=bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content)>64000:raise VLMError('Local observation unavailable')
        message=json.loads(content)['choices'][0]['message']
        if not isinstance(message,dict):raise VLMError('Local observation unavailable')
        if message.get('refusal') or message.get('tool_calls'):raise VLMError('Local observation unavailable')
        result=VisionResult.model_validate_json(message['content'])
    except (httpx.HTTPError,TimeoutError,ValueError,KeyError,IndexError,TypeError):
        raise VLMError('Local observation unavailable') from None
    if result.species!='dog':
        result.posture='unknown';result.ears='unknown';result.tail='unknown';result.hypotheses=['insufficient_context'];result.abstained=True
    if result.confidence<.6 or result.visibility=='unclear':result.abstained=True
    return result
