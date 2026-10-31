"""Minimal, expiring per-dog read grants; no copies of shared records."""
def create_tables(db):
    db.execute('CREATE TABLE IF NOT EXISTS care_shares(id TEXT PRIMARY KEY,owner TEXT NOT NULL,pet_id TEXT NOT NULL,code_hash TEXT NOT NULL UNIQUE,recipient TEXT,created REAL NOT NULL,invite_expires REAL NOT NULL,expires REAL NOT NULL,accepted REAL)')
    db.execute('CREATE INDEX IF NOT EXISTS care_owner ON care_shares(owner,pet_id)')
    db.execute('CREATE INDEX IF NOT EXISTS care_recipient ON care_shares(recipient)')


def purge(db,now):
    db.execute('DELETE FROM care_shares WHERE expires<=? OR (recipient IS NULL AND invite_expires<=?) OR pet_id IN (SELECT id FROM pets WHERE expires<=?)',(now,now,now))
