"""Run pinned AST in a private child process with bounded stdin/stdout and a deadline."""
import asyncio
import hashlib
import json
import math
import os
import signal
import sys
from pathlib import Path
from training.pretrained_audio import DOG_LABELS,MAX_BYTES,MODEL,REVISION

MAX_OUTPUT=64000
class WorkerError(RuntimeError):pass
class WorkerTimeout(WorkerError):pass

def worker_command():return [sys.executable,'-m','backend.audio_worker']

def validate_result(raw,output):
    try:result=json.loads(output)
    except (ValueError,UnicodeError):raise WorkerError('Invalid worker output') from None
    if not isinstance(result,dict):raise WorkerError('Invalid worker result')
    if (result.get('model')!=MODEL or result.get('revision')!=REVISION or result.get('decision')!='abstain'
        or result.get('production_ready') is not False or result.get('species_verified') is not False
        or result.get('input_sha256')!=hashlib.sha256(raw).hexdigest()):raise WorkerError('Worker contract mismatch')
    scores=result.get('dog_event_scores')
    if not isinstance(scores,list) or len(scores)!=7:raise WorkerError('Incomplete dog scores')
    if any(not isinstance(x,dict) or not isinstance(x.get('label'),str) for x in scores):raise WorkerError('Invalid score entries')
    if {x['label'] for x in scores}!=set(DOG_LABELS):raise WorkerError('Unexpected dog labels')
    if any(type(x.get('score')) not in (int,float) or not math.isfinite(x['score']) or not 0<=x['score']<=1 for x in scores):raise WorkerError('Invalid score values')
    return result

async def stop_process(proc):
    if proc.returncode is None:
        try:
            if os.name=='posix':os.killpg(proc.pid,signal.SIGKILL)
            else:proc.kill()
        except ProcessLookupError:pass
    await proc.wait()

async def run_ast(raw,timeout=60):
    if not isinstance(raw,bytes) or not 1<=len(raw)<=MAX_BYTES:raise ValueError('Bounded WAV bytes required')
    if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=300:raise ValueError('Invalid worker deadline')
    env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1'}
    # Do not pass provider/application credentials into the model child.
    for key in list(env):
        if any(marker in key.upper() for marker in ['TOKEN','SECRET','API_KEY','PASSWORD']) or key.startswith('PETSENSE_'):env.pop(key,None)
    proc=None
    try:
        async with asyncio.timeout(timeout):
            proc=await asyncio.create_subprocess_exec(*worker_command(),cwd=Path(__file__).resolve().parents[1],env=env,
                stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,start_new_session=os.name=='posix')
            proc.stdin.write(raw);await proc.stdin.drain();proc.stdin.close()
            output=bytearray()
            while chunk:=await proc.stdout.read(8192):
                output.extend(chunk)
                if len(output)>MAX_OUTPUT:raise WorkerError('Worker output exceeds limit')
            await proc.wait()
            if proc.returncode!=0:raise WorkerError('Local model worker failed')
            return validate_result(raw,bytes(output))
    except TimeoutError:raise WorkerTimeout('Model worker deadline exceeded') from None
    except (OSError,ValueError):
        raise WorkerError('Local worker unavailable') from None
    finally:
        if proc is not None:await stop_process(proc)
