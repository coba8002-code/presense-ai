"""Pinned local dog detector and AP10K animal keypoints. No identity/behavior proof."""
import math
import hashlib
import numpy as np
DETECTOR='PekingU/rtdetr_r50vd'
DETECTOR_REV='df939e661d8c52e80608d1ec566561aabd25a4e7'
POSE='litert-community/RTMPose-Animal-AP10K-LiteRT'
POSE_REV='1daee634c9db6889268124735374e6a9c1c2fc7b'
POSE_FILE='rtm_animal_fp16.tflite'
DETECTOR_SHA256='5263d5521eff3e356f6cd8a371fd5dfb891725beda5f713674f79669115cdc64'
POSE_SHA256='7fbfc03239cebc1f657efab722849bc9b30d36d3d4371118aed2aaf4041e742f'
AP10K_NAMES=('left_eye','right_eye','nose','neck','tail_root','left_shoulder','left_elbow','left_front_paw','right_shoulder','right_elbow','right_front_paw','left_hip','left_knee','left_back_paw','right_hip','right_knee','right_back_paw')


def decode_simcc(sx,sy,crop,width,height):
 sx=np.asarray(sx);sy=np.asarray(sy)
 if sx.shape!=(17,512) or sy.shape!=(17,512) or not np.all(np.isfinite(sx)) or not np.all(np.isfinite(sy)) or len(crop)!=4 or not all(math.isfinite(v) for v in crop) or not crop[0]<crop[2] or not crop[1]<crop[3] or not 0<width<=4096 or not 0<height<=4096:raise ValueError('Invalid bounded AP10K SimCC/crop')
 x=sx.argmax(-1)/2.;y=sy.argmax(-1)/2.;points={}
 for i,name in enumerate(AP10K_NAMES):
  px=crop[0]+x[i]/256*(crop[2]-crop[0]);py=crop[1]+y[i]/256*(crop[3]-crop[1])
  score=float(np.clip((sx[i].max()+sy[i].max())/2,0,1)) if 0<=px<width and 0<=py<height else 0.
  points[name]={'x':float(np.clip(px,0,width)),'y':float(np.clip(py,0,height)),'confidence':score}
 return points


def prepare_public_cache():
 """Explicit setup only; public weights, no media/account credentials."""
 from huggingface_hub import snapshot_download,hf_hub_download
 snapshot_download(DETECTOR,revision=DETECTOR_REV,token=False,allow_patterns=['*.json','*.safetensors'])
 return hf_hub_download(POSE,POSE_FILE,revision=POSE_REV,token=False)


class LocalDogPose:
 def __init__(self):
  import torch
  from transformers import RTDetrForObjectDetection,RTDetrImageProcessor
  from ai_edge_litert.interpreter import Interpreter
  from huggingface_hub import hf_hub_download
  torch.set_num_threads(2)
  for repo,revision,file,expected in [(DETECTOR,DETECTOR_REV,'model.safetensors',DETECTOR_SHA256),(POSE,POSE_REV,POSE_FILE,POSE_SHA256)]:
   with open(hf_hub_download(repo,file,revision=revision,local_files_only=True),'rb') as stream:
    if hashlib.file_digest(stream,'sha256').hexdigest()!=expected:raise ValueError('Pinned model artifact hash mismatch')
  self.processor=RTDetrImageProcessor.from_pretrained(DETECTOR,revision=DETECTOR_REV,local_files_only=True,trust_remote_code=False)
  self.model=RTDetrForObjectDetection.from_pretrained(DETECTOR,revision=DETECTOR_REV,local_files_only=True,trust_remote_code=False,use_safetensors=True).eval()
  dog=[int(k) for k,v in self.model.config.id2label.items() if v.lower()=='dog']
  if len(dog)!=1:raise ValueError('Dog class mapping missing')
  self.dog=dog[0];path=hf_hub_download(POSE,POSE_FILE,revision=POSE_REV,local_files_only=True)
  self.pose=Interpreter(model_path=path,num_threads=2);self.pose.allocate_tensors();self.input=self.pose.get_input_details()[0];self.outputs=self.pose.get_output_details()
  if self.input['shape'].tolist()!=[1,3,256,256] or self.input['dtype']!=np.float32 or [x['shape'].tolist() for x in self.outputs]!=[[1,17,512],[1,17,512]]:raise ValueError('Pinned animal keypoint tensor contract mismatch')
  self.pose_calls=0
 def keypoints(self,image,box):
  from PIL import Image
  width,height=image.size;x1,y1,x2,y2=box
  if not 0<=x1<x2<=width or not 0<=y1<y2<=height:raise ValueError('Bounded crop required')
  side=max(x2-x1,y2-y1)*1.2;cx=(x1+x2)/2;cy=(y1+y2)/2;crop=(cx-side/2,cy-side/2,cx+side/2,cy+side/2)
  picture=image.convert('RGB').transform((256,256),Image.Transform.EXTENT,crop,resample=Image.Resampling.BILINEAR)
  mean=np.array([123.675,116.28,103.53],np.float32);std=np.array([58.395,57.12,57.375],np.float32)
  values=((np.asarray(picture,dtype=np.float32)-mean)/std).transpose(2,0,1)[None]
  self.pose.set_tensor(self.input['index'],values);self.pose.invoke();self.pose_calls+=1
  sx=self.pose.get_tensor(self.outputs[0]['index'])[0];sy=self.pose.get_tensor(self.outputs[1]['index'])[0]
  return decode_simcc(sx,sy,crop,width,height)
 def predict(self,image):
  import torch
  width,height=image.size
  if width*height>4000000:raise ValueError('Image too large')
  inputs=self.processor(images=image.convert('RGB'),return_tensors='pt')
  with torch.inference_mode():output=self.model(**inputs)
  result=self.processor.post_process_object_detection(output,target_sizes=torch.tensor([[height,width]]),threshold=.7)[0]
  candidates=sorted([(float(s),b.tolist()) for s,label,b in zip(result['scores'],result['labels'],result['boxes']) if int(label)==self.dog],reverse=True)[:4]
  detections=[]
  for score,box in candidates:
   box=[float(np.clip(v,0,width if i%2==0 else height)) for i,v in enumerate(box)]
   if not box[0]<box[2] or not box[1]<box[3]:continue
   detections.append({'box':box,'score':score,'keypoints':self.keypoints(image,box)})
  return detections
