"""Run official link discovery, knowledge updates and optional local audio jobs."""
import argparse
import json
import os
from pathlib import Path
import time
import sqlite3
import httpx
from knowledge.models import Config
from knowledge.providers import Providers
from knowledge.pipeline import open_db, cycle, search


def load_config(path):
    path = Path(path)
    if path.stat().st_size > 128000:
        raise ValueError('Configuration too large')
    return Config.model_validate_json(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--db', default='data/knowledge.sqlite3')
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--query')
    parser.add_argument('--discover-only', action='store_true', help='Find metadata without Gemini or Notebook calls')
    parser.add_argument('--candidates', action='store_true', help='List local candidate review status without API calls')
    parser.add_argument('--audio-inbox', help='Optional existing rights-reviewed local audio job queue')
    parser.add_argument('--audio-output', default='artifacts/autolearn')
    args = parser.parse_args()
    try:
        with httpx.Client() as client:
            db = open_db(args.db)
            try:
                while True:
                    cfg = load_config(args.config)  # Rights revocation takes effect next cycle/read.
                    if args.candidates:
                        from knowledge.candidates import candidates
                        print(json.dumps(candidates(db,cfg),ensure_ascii=False))
                        return
                    if args.query is not None:
                        print(json.dumps(search(db,cfg,args.query),ensure_ascii=False))
                        return
                    provider = Providers(cfg, client, os.environ)
                    # Fail before any external call; keys never appear in output.
                    provider.credential('YOUTUBE_API_KEY')
                    if not args.discover_only:
                        provider.credential('GEMINI_API_KEY')
                    if cfg.notebook and not args.discover_only:
                        provider.credential('GOOGLE_ACCESS_TOKEN')
                    result = cycle(db,cfg,provider,discovery_only=args.discover_only)
                    if args.audio_inbox:
                        from training.autolearn import scan
                        result['local_audio_jobs'] = scan(args.audio_inbox,args.audio_output)
                    print(json.dumps(result,ensure_ascii=False,allow_nan=False),flush=True)
                    if not args.watch:
                        if result['errors'] or result['notebook_uncertain']:
                            raise SystemExit(2)
                        return
                    time.sleep(cfg.interval_seconds)
            finally:
                db.close()
    except KeyboardInterrupt:
        pass
    except (ValueError,OSError,sqlite3.Error):
        # Validation errors can echo input values; keep CLI output generic.
        parser.exit(2, 'Knowledge worker blocked: check configuration, credentials and local storage.\n')


if __name__ == '__main__':
    main()
