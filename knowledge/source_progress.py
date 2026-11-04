"""Read-only source readiness and private review packets, never inferred approvals."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import time
from knowledge.models import Analysis
from knowledge.pipeline import policy_for

REMAINING = ['training_rights', 'independent_reviewed_labels', 'authorized_local_media',
             'animal_household_source_disjoint_evaluation']

def progress(db, config=None, now=None):
    now = time.time() if now is None else now
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'research_links' not in tables:
        return {}
    cursor = db.cursor()
    cursor.row_factory = sqlite3.Row
    result = {}
    for (video_id,) in db.execute('SELECT id FROM research_links WHERE expires>? ORDER BY id LIMIT 100', (now,)):
        row = cursor.execute('SELECT * FROM videos WHERE id=?', (video_id,)).fetchone() if 'videos' in tables else None
        state, count = 'metadata_missing', 0
        if row:
            if now-row['verified'] >= 86400 or not 0 < row['verified'] <= now:
                state = 'metadata_stale'
            elif config is None:
                state = 'policy_unavailable'
            elif not all(policy_for(config, row['channel_id'], now, capability)
                         for capability in ('analysis_allowed', 'knowledge_allowed')):
                state = 'permission_required'
            elif not row['analysis'] or row['analyzed'] is None:
                state = 'awaiting_analysis'
            elif row['model'] != config.gemini_model:
                state = 'model_changed'
            elif not row['analyzed'] <= now or now-row['analyzed'] >= config.retention_days*86400:
                state = 'analysis_stale'
            else:
                try:
                    analysis = Analysis.model_validate_json(row['analysis'])
                    if any(e.end_seconds > row['duration'] for e in analysis.entries):
                        raise ValueError('Out-of-range evidence')
                    if analysis.species != 'dog':
                        state = 'unsupported_species'
                    elif not analysis.entries:
                        state = 'evidence_invalid'
                    else:
                        state = 'machine_extracted_unreviewed'
                        count = sum(e.kind == 'observation' and e.end_seconds > e.start_seconds for e in analysis.entries)
                except ValueError:
                    state = 'evidence_invalid'
        result[video_id] = {'analysis_status': state, 'proposal_count': count,
                            'training_ready': False, 'remaining_training_requirements': REMAINING.copy()}
    return result

def packet(db, config=None, now=None):
    now = time.time() if now is None else now
    states = progress(db, config, now)
    current = []
    if config is not None and any(v['analysis_status'] == 'machine_extracted_unreviewed' for v in states.values()):
        from training.video_review import proposals
        original = db.row_factory
        try:
            db.row_factory = sqlite3.Row
            current = [p for p in proposals(db, config, now)
                       if states.get(p['source_id'], {}).get('analysis_status') == 'machine_extracted_unreviewed']
        finally:
            db.row_factory = original
    return {'schema_version': 1, 'generated_at': now, 'training_ready': False,
            'sources': states, 'proposals': current,
            'review_template': {k: None for k in ('proposal_id', 'decision', 'label', 'animal_id',
                'recording_group', 'dataset', 'split', 'reviewer', 'review_evidence', 'reviewed_at')},
            'notice': 'Unreviewed machine observations only. Fill nothing automatically; this packet cannot approve training.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        config = None
        if args.config:
            from knowledge.worker import load_config
            config = load_config(args.config)
        with closing(sqlite3.connect(args.db.resolve().as_uri()+'?mode=ro', uri=True)) as db:
            result = packet(db, config)
        # Private local export, exclusive creation; no overwrite, network or media.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print(json.dumps({'sources': len(result['sources']), 'proposals': len(result['proposals']), 'training_ready': False}))
    except (ValueError, OSError, sqlite3.Error):
        parser.exit(2, 'Review export blocked: check local DB, policy configuration and fresh evidence.\n')

if __name__ == '__main__':
    main()
