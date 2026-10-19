"""Read-only candidate inventory; inferred evidence never grants training rights."""
import time
import json
from knowledge.pipeline import policy_for
from knowledge.providers import canonical


def candidates(db, config, now=None):
    now = time.time() if now is None else now
    result = []
    for row in db.execute('SELECT * FROM videos ORDER BY created, id LIMIT 500'):
        allowed = all(policy_for(config,row['channel_id'],now,capability)
                      for capability in ('analysis_allowed','knowledge_allowed'))
        if row['analysis'] and json.loads(row['analysis']).get('species') != 'dog':
            status = 'unsupported_species'
        elif now-row['verified'] >= 86400:
            status = 'metadata_refresh_required'
        elif not allowed:
            status = 'rights_review_required'
        elif (not row['analysis'] or row['model'] != config.gemini_model
              or now-(row['analyzed'] or 0) >= config.retention_days*86400):
            status = 'awaiting_analysis'
        else:
            status = 'expert_review_required'
        result.append(dict(source_id=row['id'],url=canonical(row['id']),
            channel_id=row['channel_id'],title=row['title'],status=status,
            training_ready=False,
            remaining_training_requirements=['training_rights','expert_labels',
                'authorized_media_access','animal_disjoint_evaluation']))
    return result
