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
 const api={normalize,summarize,plan};if(typeof module!=='undefined')module.exports=api;else root.PetTimeline=api;
})(globalThis);
