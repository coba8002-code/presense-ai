"""Private worker. Offline weights only; no credentials, tools or network requests."""
import json
import math
import sys
from training.av_alignment import align
from training.audio_timeline import analyze_windows
from training.pretrained_audio import ASTDogAudio,MODEL,REVISION
from training.event_candidates import candidates


def main():
 data=json.loads(sys.stdin.buffer.read(4097))
 if set(data)!= {'path','consent','vision','pose'} or data['consent'] is not True or type(data['vision']) is not bool or type(data['pose']) is not bool:raise ValueError('Invalid local job')
 model=None
 def observe(signal,start,duration):
  nonlocal model
  if model is None:model=ASTDogAudio()
  if start<0:
   trim=math.ceil(-start*16000);signal=signal[trim:];start+=trim/16000
  signal=signal[:int((duration-start)*16000)]
  result=analyze_windows(signal,model.analyze,offset=start,video_duration=duration)
  event_windows=[{'start':w['start'],'end':w['end'],'dog_event_scores':w['score_result']['dog_event_scores'],'audio_quality':w['audio_quality']} for w in result['windows']]
  return {'candidate_events':candidates(event_windows),'model':MODEL,'revision':REVISION,'score_type':'uncalibrated_independent_sigmoid','decision':'abstain','species_verified':False,
   'windows':[{'start':w['start'],'end':w['end'],'dog_event_scores':w['score_result']['dog_event_scores']} for w in result['windows']],
   'limitations':['Window scores are not detected onset/offset events','No speaker, intent, emotion or independent accuracy verification']}
 def vision(report,image_at):
  from training.small_vlm import load_base,predict,image_from_bytes,MODEL as VM,REVISION as VR
  processor=vlm=detector=None
  if data['vision']:processor,vlm=load_base()
  if data['pose']:
   from training.dog_pose import LocalDogPose,DETECTOR,DETECTOR_REV,POSE,POSE_REV
   from training.track_pose import adapt
   detector=LocalDogPose()
  count=len(report['frame_times']);indexes=sorted({round(i*(count-1)/5) for i in range(6)})
  observations=[];frames=[];width=height=None
  for index in indexes:
   image=image_from_bytes(image_at(index));width,height=image.size
   if data['vision']:
    candidate=predict(processor,vlm,image)
    observations.append({'seconds':report['frame_times'][index],'posture_candidate':candidate})
   if detector:frames.append({'seconds':report['frame_times'][index],'detections':detector.predict(image)})
  if detector:
   document={'source_sha256':report['source_sha256'],'source_kind':'upstream_model','model':DETECTOR+'/'+POSE,'revision':DETECTOR_REV+'+'+POSE_REV,'width':width,'height':height,'frames':frames}
   tracks=adapt(document)
   for raw,tracked in zip(frames,tracks['frames']):
    for detection,track in zip(raw['detections'],tracked['detections']):detection.update(track)
   report['pose_model']={'detector_model':DETECTOR,'detector_revision':DETECTOR_REV,'keypoint_model':POSE,'keypoint_revision':POSE_REV,'width':width,'height':height,'frames':frames,'pose_forward_calls':detector.pose_calls,'detector_threshold':.7,'identity_verified':False,'species_verified':False,'decision':'abstain','coordinate_space':'decoded_scaled_frame','confidence_kind':'clipped_raw_simcc_peak_not_probability','limitations':['Dog boxes and keypoints are unvalidated candidates','No global identity or speaker attribution','Sparse frame gaps reset geometry association','No behavioral/medical/emotion/intent inference']}
  if data['vision']:
   return {'model':VM,'revision':VR,'observations':observations,'decision':'abstain','species_verified':False,
    'limitations':['Unvalidated single-frame posture candidates only','No reliable non-dog rejection, tracking, movement or emotion/intent inference']}
  return None
 report=align(data['path'],consent=True,audio_observer=observe,isolate_processes=False,frame_observer=vision if data['vision'] or data['pose'] else None,max_seconds=115)
 json.dump(report,sys.stdout,allow_nan=False)
if __name__=='__main__':
 try:main()
 except Exception:sys.exit(2)
