'use strict';
(function(root){
 const finite=x=>typeof x==='number'&&Number.isFinite(x);
 const labels=['bark','whine','howl','growl','other'];
 function normalize(events,duration,offset=0){
  if(!finite(duration)||duration<=.1||duration>30||!finite(offset)||offset<0||!Array.isArray(events)||events.length>20)throw new Error('Invalid clock/event limit');
  return events.map(e=>{
   if(!e||!labels.includes(e.label)||!finite(e.start)||!finite(e.end)||e.start<0||e.end<=e.start||e.end+offset>duration)throw new Error('Invalid bounded event');
   return {label:e.label,start:e.start+offset,end:e.end+offset,source:'guardian_report',speaker:'unconfirmed'};
  }).sort((a,b)=>a.start-b.start||a.end-b.end);
 }
 function summarize(events){
  const gaps=[];for(let i=1;i<events.length;i++)gaps.push(Math.max(0,events[i].start-events[i-1].end));
  return {count:events.length,intervals:gaps.map(x=>Math.round(x*1000)/1000),speaker:'unconfirmed',source:'guardian_report',training_eligible:false};
 }
 function plan(duration,events){
  events=normalize(events,duration);
  if(!events.length)return Array.from({length:6},(_,i)=>.05+(duration-.1)*i/5);
  // At most the first 3 events; disclose this sampling limit in the UI.
  const points=[];
  for(const e of events.slice(0,3))for(const x of [e.start-.4,e.start,(e.start+e.end)/2,e.end+.4])points.push(Math.max(.05,Math.min(duration-.05,x)));
  return [...new Set(points.map(x=>Math.round(x*1000)/1000))].sort((a,b)=>a-b);
 }
 function validateAlignment(r,hash,duration){
  if(!r||r.schema_version!==1||r.source_sha256!==hash||r.source!=='local_ffmpeg_decoded_pts'||r.clock!=='relative_to_first_decoded_video_frame'||!finite(r.duration)||Math.abs(r.duration-duration)>.1||typeof r.audio_present!=='boolean'||!Array.isArray(r.frame_times)||!r.frame_times.length||r.frame_times.length>1800||!Array.isArray(r.audio_windows)||r.audio_windows.length>310)throw new Error('Invalid alignment report');
  if(r.frame_times.some((v,i)=>!finite(v)||v<0||v>duration+.05||(i&&v<=r.frame_times[i-1])))throw new Error('Invalid frame clock');
  let last=-1;for(const w of r.audio_windows){if(!w||!finite(w.start)||!finite(w.end)||!finite(w.rms_dbfs)||w.start<0||w.start<last||w.end<=w.start||w.end>duration+.1||w.rms_dbfs>0||w.rms_dbfs< -240)throw new Error('Invalid audio clock');last=w.end-.000001;}
  if(r.audio_present&&(!finite(r.audio_start)||r.audio_start<-.05||r.audio_start>duration||!r.audio_windows.length))throw new Error('Invalid audio origin');
  if(!r.audio_present&&r.audio_windows.length)throw new Error('Absent audio cannot have energy windows');
  if(r.audio_model){
   const m=r.audio_model,labels=['Dog','Bark','Yip','Howl','Bow-wow','Growling','Whimper (dog)'];
   if(m.model!=='MIT/ast-finetuned-audioset-10-10-0.4593'||m.revision!=='f826b80d28226b62986cc218e5cec390b1096902'||m.decision!=='abstain'||m.species_verified!==false||!Array.isArray(m.windows)||!m.windows.length||m.windows.length>60)throw new Error('Invalid audio model');
   for(const w of m.windows){if(!finite(w.start)||!finite(w.end)||w.start<0||w.end<=w.start||w.end>duration||!Array.isArray(w.dog_event_scores)||w.dog_event_scores.length!==7||new Set(w.dog_event_scores.map(s=>s.label)).size!==7||w.dog_event_scores.some(s=>!labels.includes(s.label)||!finite(s.score)||s.score<0||s.score>1))throw new Error('Invalid audio scores');}
  }
  if(r.audio_model?.candidate_events){
   const e=r.audio_model.candidate_events;
   if(e.validated!==false||e.decision!=='abstain'||!Array.isArray(e.candidates)||e.candidates.length>420)throw new Error('Invalid candidate policy');
   for(const c of e.candidates)if(!['Dog','Bark','Yip','Howl','Bow-wow','Growling','Whimper (dog)'].includes(c.label)||!finite(c.start)||!finite(c.end)||c.start<0||c.end<=c.start||c.end>duration||!Array.isArray(c.quality_flags)||c.quality_flags.some(x=>!['near_silence','clipping'].includes(x))||c.speaker!=='unconfirmed'||c.status!=='unvalidated_candidate')throw new Error('Invalid candidate envelope');
  }
  if(r.vision_model){
   const m=r.vision_model;
   if(m.model!=='HuggingFaceTB/SmolVLM2-256M-Video-Instruct'||m.revision!=='067788b187b95ebe7b2e040b3e4299e342e5b8fd'||m.decision!=='abstain'||m.species_verified!==false||!Array.isArray(m.observations)||!m.observations.length||m.observations.length>6)throw new Error('Invalid vision model');
   for(const o of m.observations)if(!finite(o.seconds)||o.seconds<0||o.seconds>duration||!['standing','sitting','lying','unknown'].includes(o.posture_candidate))throw new Error('Invalid posture candidate');
  }
  if(r.pose_model){
   const p=r.pose_model,names=['left_eye','right_eye','nose','neck','tail_root','left_shoulder','left_elbow','left_front_paw','right_shoulder','right_elbow','right_front_paw','left_hip','left_knee','left_back_paw','right_hip','right_knee','right_back_paw'];
   if(p.detector_model!=='PekingU/rtdetr_r50vd'||p.detector_revision!=='df939e661d8c52e80608d1ec566561aabd25a4e7'||p.keypoint_model!=='litert-community/RTMPose-Animal-AP10K-LiteRT'||p.keypoint_revision!=='1daee634c9db6889268124735374e6a9c1c2fc7b'||p.decision!=='abstain'||p.identity_verified!==false||p.species_verified!==false||p.confidence_kind!=='clipped_raw_simcc_peak_not_probability'||!Number.isInteger(p.width)||!Number.isInteger(p.height)||p.width<1||p.height<1||p.width*p.height>4000000||!Array.isArray(p.frames)||!p.frames.length||p.frames.length>6)throw new Error('Invalid dog pose models');
   let last=-1;
   for(const f of p.frames){
    if(!finite(f.seconds)||f.seconds<=last||f.seconds<0||f.seconds>duration||!Array.isArray(f.detections)||f.detections.length>4)throw new Error('Invalid dog detection timeline');last=f.seconds;
    for(const d of f.detections){
     if(!Array.isArray(d.box)||d.box.length!==4||d.box.some(v=>!finite(v))||d.box[0]<0||d.box[1]<0||d.box[2]<=d.box[0]||d.box[3]<=d.box[1]||d.box[2]>p.width||d.box[3]>p.height||!finite(d.score)||d.score<0||d.score>1||!/^clip-candidate-[0-9]{5}$/.test(d.track_candidate_id)||!d.keypoints||Object.keys(d.keypoints).length!==17)throw new Error('Invalid dog candidate');
     for(const [name,pt]of Object.entries(d.keypoints))if(!names.includes(name)||!finite(pt.x)||!finite(pt.y)||!finite(pt.confidence)||pt.x<0||pt.y<0||pt.x>p.width||pt.y>p.height||pt.confidence<0||pt.confidence>1)throw new Error('Invalid AP10K keypoint');
    }
   }
  }
  return r;
 }
 const api={normalize,summarize,plan,validateAlignment};if(typeof module!=='undefined')module.exports=api;else root.PetTimeline=api;
})(globalThis);
