'use strict';
const PetSenseAudio=(()=>{
 function wav(samples){
  if(!(samples instanceof Float32Array)||samples.length<1600||samples.length>160000||!samples.every(Number.isFinite))throw new Error('0.1~10초의 유효한 소리가 필요합니다.');
  const b=new ArrayBuffer(44+samples.length*2),v=new DataView(b);
  const str=(o,s)=>{for(let i=0;i<s.length;i++)v.setUint8(o+i,s.charCodeAt(i));};
  str(0,'RIFF');v.setUint32(4,b.byteLength-8,true);str(8,'WAVE');str(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,16000,true);v.setUint32(28,32000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);str(36,'data');v.setUint32(40,samples.length*2,true);
  samples.forEach((x,i)=>{x=Math.max(-1,Math.min(1,x));v.setInt16(44+i*2,Math.round(x*(x<0?32768:32767)),true);});
  return new Blob([b],{type:'audio/wav'});
 }
 async function convert(file,start=0){
  if(!file||file.size>20*1024*1024||file.size===0)throw new Error('20MB 이하의 음성 파일을 선택하세요.');
  if(!Number.isFinite(start)||start<0)throw new Error('시작 시간은 0 이상의 초 단위입니다.');
  const AC=window.AudioContext||window.webkitAudioContext,OC=window.OfflineAudioContext||window.webkitOfflineAudioContext;
  if(!AC||!OC)throw new Error('이 브라우저에서 음성 변환을 지원하지 않습니다. 최신 브라우저 또는 변환된 WAV를 사용하세요.');
  const ac=new AC();let decoded;
  try{decoded=await ac.decodeAudioData(await file.arrayBuffer());}catch(e){throw new Error('음성을 읽지 못했습니다. 이 브라우저가 지원하는 WAV·MP3·M4A 파일을 선택하세요.');}finally{await ac.close();}
  const seconds=Math.min(10,decoded.duration-start);
  if(seconds<0.1)throw new Error('선택 구간에 최소 0.1초의 소리가 필요합니다.');
  const frames=Math.floor(seconds*16000),offline=new OC(1,frames,16000);
  // Copy only the selected interval into mono, avoiding channel-layout dependent mixing.
  const begin=Math.floor(start*decoded.sampleRate),count=Math.min(decoded.length-begin,Math.ceil(seconds*decoded.sampleRate));
  const mono=offline.createBuffer(1,count,decoded.sampleRate),data=mono.getChannelData(0);
  for(let c=0;c<decoded.numberOfChannels;c++){
   const channel=decoded.getChannelData(c);
   for(let i=0;i<count;i++)data[i]+=channel[begin+i]/decoded.numberOfChannels;
  }
  const source=offline.createBufferSource();source.buffer=mono;source.connect(offline.destination);source.start();
  const rendered=await offline.startRendering();
  return {blob:wav(rendered.getChannelData(0)),start,seconds:frames/16000,sourceSeconds:decoded.duration};
 }
 function week(records,now=Date.now()){
  const start=now-7*86400000,valid=records.filter(r=>r.at>=start&&r.at<=now);
  const pets=new Map();for(const r of valid){const x=pets.get(r.pet)||{pet:r.pet,count:0,days:new Set()};x.count++;x.days.add(new Date(r.at).toLocaleDateString('ko-KR',{timeZone:'Asia/Seoul'}));pets.set(r.pet,x);}
  return {count:valid.length,pets:[...pets.values()].map(x=>({pet:x.pet,count:x.count,days:x.days.size})),records:valid};
 }
 return {wav,convert,week};
})();
if(typeof module!=='undefined')module.exports=PetSenseAudio;
