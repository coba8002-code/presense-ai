'use strict';
const $=id=>document.getElementById(id), KEY='petsense.observations.v1';
let candidate=null,records=[],recorded=null,recording=null,recordBusy=false,recordingGeneration=0;
const labels={'Dog':'개 소리','Bark':'짖음','Yip':'짧고 높은 소리','Howl':'하울링','Bow-wow':'연속 짖음','Growling':'으르렁거림','Whimper (dog)':'낑낑거림'};
function text(tag,value,parent){const el=document.createElement(tag);el.textContent=value;parent.append(el);return el;}
function render(){const w=PetSenseAudio.week(records);$('weekly').replaceChildren();text('h3','최근 7일의 관찰 기록',$('weekly'));text('p',`${w.count}개 기록 · 한국 시간 기준 날짜 · 같은 이름은 합산됩니다.`,$('weekly'));for(const p of w.pets)text('p',`${p.pet}: ${p.count}개 기록 / ${p.days}일에 기록`,$('weekly'));text('p','기록량은 실제 짖음 빈도·상태 개선을 뜻하지 않습니다. 비교에는 같은 관찰 시간과 조건이 필요합니다.',$('weekly')); $('records').replaceChildren();$('count').textContent=`저장된 관찰 ${records.length}개 · 기록 수는 행동 빈도를 의미하지 않습니다.`;for(const r of [...records].reverse()){const el=text('article','',$('records'));el.className='record';text('strong',`${r.pet} · ${new Date(r.at).toLocaleString('ko-KR')}`,el);text('p',r.context||'상황 기록 없음',el);text('p','소리 사건 점수 기록 · 감정과 원인 판단 보류',el);const b=text('button','이 기록 삭제',el);b.className='secondary';b.onclick=()=>{const next=records.filter(x=>x.id!==r.id);persist(next);};}}
function persist(next){try{localStorage.setItem(KEY,JSON.stringify(next));records=next;render();return true;}catch(e){$('status').textContent='브라우저 저장에 실패했습니다. 저장 공간과 설정을 확인하세요.';return false;}}
try{const raw=JSON.parse(localStorage.getItem(KEY)||'[]');if(Array.isArray(raw))records=raw.filter(r=>r&&typeof r.id==='string'&&typeof r.pet==='string'&&typeof r.context==='string'&&Number.isFinite(r.at)).slice(-100);}catch(e){$('status').textContent='저장된 기록을 읽을 수 없습니다.';}render();
let activeAnalysis=null;
globalThis.PetSenseAnalysisInput=()=>({file:recorded||$('audio').files[0],start:recorded?0:Number($('start').value)});
function cancelAnalysis(message='분석 요청을 취소했습니다. 이미 전송된 소리의 서버 처리는 잠시 계속될 수 있습니다.'){
 const task=activeAnalysis;if(!task)return;
 activeAnalysis=null;clearTimeout(task.timer);task.controller.abort();
 candidate=null;$('save').hidden=true;$('result').replaceChildren();$('submit').disabled=false;$('cancel-analysis').hidden=true;$('status').textContent=message;
}
$('cancel-analysis').onclick=()=>cancelAnalysis();
$('analysis-form').onsubmit=async event=>{
 event.preventDefault();if(activeAnalysis||recordBusy||!$('consent').checked)return;
 candidate=null;$('save').hidden=true;$('result').replaceChildren();
 const file=recorded||$('audio').files[0];
 if(!file){$('status').textContent='녹음하거나 음성 파일을 선택하세요.';return;}
 const task={controller:new AbortController(),timer:null};activeAnalysis=task;
 const context=$('context').value,pet=$('pet').value;
 const headers={'Content-Type':'audio/wav','X-Audio-Consent':'true','X-Audio-Species':'dog'};
 if($('auth-mode').value==='account')headers['X-PetSense-Session']=$('notes-session').value;
 else headers.Authorization=`Bearer ${$('token').value}`;
 $('submit').disabled=true;$('cancel-analysis').hidden=false;
 $('status').textContent='소리를 준비하고 분석합니다. 첫 실행에는 모델 준비 시간이 필요합니다.';
 task.timer=setTimeout(()=>{if(activeAnalysis===task)cancelAnalysis('분석 대기 시간이 길어 요청을 중단했습니다. 서버 준비 상태를 확인한 후 다시 시도하세요.');},90000);
 try{
  const input=await PetSenseAudio.convert(file,recorded?0:Number($('start').value));
  if(activeAnalysis!==task)return;
  if(!$('consent').checked)throw new Error('분석 동의가 해제되었습니다.');
  let response;
  try{response=await fetch('/v1/audio/events',{method:'POST',signal:task.controller.signal,headers,body:input.blob});}
  catch(error){if(task.controller.signal.aborted)throw error;throw new Error('서버에 연결하지 못했습니다. 연결 상태를 확인한 뒤 직접 다시 시도하세요.');}
  if(!response.ok){
   const messages={401:'인증 방식과 서버 토큰 또는 계정 세션을 확인하세요.',403:'분석 동의가 필요합니다.',408:'소리 업로드 시간이 초과되었습니다. 연결을 확인하고 다시 시도하세요.',413:'파일이 너무 큽니다.',415:'WAV 파일을 선택하세요.',422:'16kHz PCM16, 0.1~10초 WAV인지 확인하세요.',429:'분석 요청이 많습니다. 잠시 후 직접 다시 시도하세요.',503:'서버의 AST 모델 설정이나 준비 상태를 확인하세요.',504:'서버 분석 대기 시간이 초과되었습니다. 잠시 후 다시 시도하세요.'};
   throw new Error(messages[response.status]||'분석을 완료하지 못했습니다.');
  }
  const result=await response.json();
  if(activeAnalysis!==task)return;
  if(result.decision!=='abstain'||!Array.isArray(result.dog_event_scores)||!result.dog_event_scores.length||!result.dog_event_scores.every(x=>typeof x.label==='string'&&Number.isFinite(x.score)&&x.score>=0&&x.score<=1))throw new Error('예상한 분석 결과 형식과 다릅니다.');
  text('p',`선택 구간: ${input.start.toFixed(1)}초부터 ${input.seconds.toFixed(1)}초 / 원본 ${input.sourceSeconds?.toFixed(1)||'?'}초`,$('result'));
  const n=text('p','감정·원인 판단 보류',$('result'));n.className='notice';
  for(const score of result.dog_event_scores){const row=text('div','',$('result'));row.className='score';text('span',labels[score.label]||score.label,row);text('span',score.score.toFixed(3),row);const bar=document.createElement('progress');bar.max=1;bar.value=score.score;bar.setAttribute('aria-label',labels[score.label]||score.label);row.append(bar);}
  candidate={id:crypto.randomUUID(),at:Date.now(),pet,context,result,segment:{start:input.start,seconds:input.seconds}};
  $('save').hidden=false;$('status').textContent='분석을 마쳤습니다. 저장 버튼을 누르면 이 브라우저에 결과가 남습니다.';
 }catch(e){if(activeAnalysis===task)$('status').textContent=e.message||'연결을 확인하세요.';}
 finally{clearTimeout(task.timer);if(activeAnalysis===task){activeAnalysis=null;$('submit').disabled=false;$('cancel-analysis').hidden=true;}}
};
$('save').onclick=()=>{if(candidate&&persist([...records,candidate].slice(-100))){candidate=null;$('save').hidden=true;$('status').textContent='기록을 저장했습니다. 원본 음성은 저장하지 않았습니다.';}};
$('clear').onclick=()=>{if(confirm('이 브라우저에 저장한 관찰 기록을 모두 삭제할까요?')){try{localStorage.removeItem(KEY);records=[];render();$('status').textContent='저장 기록을 삭제했습니다.';}catch(e){$('status').textContent='삭제하지 못했습니다. 브라우저 사이트 데이터를 확인하세요.';}}};
$('export').onclick=()=>{const blob=new Blob([JSON.stringify({format_version:1,records},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='petsense-observations.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};

function download(value,name,type){const blob=new Blob([value],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('consult').onclick=()=>{const w=PetSenseAudio.week(records);const lines=['PetSense AI 상담 준비 노트','최근 7일, 작성: '+new Date().toLocaleString('ko-KR',{timeZone:'Asia/Seoul'}),'보호자 기록이며 진단·행동 개선 판정이 아닙니다.','기록은 브라우저에 남은 최대 100개에서 집계됩니다.',''];for(const r of w.records){lines.push(r.pet+' / '+new Date(r.at).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'}),r.context||'상황 미입력','모델: '+String(r.result?.model||'미기록'),'감정·원인 판단 보류','');}download(lines.join('\n'),'petsense-consultation.txt','text/plain;charset=utf-8');};
function release(session){clearTimeout(session.timer);session.stream.getTracks().forEach(t=>t.stop());if(recording===session){recording=null;recordBusy=false;$('record').disabled=false;$('stop').hidden=true;$('cancel-record').hidden=true;}}
function stopRecording(cancel=false){if(cancel)recordingGeneration++;const s=recording;if(!s)return;s.cancel=cancel;try{if(s.recorder.state!=='inactive')s.recorder.stop();}finally{clearTimeout(s.timer);s.stream.getTracks().forEach(t=>t.stop());}if(cancel){recorded=null;$('record-status').textContent='녹음을 취소했습니다.';}}
$('record').onclick=async()=>{if(recordBusy)return;if(!$('consent').checked){$('record-status').textContent='분석 동의를 확인한 뒤 녹음하세요.';return;}if(!navigator.mediaDevices?.getUserMedia||typeof MediaRecorder==='undefined'){ $('record-status').textContent='마이크 녹음은 HTTPS 또는 localhost의 지원 브라우저에서 사용할 수 있습니다. 음성 파일을 선택해 주세요.';return;}recordBusy=true;$('record').disabled=true;recorded=null;const generation=++recordingGeneration;try{const stream=await navigator.mediaDevices.getUserMedia({audio:true});if(generation!==recordingGeneration||!$('consent').checked){stream.getTracks().forEach(t=>t.stop());throw new Error('동의가 해제되었습니다.');}let recorder;try{recorder=new MediaRecorder(stream);}catch(e){stream.getTracks().forEach(t=>t.stop());throw e;}const s={stream,recorder,chunks:[],cancel:false,timer:null};recording=s;recorder.ondataavailable=e=>{if(e.data.size)s.chunks.push(e.data);};recorder.onstop=()=>{const current=recording===s;release(s);if(current&&!s.cancel){recorded=new Blob(s.chunks,{type:recorder.mimeType});$('record-status').textContent='녹음 완료. 분석하기를 누르면 전송됩니다.';}s.chunks=[];};recorder.onerror=()=>{s.cancel=true;release(s);$('record-status').textContent='녹음에 실패했습니다. 다시 시도하거나 파일을 선택하세요.';};recorder.start();s.timer=setTimeout(()=>stopRecording(),10000);$('stop').hidden=false;$('cancel-record').hidden=false;$('record-status').textContent='녹음 중 · 최대 10초 후 자동 종료';}catch(e){recordBusy=false;$('record').disabled=false;$('record-status').textContent='마이크 권한과 연결을 확인하세요. '+e.message;}};
$('stop').onclick=()=>stopRecording();$('cancel-record').onclick=()=>stopRecording(true);
$('audio').onchange=()=>{cancelAnalysis('파일이 변경되어 이전 요청을 취소했습니다.');stopRecording(true);recorded=null;$('record-status').textContent='선택한 음성 파일을 사용합니다.';};
$('consent').onchange=()=>{if(!$('consent').checked){cancelAnalysis('동의가 해제되어 요청을 취소했습니다.');stopRecording(true);recorded=null;}};
window.addEventListener('pagehide',()=>{cancelAnalysis();stopRecording(true);});
