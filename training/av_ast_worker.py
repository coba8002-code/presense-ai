"""Private worker. Offline weights only; no credentials, tools or network requests."""
import json
import math
import sys
from training.av_alignment import align
from training.audio_timeline import analyze_windows
from training.pretrained_audio import ASTDogAudio,MODEL,REVISION


def main():
 data=json.loads(sys.stdin.buffer.read(4097))
 if set(data)!= {'path','consent','vision'} or data['consent'] is not True or type(data['vision']) is not bool:raise ValueError('Invalid local job')
 model=None
 def observe(signal,start,duration):
  nonlocal model
  if model is None:model=ASTDogAudio()
  if start<0:
   trim=math.ceil(-start*16000);signal=signal[trim:];start+=trim/16000
  signal=signal[:int((duration-start)*16000)]
  result=analyze_windows(signal,model.analyze,offset=start,video_duration=duration)
  return {'model':MODEL,'revision':REVISION,'score_type':'uncalibrated_independent_sigmoid','decision':'abstain','species_verified':False,
   'windows':[{'start':w['start'],'end':w['end'],'dog_event_scores':w['score_result']['dog_event_scores']} for w in result['windows']],
   'limitations':['Window scores are not detected onset/offset events','No speaker, intent, emotion or independent accuracy verification']}
 def vision(report,image_at):
  from training.small_vlm import load_base,predict,image_from_bytes,MODEL as VM,REVISION as VR
  processor,vlm=load_base();count=len(report['frame_times']);indexes=sorted({round(i*(count-1)/5) for i in range(6)})
  observations=[]
  for index in indexes:
   candidate=predict(processor,vlm,image_from_bytes(image_at(index)))
   observations.append({'seconds':report['frame_times'][index],'posture_candidate':candidate})
  return {'model':VM,'revision':VR,'observations':observations,'decision':'abstain','species_verified':False,
   'limitations':['Unvalidated single-frame posture candidates only','No reliable non-dog rejection, tracking, movement or emotion/intent inference']}
 report=align(data['path'],consent=True,audio_observer=observe,isolate_processes=False,frame_observer=vision if data['vision'] else None,max_seconds=115)
 json.dump(report,sys.stdout,allow_nan=False)
if __name__=='__main__':
 try:main()
 except Exception:sys.exit(2)
