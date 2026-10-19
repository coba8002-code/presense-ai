"""Persistent link discovery and evidence retrieval, not model-weight training."""
import fcntl
import json
import re
import sqlite3
import time
from pathlib import Path
from knowledge.providers import canonical


class BudgetExceeded(ValueError):
    pass


def open_db(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE IF NOT EXISTS videos (
          id TEXT PRIMARY KEY, channel_id TEXT NOT NULL, title TEXT NOT NULL,
          duration INTEGER NOT NULL, verified REAL NOT NULL, created REAL NOT NULL,
          analysis TEXT, analyzed REAL, model TEXT, error TEXT, attempted REAL NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS notebooks (
          video_id TEXT PRIMARY KEY, source_id TEXT, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS usage (day INTEGER PRIMARY KEY, count INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    ''')
    db.commit()
    return db


def policy_for(config, channel, now, capability):
    policy = config.policies.get(channel)
    return bool(policy and policy.expires_at > now and getattr(policy, capability))


def request(db, config, now, fn, *args):
    day = int(now // 86400)
    # Charge before calling, even if the request fails or the worker crashes.
    with db:
        db.execute('INSERT OR IGNORE INTO usage VALUES (?, 0)', (day,))
        row = db.execute('SELECT count FROM usage WHERE day=?', (day,)).fetchone()
        if row['count'] >= config.daily_requests:
            raise BudgetExceeded('Daily provider request budget exhausted')
        db.execute('UPDATE usage SET count=count+1 WHERE day=?', (day,))
        db.execute('DELETE FROM usage WHERE day < ?', (day-30,))
    return fn(*args)


def notebook_cleanup(db, config, provider, now, video_id):
    row = db.execute('SELECT * FROM notebooks WHERE video_id=?', (video_id,)).fetchone()
    if not row:
        return
    if row['state'] != 'registered':
        # A timed out POST may have succeeded remotely. Never blindly duplicate it.
        return
    request(db, config, now, provider.notebook_delete, row['source_id'])
    with db:
        db.execute('DELETE FROM notebooks WHERE video_id=?', (video_id,))


def cycle(db, config, provider, now=None, discovery_only=False):
    now = time.time() if now is None else now
    path = db.execute('PRAGMA database_list').fetchone()['file']
    with open(path + '.lock', 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Knowledge worker is already running') from None
        return _cycle(db, config, provider, now, discovery_only)


def _cycle(db, config, provider, now, discovery_only=False):
    summary = dict(discovered=0, analyzed=0, synced=0, blocked=0, errors=0)
    target = (config.notebook_endpoint + ':' + config.notebook) if config.notebook else ''
    old = db.execute("SELECT value FROM settings WHERE key='notebook'").fetchone()
    if not discovery_only and old and old['value'] != target and db.execute('SELECT 1 FROM notebooks LIMIT 1').fetchone():
        raise ValueError('Reconcile existing Notebook sources before changing target')
    if not discovery_only:
        with db:
            db.execute("INSERT OR REPLACE INTO settings VALUES ('notebook', ?)", (target,))

    # Local content is withdrawn immediately; remote deletion failures are retried.
    for row in db.execute('SELECT * FROM videos').fetchall():
        expired = now - (row['analyzed'] or row['created']) >= config.retention_days*86400
        permitted = policy_for(config, row['channel_id'], now, 'knowledge_allowed')
        notebook_permitted = policy_for(config, row['channel_id'], now, 'notebook_allowed')
        if expired or not permitted:
            with db:
                db.execute('UPDATE videos SET analysis=NULL, analyzed=NULL WHERE id=?', (row['id'],))
        if not discovery_only and (expired or not permitted or not notebook_permitted):
            try:
                notebook_cleanup(db, config, provider, now, row['id'])
            except ValueError:
                summary['errors'] += 1
        if expired and not db.execute('SELECT 1 FROM notebooks WHERE video_id=?', (row['id'],)).fetchone():
            with db:
                db.execute('DELETE FROM videos WHERE id=?', (row['id'],))

    ids = []
    # Refresh saved sources before discovery so deleted/private sources are withdrawn.
    for row in db.execute('SELECT id FROM videos WHERE verified <= ? ORDER BY verified LIMIT 20', (now-86400,)):
        ids.append(row['id'])
    for query in config.queries:
        try:
            ids.extend(request(db, config, now, provider.discover, query))
        except BudgetExceeded:
            summary['blocked'] += 1
            break
        except ValueError:
            summary['errors'] += 1
    ids.extend(row['id'] for row in db.execute('SELECT id FROM videos ORDER BY attempted LIMIT 20'))
    ids = list(dict.fromkeys(ids))[:40]
    for video_id in ids:
        try:
            canonical(video_id)
            existing = db.execute('SELECT * FROM videos WHERE id=?', (video_id,)).fetchone()
            if not existing or now - existing['verified'] >= 86400:
                metadata = request(db, config, now, provider.video, video_id)
                if metadata is None:
                    with db:
                        db.execute('UPDATE videos SET analysis=NULL, analyzed=NULL, verified=0 WHERE id=?', (video_id,))
                    if not discovery_only:
                        notebook_cleanup(db, config, provider, now, video_id)
                    with db:
                        db.execute('DELETE FROM videos WHERE id=? AND NOT EXISTS (SELECT 1 FROM notebooks WHERE video_id=?)', (video_id, video_id))
                    continue
                if not existing and db.execute('SELECT count(*) FROM videos').fetchone()[0] >= 500:
                    summary['blocked'] += 1
                    continue
                with db:
                    db.execute('''INSERT INTO videos(id,channel_id,title,duration,verified,created)
                        VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                        channel_id=excluded.channel_id,title=excluded.title,
                        duration=excluded.duration,verified=excluded.verified''',
                        (video_id,metadata['channel_id'],metadata['title'],metadata['duration'],now,now))
                summary['discovered'] += 1
            with db:
                db.execute('UPDATE videos SET attempted=? WHERE id=?', (now,video_id))
            row = db.execute('SELECT * FROM videos WHERE id=?', (video_id,)).fetchone()
            if discovery_only:
                continue
            if not (policy_for(config, row['channel_id'], now, 'analysis_allowed')
                    and policy_for(config, row['channel_id'], now, 'knowledge_allowed')):
                summary['blocked'] += 1
                continue
            if row['analysis'] and json.loads(row['analysis']).get('species') != 'dog':
                summary['blocked'] += 1
                continue
            if not row['analysis'] or row['model'] != config.gemini_model:
                if summary['analyzed'] >= config.max_videos:
                    continue
                result = request(db, config, now, provider.analyze, video_id)
                if any(e.end_seconds > row['duration'] for e in result.entries):
                    raise ValueError('Analysis timestamps exceed video duration')
                if result.species != 'dog' or not result.entries:
                    raise ValueError('Insufficient video evidence')
                with db:
                    db.execute('UPDATE videos SET analysis=?,analyzed=?,model=?,error=NULL WHERE id=?',
                        (result.model_dump_json(), now, config.gemini_model, video_id))
                summary['analyzed'] += 1
            if config.notebook and policy_for(config, row['channel_id'], now, 'notebook_allowed'):
                sync = db.execute('SELECT * FROM notebooks WHERE video_id=?', (video_id,)).fetchone()
                if not sync:
                    # Persist intent before POST; crash/timeout leaves an explicit uncertain outcome.
                    with db:
                        db.execute("INSERT INTO notebooks VALUES (?,NULL,'uncertain')", (video_id,))
                    try:
                        source_id = request(db, config, now, provider.notebook_add, video_id)
                    except BudgetExceeded:
                        with db:
                            db.execute('DELETE FROM notebooks WHERE video_id=?', (video_id,))
                        raise
                    with db:
                        db.execute("UPDATE notebooks SET source_id=?,state='registered' WHERE video_id=?", (source_id,video_id))
                    summary['synced'] += 1
        except BudgetExceeded:
            summary['blocked'] += 1
            break
        except (ValueError, KeyError, TypeError):
            # No provider exception text, credentials or transcript in logs.
            with db:
                db.execute("UPDATE videos SET error='Processing unavailable' WHERE id=?", (video_id,))
            summary['errors'] += 1
    summary['notebook_uncertain'] = db.execute("SELECT count(*) FROM notebooks WHERE state='uncertain'").fetchone()[0]
    summary['notice'] = 'Knowledge update only. No model weights trained; AI extractions remain unreviewed.'
    return summary


def search(db, config, query, now=None):
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 200:
        raise ValueError('Query must contain 1–200 characters')
    now = time.time() if now is None else now
    terms = set(re.findall(r'[\w]+', query.lower()))
    hits = []
    for row in db.execute('SELECT * FROM videos WHERE analysis IS NOT NULL AND verified > ? AND analyzed > ?',
                          (now-86400, now-config.retention_days*86400)):
        if row['model'] != config.gemini_model or not policy_for(config, row['channel_id'], now, 'knowledge_allowed'):
            continue
        data = json.loads(row['analysis'])
        if data.get('species') != 'dog':
            continue
        for entry in data['entries']:
            if entry['confidence'] < .6:
                continue
            text = entry['text'].lower()
            rank = sum(1 for term in terms if term in text)
            if rank:
                hits.append(dict(score=rank, **entry, species=data['species'], title=row['title'],
                    source_id=row['id'], citation=canonical(row['id'])+f"&t={entry['start_seconds']}s",
                    verification='machine_extracted_unreviewed', confidence_kind='uncalibrated'))
    return sorted(hits, key=lambda h: (-h['score'], h['source_id'], h['start_seconds']))[:5]
