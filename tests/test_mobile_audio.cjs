const assert=require('assert');
const audio=require('../backend/static/app/audio.js');
(async()=>{
 const samples=new Float32Array(1600);samples[0]=-2;samples[1]=2;
 const blob=audio.wav(samples),v=new DataView(await blob.arrayBuffer());
 assert.equal(v.getUint32(24,true),16000);assert.equal(v.getUint16(22,true),1);assert.equal(v.getInt16(44,true),-32768);assert.equal(v.getInt16(46,true),32767);assert.equal(v.getUint32(40,true),3200);
 assert.throws(()=>audio.wav(new Float32Array(1599)));assert.throws(()=>audio.wav(new Float32Array(160001)));
 samples[2]=NaN;assert.throws(()=>audio.wav(samples));
 const now=Date.now(),week=audio.week([{pet:'보리',at:now},{pet:'보리',at:now-1},{pet:'다른개',at:now-8*86400000},{pet:'미래',at:now+1}],now);
 assert.equal(week.count,2);assert.equal(week.pets.length,1);assert.equal(week.pets[0].days,1);
 let closed=false,mixed;
 global.window={AudioContext:class{async decodeAudioData(){return {duration:2,length:32000,sampleRate:16000,numberOfChannels:2,getChannelData:c=>new Float32Array(32000).fill(c?-.5:1)};}async close(){closed=true;}},OfflineAudioContext:class{constructor(ch,n,sr){this.length=n;this.destination={};}createBuffer(ch,n,sr){mixed=new Float32Array(n);return {getChannelData:()=>mixed};}createBufferSource(){return {connect(){},start(){}};}async startRendering(){return {getChannelData:()=>new Float32Array(this.length)};}}};
 const converted=await audio.convert(new Blob(['sound']),1);assert(closed);assert.equal(converted.seconds,1);assert.equal(mixed[0],.25);
 await assert.rejects(()=>audio.convert(new Blob(['sound']),3));await assert.rejects(()=>audio.convert(new Blob(['sound']),-1));await assert.rejects(()=>audio.convert(new Blob([]),0));
 console.log('WAV bounds/PCM clipping, mono segment conversion, cleanup, week filtering passed (Web Audio mocked).');
})().catch(e=>{console.error(e);process.exit(1)});
