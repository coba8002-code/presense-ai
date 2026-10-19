const element = id => document.getElementById(id);
const status = (text, error = false) => {
  element('status').textContent = text;
  element('status').className = error ? 'error' : '';
};
const labels = {model_unavailable: '소리 감지 · 학습 모델 미연결 — 행동 분석 보류',
  quiet: '조용한 구간', low_confidence: '근거 부족 — 행동 분석 보류',
  species_mismatch: '선택한 동물과 모델이 다릅니다 — 분석 보류',
  predicted: '실험용 모델 결과'};
let generation = 0;
let stream = null;
let context = null;
let worklet = null;
let controller = null;
let running = false;

function stop(message = '중지됨 — 마이크를 해제했습니다.') {
  generation++;
  running = false;
  controller?.abort();
  controller = null;
  if (worklet) { worklet.port.onmessage = null; worklet.disconnect(); }
  worklet = null;
  stream?.getTracks().forEach(track => track.stop());
  stream = null;
  if (context) context.close().catch(() => {});
  context = null;
  element('token').value = '';
  element('start').disabled = false;
  element('stop').disabled = true;
  element('species').disabled = false;
  status(message);
}

async function start() {
  if (running) return;
  const token = element('token').value.trim();
  const species = element('species').value;
  if (!token || !element('consent').checked) {
    status('연결 토큰과 음원 전송 동의가 필요합니다.', true);
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || !window.AudioWorkletNode) {
    status('마이크와 AudioWorklet을 지원하는 HTTPS 또는 localhost 브라우저가 필요합니다.', true);
    return;
  }
  running = true;
  const session = ++generation;
  element('start').disabled = true;
  element('stop').disabled = false;
  element('species').disabled = true;
  let busy = false;
  let dropped = 0;
  let latestSequence = -1;
  try {
    status('마이크 사용 권한을 확인하고 있습니다.');
    const acquired = await navigator.mediaDevices.getUserMedia({audio: {
      channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: false
    }});
    if (session !== generation) { acquired.getTracks().forEach(track => track.stop()); return; }
    stream = acquired;
    const audioContext = new AudioContext({sampleRate: 16000});
    context = audioContext;
    if (audioContext.sampleRate !== 16000) throw new Error('unsupported sample rate');
    await audioContext.audioWorklet.addModule('/realtime/capture.js');
    if (session !== generation) return;
    const node = new AudioWorkletNode(audioContext, 'pcm-chunker');
    worklet = node;
    audioContext.createMediaStreamSource(stream).connect(node);
    node.connect(audioContext.destination);
    for (const track of stream.getTracks()) track.onended = () => {
      if (session === generation) stop('마이크 연결이 끊어졌습니다. 다시 시작해 주세요.');
    };
    node.port.onmessage = async ({data}) => {
      if (session !== generation) return;
      latestSequence = data.sequence;
      if (!element('consent').checked) { stop('동의가 해제되어 마이크를 중지했습니다.'); return; }
      if (busy) { dropped++; element('metrics').textContent = `전송 대기 중 · 건너뛴 구간 ${dropped}개`; return; }
      if (data.rms < .02) { status('조용한 구간 · 음원은 전송하지 않습니다.'); return; }
      busy = true;
      const abort = new AbortController();
      controller = abort;
      const timeout = setTimeout(() => abort.abort(), 5000);
      const started = performance.now();
      try {
        const response = await fetch('/v1/audio/chunks', {
          method: 'POST', signal: abort.signal, cache: 'no-store',
          headers: {'Authorization': `Bearer ${token}`, 'Content-Type': 'application/octet-stream',
            'X-Audio-Consent': 'true', 'X-Audio-Species': species,
            'X-Audio-Sequence': String(data.sequence)}, body: data.pcm
        });
        if (!response.ok) {
          if ([401, 403, 503].includes(response.status)) {
            if (session === generation) stop('인증·동의 또는 서버 설정을 확인하고 다시 시작해 주세요.');
            return;
          }
          throw new Error('request failed');
        }
        const result = await response.json();
        if (session !== generation || data.sequence !== latestSequence) return;
        const prediction = result.prediction ? `\n라벨: ${result.prediction} (보정되지 않은 점수)` : '';
        status((labels[result.status] || '알 수 없는 분석 상태') + prediction);
        element('metrics').textContent = `녹음 구간 1초 · 요청 왕복 ${Math.round(performance.now() - started)}ms · 서버 처리 ${result.processing_ms}ms · 건너뛴 구간 ${dropped}개`;
      } catch {
        if (session === generation) status('전송 실패 또는 시간 초과 — 다음 구간에서 다시 시도합니다.', true);
      } finally {
        clearTimeout(timeout);
        if (session === generation) { busy = false; controller = null; }
      }
    };
    await audioContext.resume();
    if (session === generation) status('마이크 연결됨 · 1초 단위로 소리를 확인합니다.');
  } catch {
    if (session === generation) {
      stop();
      status('마이크 권한 또는 16 kHz 오디오 지원을 확인해 주세요.', true);
    }
  }
}

element('start').addEventListener('click', start);
element('stop').addEventListener('click', () => stop());
element('consent').addEventListener('change', () => { if (!element('consent').checked && running) stop('동의를 해제하여 중지했습니다.'); });
document.addEventListener('visibilitychange', () => { if (document.hidden && running) stop('화면을 떠나 마이크를 중지했습니다.'); });
window.addEventListener('pagehide', () => stop());
