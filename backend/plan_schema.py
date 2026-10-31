"""Plan retention follows the parent case without extending it."""
def create_tables(db):
    db.execute('CREATE TABLE IF NOT EXISTS care_plans(id TEXT PRIMARY KEY,owner TEXT NOT NULL,case_id TEXT NOT NULL,goal TEXT NOT NULL,due REAL NOT NULL,created REAL NOT NULL,expires REAL NOT NULL,status TEXT NOT NULL,closed REAL,followup_id TEXT,key_hash TEXT NOT NULL,payload_hash TEXT NOT NULL,UNIQUE(owner,key_hash))')
    db.execute('CREATE INDEX IF NOT EXISTS plan_case ON care_plans(owner,case_id)')


def purge(db,now):
    db.execute('DELETE FROM care_plans WHERE expires<=? OR NOT EXISTS (SELECT 1 FROM journal_cases c WHERE c.id=care_plans.case_id AND c.owner=care_plans.owner)',(now,))
