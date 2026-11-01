"""Deterministic connected groups for conservative split isolation."""


class Groups:
    def __init__(self, identities):
        self.parents={key:key for key in identities}

    def find(self,key):
        root=key
        while self.parents[root]!=root:root=self.parents[root]
        while self.parents[key]!=key:
            parent=self.parents[key];self.parents[key]=root;key=parent
        return root

    def join(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.parents[max(a,b)]=min(a,b)


def valid_identity(value):
    if not isinstance(value,str) or not value or value!=value.strip() or value.lower() in ('unknown','none','null','pending'):
        raise ValueError('Explicit canonical grouping identity required')
    return value


def animal_groups(rows):
    graph=Groups(valid_identity(r['animal_id']) for r in rows)
    seen={}
    for row in rows:
        for field in ('household_id','recording_group','source_id','duplicate_group'):
            if field not in row:continue
            key=(field,valid_identity(row[field]))
            if key in seen:graph.join(row['animal_id'],seen[key])
            else:seen[key]=row['animal_id']
    return {animal:graph.find(animal) for animal in graph.parents}
