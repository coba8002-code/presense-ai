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
  return r;
 }
 const api={normalize,summarize,plan,validateAlignment};if(typeof module!=='undefined')module.exports=api;else root.PetTimeline=api;
})(globalThis);
