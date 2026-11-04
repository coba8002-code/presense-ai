"""Read-only OpenAI-compatible server discovery on the machine running this CLI."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
import httpx

DEFAULTS=('http://127.0.0.1:1234/v1','http://127.0.0.1:11434/v1')

def validate_url(value):
    parsed=urlsplit(value)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path.rstrip('/')!='/v1' or any(c.isspace() for c in value):raise ValueError('Expected a credential-free HTTP(S) /v1 base URL')
    parsed.port
    return value.rstrip('/')

def probe(base_url,client):
    base_url=validate_url(base_url)
    result={'base_url':base_url,'status':'unreachable','model_ids':[],'inference_tested':False,'vision_verified':False,'training_performed':False}
    try:
        with client.stream('GET',base_url+'/models',timeout=3,follow_redirects=False) as response:
            if response.status_code in (401,403):return {**result,'status':'authentication_required'}
            if 300<=response.status_code<400:return {**result,'status':'redirect_refused'}
            if response.status_code!=200:return {**result,'status':'http_error','http_status':response.status_code}
            body=bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body)>65536:return {**result,'status':'response_too_large'}
            data=json.loads(body)
            if not isinstance(data,dict) or not isinstance(data.get('data'),list):raise ValueError('Invalid model list')
            ids=[]
            for row in data['data'][:20]:
                if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not 0<len(row['id'])<=200:raise ValueError('Invalid model identifier')
                ids.append(row['id'])
            return {**result,'status':'models_available' if ids else 'no_models','model_ids':ids,'models_truncated':len(data['data'])>20}
    except httpx.HTTPError:return result
    except (ValueError,TypeError):return {**result,'status':'incompatible_response'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',action='append',help='Explicit server /v1 URL; defaults only to LM Studio/Ollama loopback ports')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        urls=[validate_url(url) for url in (args.base_url or DEFAULTS)]
        if len(urls)>5 or (args.output and args.output.exists()):raise ValueError('Use at most five addresses and a fresh output file')
    except ValueError:parser.exit(2,'Invalid server URL or output. Do not put passwords or tokens in URLs.\n')
    with httpx.Client() as client:results=[probe(url,client) for url in urls]
    report={'scope':'Only the machine executing this CLI; loopback does not refer to a different PC','checks':results,'private_media_sent':False,'network_scan_performed':False}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x',encoding='utf-8') as out:json.dump(report,out,ensure_ascii=False,indent=2)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if any(r['status']=='models_available' for r in results) else 2
if __name__=='__main__':raise SystemExit(main())
