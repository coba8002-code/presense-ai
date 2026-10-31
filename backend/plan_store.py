"""Owner-confirmed observation plans, never verified efficacy or automatic advice."""
import uuid
from backend.journal_store import JournalStore,JournalConflict,JournalLimit,fingerprint

class PlanStore(JournalStore):
    @staticmethod
    def plan_view(row):
        return {k:row[k] for k in ('id','case_id','goal','due','created','expires','status','closed','followup_id')} | {'kind':'guardian_care_plan','verified_completion':False,'training_approved':False}

    def _plan(self,db,owner,plan_id):
        row=db.execute('SELECT * FROM care_plans WHERE id=? AND owner=? AND expires>?',(plan_id,owner,self.clock())).fetchone()
        if not row:raise KeyError('Plan unavailable')
        return row

    def create_plan(self,token,data,key):
        _,key_hash,payload_hash=fingerprint(data,key)
        with self.connect() as db:
            owner=self._begin(db,token);case=self._case(db,owner,data.case_id)
            old=db.execute('SELECT * FROM care_plans WHERE owner=? AND key_hash=?',(owner,key_hash)).fetchone()
            if old:
                if old['payload_hash']!=payload_hash:raise JournalConflict('Plan content changed')
                return self.plan_view(old)
            now=self.clock();expires=min(now+30*86400,case['expires']);due=data.due_at.timestamp()
            if not now<=due<expires:raise ValueError('Due date outside retention window')
            if db.execute('SELECT count(*) FROM care_plans WHERE owner=?',(owner,)).fetchone()[0]>=100 or db.execute('SELECT count(*) FROM care_plans WHERE owner=? AND case_id=?',(owner,data.case_id)).fetchone()[0]>=10:raise JournalLimit('Plan limit reached')
            plan_id=str(uuid.uuid4())
            db.execute('INSERT INTO care_plans VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(plan_id,owner,data.case_id,data.goal,due,now,expires,'planned',None,None,key_hash,payload_hash))
            return self.plan_view(self._plan(db,owner,plan_id))

    def list_plans(self,token,case_id):
        with self.connect() as db:
            owner=self._begin(db,token);self._case(db,owner,case_id)
            return [self.plan_view(row) for row in db.execute('SELECT * FROM care_plans WHERE owner=? AND case_id=? ORDER BY due,id LIMIT 10',(owner,case_id))]

    def transition(self,token,plan_id,data):
        with self.connect() as db:
            owner=self._begin(db,token);row=self._plan(db,owner,plan_id)
            if row['status']!='planned':
                if row['status']==data.status and row['followup_id']==data.followup_id:return self.plan_view(row)
                raise JournalConflict('Plan is already closed')
            if data.status=='completed':
                follow=db.execute('SELECT 1 FROM journal_followups WHERE id=? AND owner=? AND case_id=? AND created>=? AND observed<=?',(data.followup_id,owner,row['case_id'],row['created'],self.clock())).fetchone()
                if not follow:raise ValueError('A new followup for this case is required')
            db.execute('UPDATE care_plans SET status=?,closed=?,followup_id=? WHERE id=? AND owner=?',(data.status,self.clock(),data.followup_id,plan_id,owner))
            return self.plan_view(self._plan(db,owner,plan_id))

    def delete_plan(self,token,plan_id):
        with self.connect() as db:
            owner=self._begin(db,token);self._plan(db,owner,plan_id)
            db.execute('DELETE FROM care_plans WHERE owner=? AND id=?',(owner,plan_id))
