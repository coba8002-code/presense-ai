"""Explicit local AST queue worker; cached offline weights, no paid providers or training."""
import argparse
import asyncio
import os
import signal
import sqlite3
from backend.job_store import JobStore
from backend.audio_process import run_ast,WorkerError,WorkerTimeout

async def once(store):
    claim=store.claim()
    if claim is None:return False
    async def watch():
        while store.keep_running(claim):await asyncio.sleep(.25)
    inference=asyncio.create_task(run_ast(claim['raw'],timeout=60))
    watcher=asyncio.create_task(watch())
    try:
        done,_=await asyncio.wait({inference,watcher},return_when=asyncio.FIRST_COMPLETED)
        if watcher in done:
            await watcher
            return True
        try:store.finish(claim,await inference)
        except WorkerTimeout:store.finish(claim,error='deadline_exceeded')
        except (WorkerError,ValueError):store.finish(claim,error='model_unavailable')
        return True
    except asyncio.CancelledError:
        store.finish(claim,error='worker_lost')
        raise
    finally:
        for task in (inference,watcher):
            if not task.done():task.cancel()
        await asyncio.gather(inference,watcher,return_exceptions=True)

async def serve(store,watch):
    task=asyncio.current_task();loop=asyncio.get_running_loop()
    if hasattr(signal,'SIGTERM'):
        signal.signal(signal.SIGTERM,lambda *_:loop.call_soon_threadsafe(task.cancel))
    while True:
        await once(store)
        if not watch:return
        await asyncio.sleep(1)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',required=True);p.add_argument('--watch',action='store_true')
    args=p.parse_args()
    if os.getenv('PETSENSE_ENABLE_AST_JOBS','false').lower()!='true':p.exit(2,'Audio jobs require explicit enablement.\n')
    try:asyncio.run(serve(JobStore(args.db),args.watch))
    except (KeyboardInterrupt,asyncio.CancelledError):pass
    except (OSError,sqlite3.Error,ValueError):p.exit(2,'Worker unavailable; check private database and pinned model cache.\n')

if __name__=='__main__':main()
