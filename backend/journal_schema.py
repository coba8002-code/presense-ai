"""Journal schema and cascades shared by account deletion and TTL maintenance."""


def create_tables(db):
    db.execute('CREATE TABLE IF NOT EXISTS journal_cases(id TEXT PRIMARY KEY,owner TEXT NOT NULL,pet_id TEXT NOT NULL,pet_name TEXT NOT NULL,observed REAL NOT NULL,created REAL NOT NULL,expires REAL NOT NULL,payload TEXT NOT NULL,consent_version TEXT NOT NULL,key_hash TEXT NOT NULL,payload_hash TEXT NOT NULL,UNIQUE(owner,key_hash))')
    db.execute('CREATE INDEX IF NOT EXISTS journal_owner ON journal_cases(owner,observed,id)')
    db.execute('CREATE INDEX IF NOT EXISTS journal_pet ON journal_cases(owner,pet_id)')
    db.execute('CREATE TABLE IF NOT EXISTS journal_followups(id TEXT PRIMARY KEY,owner TEXT NOT NULL,case_id TEXT NOT NULL,observed REAL NOT NULL,created REAL NOT NULL,payload TEXT NOT NULL,key_hash TEXT NOT NULL,payload_hash TEXT NOT NULL,UNIQUE(owner,case_id,key_hash))')
    db.execute('CREATE INDEX IF NOT EXISTS journal_followup_case ON journal_followups(owner,case_id,observed)')


def purge(db,now):
    db.execute('DELETE FROM journal_followups WHERE case_id IN (SELECT id FROM journal_cases WHERE expires<=? OR pet_id IN (SELECT id FROM pets WHERE expires<=?))',(now,now))
    db.execute('DELETE FROM journal_cases WHERE expires<=? OR pet_id IN (SELECT id FROM pets WHERE expires<=?)',(now,now))


def delete_pet(db,owner,pet_id):
    db.execute('DELETE FROM journal_followups WHERE owner=? AND case_id IN (SELECT id FROM journal_cases WHERE owner=? AND pet_id=?)',(owner,owner,pet_id))
    db.execute('DELETE FROM journal_cases WHERE owner=? AND pet_id=?',(owner,pet_id))
