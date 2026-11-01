"""Bounded adapter for supplied detector/keypoint outputs; not a detector or ID proof."""
import argparse
import json
import math
from pathlib import Path
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

class Strict(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
class Point(Strict):
 x:float=Field(ge=0,allow_inf_nan=False)
 y:float=Field(ge=0,allow_inf_nan=False)
 confidence:float=Field(ge=0,le=1,allow_inf_nan=False)
class Detection(Strict):
 box:list[float]=Field(min_length=4,max_length=4)
 score:float=Field(ge=0,le=1,allow_inf_nan=False)
 keypoints:dict[Literal['left_eye','right_eye','nose','neck','tail_root','left_shoulder','left_elbow','left_front_paw','right_shoulder','right_elbow','right_front_paw','left_hip','left_knee','left_back_paw','right_hip','right_knee','right_back_paw'],Point]=Field(default_factory=dict)
class Frame(Strict):
 seconds:float=Field(ge=0,le=30,allow_inf_nan=False)
 detections:list[Detection]=Field(max_length=8)
class Document(Strict):
 source_sha256:str=Field(pattern='^[a-f0-9]{64}$')
 source_kind:Literal['synthetic_fixture','upstream_model','human_annotation']
 model:str=Field(min_length=1,max_length=200)
 revision:str=Field(min_length=1,max_length=200)
 width:int=Field(ge=1,le=4096)
 height:int=Field(ge=1,le=4096)
 frames:list[Frame]=Field(min_length=1,max_length=1800)

def overlap(a,b):
 intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
 area=lambda x:(x[2]-x[0])*(x[3]-x[1])
 return intersection/(area(a)+area(b)-intersection)

def adapt(document):
 doc=Document.model_validate(document)
 if doc.width*doc.height>4000000 or any(b.seconds<=a.seconds for a,b in zip(doc.frames,doc.frames[1:])):raise ValueError('Bounded image and ordered common clock required')
 output=[];previous=[];previous_time=None;seq=0
 for frame in doc.frames:
  detections=frame.detections
  for d in detections:
   b=d.box
   if not all(math.isfinite(x) for x in b) or not 0<=b[0]<b[2]<=doc.width or not 0<=b[1]<b[3]<=doc.height or any(p.x>doc.width or p.y>doc.height for p in d.keypoints.values()):raise ValueError('Invalid detector/image coordinates')
  matrix=[[overlap(d.box,p['box']) for p in previous] for d in detections];rows=[]
  for i,d in enumerate(detections):
   candidates=sorted([(value,j) for j,value in enumerate(matrix[i])],reverse=True)
   chosen=None
   if candidates and previous_time is not None and frame.seconds-previous_time<=.5 and d.score>=.5:
    value,j=candidates[0];second=candidates[1][0] if len(candidates)>1 else 0
    reverse=sorted([(matrix[k][j],k) for k in range(len(detections))],reverse=True)
    if value>=.3 and value-second>=.2 and reverse[0][1]==i and (len(reverse)==1 or reverse[0][0]-reverse[1][0]>=.2) and previous[j]['score']>=.5:chosen=previous[j]['track_candidate_id']
   if chosen is None:seq+=1;chosen=f'clip-candidate-{seq:05d}'
   neck=d.keypoints.get('neck');tail=d.keypoints.get('tail_root');angle=None
   if neck and tail and neck.confidence>=.5 and tail.confidence>=.5 and math.hypot(neck.x-tail.x,neck.y-tail.y)>1:
    angle=math.degrees(math.atan2(neck.y-tail.y,neck.x-tail.x))
   rows.append({'track_candidate_id':chosen,'box':d.box,'score':d.score,'torso_angle_degrees':angle,
    'keypoints_supplied':len(d.keypoints),'visible_keypoints':sum(p.confidence>=.5 for p in d.keypoints.values()),
    'association':'geometry_candidate_not_identity' if any(p['track_candidate_id']==chosen for p in previous) else 'new_or_ambiguous_candidate','pose_abstained':angle is None})
  output.append({'seconds':frame.seconds,'detections':rows});previous=rows;previous_time=frame.seconds
 return {'source_sha256':doc.source_sha256,'source_kind':doc.source_kind,'upstream_model':doc.model,'upstream_revision':doc.revision,
  'frames':output,'identity_verified':False,'speaker':'unconfirmed','inference_performed_here':False,'behavior_interpretation':None,
  'policy':'mutual_iou_0.3_margin_0.2_gap_0.5s_v1_unvalidated','limitations':['Supplied detections only; no actual detector/keypoint inference','Candidate IDs are clip-local geometry, never global pet identity','Thresholds and geometry are unvalidated; camera/occlusion/crossings can break association','Torso angle is image geometry, not posture class, emotion, intent or diagnosis']}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.input.stat().st_size>8000000:raise ValueError('Bounded local supplied observations required')
 result=adapt(json.loads(a.input.read_text()))
 with a.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)
if __name__=='__main__':main()
