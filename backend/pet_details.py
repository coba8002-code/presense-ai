"""Optional guardian reports; no automatic breed, identity or emotion verification."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator,field_validator

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)

class DogDetails(Strict):
    breed_kind:Literal['unknown','mixed','reported']='unknown'
    breed_name:str|None=Field(default=None,min_length=1,max_length=60)
    age_months:int|None=Field(default=None,ge=0,le=360)
    weight_kg:float|None=Field(default=None,ge=.1,le=200,allow_inf_nan=False)
    ears:Literal['unknown','upright','floppy','mixed']='unknown'
    tail:Literal['unknown','straight','curled','short','absent']='unknown'
    muzzle:Literal['unknown','short','medium','long']='unknown'
    coat:Literal['unknown','short','long']='unknown'

    @field_validator('breed_name')
    @classmethod
    def clean(cls,value):
        if value is not None:
            value=value.strip()
            if not value or any(ord(c)<32 for c in value):raise ValueError('Breed name must be plain text')
        return value

    @model_validator(mode='after')
    def breed_report(self):
        if self.breed_kind=='reported' and not self.breed_name:raise ValueError('Reported breed name required')
        if self.breed_kind=='unknown' and self.breed_name is not None:raise ValueError('Unknown breed cannot have a name')
        return self

class CaptureContext(Strict):
    setting:Literal['unknown','alone','play','walk','meal','rest','unfamiliar_person','unfamiliar_dog']='unknown'
    dogs:Literal['unknown','one','multiple']='unknown'
    speaker:Literal['unconfirmed','guardian_confirmed']='unconfirmed'
    device_id:str|None=Field(default=None,pattern=r'^[A-Za-z0-9_-]{1,40}$')
    noise:Literal['unknown','quiet','noisy']='unknown'
    distance:Literal['unknown','near','far']='unknown'
    visibility:Literal['unknown','clear','occluded','not_recorded']='unknown'

def interpretation_limits(details,context):
    """Missing-cue prompts from guardian reports, never inferred dog emotions."""
    details=details or {}
    reasons=[]
    if context['speaker']!='guardian_confirmed':reasons.append('speaker_unconfirmed')
    if context['dogs']=='multiple':reasons.append('multiple_dogs_attribution_unverified')
    if context['visibility']!='clear':reasons.append('visual_cues_unavailable_or_unverified')
    if details.get('tail')=='absent':reasons.append('tail_cue_not_applicable_reported')
    elif details.get('tail') in ('curled','short'):reasons.append('individual_neutral_tail_reference_needed')
    if details.get('ears')=='floppy':reasons.append('ear_base_visibility_check_needed')
    if details.get('coat')=='long':reasons.append('coat_occlusion_check_needed')
    return reasons

def create_tables(db):
    db.execute('CREATE TABLE IF NOT EXISTS pet_details(pet_id TEXT PRIMARY KEY,owner TEXT NOT NULL,reported_at REAL NOT NULL,payload TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS job_contexts(job_id TEXT PRIMARY KEY,owner TEXT NOT NULL,pet_id TEXT NOT NULL,payload TEXT NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS pet_details_owner ON pet_details(owner)')
    db.execute('CREATE INDEX IF NOT EXISTS job_contexts_owner ON job_contexts(owner)')

def purge(db):
    db.execute('DELETE FROM pet_details WHERE NOT EXISTS (SELECT 1 FROM pets p WHERE p.id=pet_details.pet_id AND p.owner=pet_details.owner)')
    db.execute("DELETE FROM job_contexts WHERE NOT EXISTS (SELECT 1 FROM audio_jobs j WHERE j.id=job_contexts.job_id AND j.owner=job_contexts.owner AND j.status NOT IN ('cancelled','expired'))")
