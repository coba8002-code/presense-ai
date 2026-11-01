"""Explicitly consented model-metadata history; no raw media or automatic training."""
def create_tables(db):
 db.execute('CREATE TABLE IF NOT EXISTS model_observations(id TEXT PRIMARY KEY,owner TEXT NOT NULL,pet_id TEXT NOT NULL,source_job_id TEXT NOT NULL,created REAL NOT NULL,submitted REAL NOT NULL,expires REAL NOT NULL,payload TEXT NOT NULL,payload_hash TEXT NOT NULL,UNIQUE(owner,source_job_id))')
 db.execute('CREATE INDEX IF NOT EXISTS observation_pet ON model_observations(owner,pet_id,submitted)')
 db.execute('CREATE TABLE IF NOT EXISTS observation_feedback(id TEXT PRIMARY KEY,owner TEXT NOT NULL,observation_id TEXT NOT NULL,created REAL NOT NULL,reason TEXT NOT NULL,status TEXT NOT NULL,review_payload TEXT,UNIQUE(owner,observation_id))')

def purge(db,now):
 db.execute('DELETE FROM model_observations WHERE expires<=? OR pet_id IN (SELECT id FROM pets WHERE expires<=?)',(now,now))
 db.execute('DELETE FROM observation_feedback WHERE NOT EXISTS (SELECT 1 FROM model_observations m WHERE m.id=observation_feedback.observation_id AND m.owner=observation_feedback.owner)')

def delete_pet(db,owner,pet):
 db.execute('DELETE FROM observation_feedback WHERE owner=? AND observation_id IN (SELECT id FROM model_observations WHERE owner=? AND pet_id=?)',(owner,owner,pet))
 db.execute('DELETE FROM model_observations WHERE owner=? AND pet_id=?',(owner,pet))

def delete_job(db,owner,job):
 db.execute('DELETE FROM observation_feedback WHERE owner=? AND observation_id IN (SELECT id FROM model_observations WHERE owner=? AND source_job_id=?)',(owner,owner,job))
 db.execute('DELETE FROM model_observations WHERE owner=? AND source_job_id=?',(owner,job))
