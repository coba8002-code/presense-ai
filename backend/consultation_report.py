"""Atomic, bounded guardian report snapshots. No model inference or stored copies."""
import json


def build_report(store,token,pet_id,days=7):
    if type(days) is not int or days not in (7,30,90):raise ValueError('Invalid report window')
    with store.connect() as db:
        owner=store._begin(db,token);pet=store._pet(db,owner,pet_id)
        end=store.clock();start=end-days*86400
        params=(owner,pet_id,end,start,end)
        where='owner=? AND pet_id=? AND expires>? AND observed>=? AND observed<=?'
        total=db.execute('SELECT count(*) FROM journal_cases WHERE '+where,params).fetchone()[0]
        rows=db.execute('SELECT * FROM journal_cases WHERE '+where+' ORDER BY observed DESC,id DESC LIMIT 100',params).fetchall()
        cases=[];missing={key:0 for key in ('before','during','after','duration','change','dogs','followup')}
        for row in reversed(rows):
            follows=db.execute('SELECT id,created,payload FROM journal_followups WHERE owner=? AND case_id=? AND observed<=? ORDER BY observed,id LIMIT 20',(owner,row['id'],end)).fetchall()
            case={**store.view(row),'followups':[{'id':f['id'],'created':f['created'],'data':json.loads(f['payload']),'kind':'guardian_report','model_analysis':False,'training_approved':False} for f in follows]}
            for key in ('before','during','after'):
                missing[key]+=int(not case['data'][key].strip())
            for key in ('duration','change','dogs'):
                missing[key]+=int(case['data'][key]=='unknown')
            missing['followup']+=int(not follows);cases.append(case)
        return {'version':1,'kind':'guardian_consultation_report','model_analysis':False,'training_approved':False,'pet':{'id':pet_id,'name':pet['name']},'generated_at':end,'start':start,'end':end,'days':days,'total':total,'included':len(cases),'truncated':total>len(cases),'missing':missing,'cases':cases}
