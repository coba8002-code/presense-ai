"""Source-linked dog case candidates, never independent references or training grants."""
import time
from knowledge.models import Analysis
from knowledge.pipeline import policy_for
from knowledge.providers import canonical
from training.video_review import digest


def case_cards(db, config, now=None):
    now = time.time() if now is None else now
    cards = []
    for row in db.execute('SELECT * FROM videos WHERE analysis IS NOT NULL ORDER BY id LIMIT 500'):
        if (row['model'] != config.gemini_model or not 0 <= now-row['verified'] < 86400
            or row['analyzed'] is None or not 0 <= now-row['analyzed'] < config.retention_days*86400
            or not policy_for(config, row['channel_id'], now, 'knowledge_allowed')):
            continue
        analysis = Analysis.model_validate_json(row['analysis'])
        if analysis.species != 'dog':continue
        groups = {kind: [] for kind in ('observation', 'speaker_statement', 'hypothesis')}
        for entry in analysis.entries:
            if not 0 <= entry.start_seconds < entry.end_seconds <= row['duration']:continue
            groups[entry.kind].append({**entry.model_dump(),
                'citation': canonical(row['id'])+f'&t={entry.start_seconds}s'})
        if not groups['observation']:continue
        provenance = {'source_id': row['id'], 'channel_id': row['channel_id'],
            'analysis_sha256': digest(analysis.model_dump()), 'model': row['model'], 'analyzed_at': row['analyzed'],
            'metadata_verified_at': row['verified'], 'duration_seconds': row['duration']}
        cards.append({'case_id': digest(provenance), **provenance, 'url': canonical(row['id']),
            'title': row['title'], 'species': 'dog', 'entries': groups,
            'speaker_identity_verified': False, 'expert_statement_verified': False,
            'intervention': None, 'followup_outcome': None, 'animal_id': None, 'household_id': None,
            'audio_confounds': {'commentary': 'unknown', 'music': 'unknown', 'dubbing': 'unknown'},
            'editing_checked': False, 'review_status': 'independent_review_required',
            'ground_truth': False, 'training_ready': False,
            'remaining': ['case and speaker attribution review', 'separate observation from interpretation',
                'editing and natural-vocalization review', 'rights and authorized media',
                'global animal/household/session identities', 'independent evaluation']})
    return cards
