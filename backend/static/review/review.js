const el = id => document.getElementById(id);
const fields = ['label', 'animal_id', 'recording_group', 'dataset', 'split', 'reviewer', 'review_evidence'];
let rows = [], selected = null, videoURL = null, videoSource = null, clipEnd = null, generation = 0, dirty = false, formEdited = false;
const approved = new Map();
const video = el('video');
function status(text, error = false) { el('status').textContent = text; el('status').classList.toggle('error', error); }
function clearVideo(resetInput = true) {
  video.pause(); video.removeAttribute('src'); video.load();
  if (videoURL) URL.revokeObjectURL(videoURL);
  videoURL = null; videoSource = null; clipEnd = null;
  if (resetInput) el('video-file').value = '';
  el('offset').value = '0'; el('confirmed').checked = false;
  el('play').disabled = true; el('approve').disabled = true;
  el('video-status').textContent = '선택한 원본의 로컬 영상을 열어 주세요.';
}
function interval() {
  if (!selected || video.error || video.readyState < 1 || videoSource !== selected.source_id || !Number.isFinite(video.duration)) return null;
  const offset = Number(el('offset').value);
  const start = selected.observation.start_seconds - offset, end = selected.observation.end_seconds - offset;
  if (el('offset').value === '' || !Number.isFinite(offset) || offset < 0 || offset > 1800 || start < 0 || end <= start || end > video.duration) return null;
  return {start, end};
}
function refreshVideo() {
  const range = interval(); el('play').disabled = !range; el('approve').disabled = !range;
  el('video-status').textContent = range ? `로컬 구간 ${range.start.toFixed(3)}–${range.end.toFixed(3)}초 · 전체 ${video.duration.toFixed(3)}초` : '영상 또는 시작 위치를 확인하세요. 관찰 구간이 영상 범위 안에 있어야 합니다.';
}
function refreshList() {
  const current = selected?.proposal_id;
  el('candidate').replaceChildren(...rows.map((row, i) => {
    const option = document.createElement('option'); option.value = row.proposal_id;
    option.textContent = `${approved.has(row.proposal_id) ? '✓' : '○'} ${i + 1}. ${row.source_id} · ${row.observation.start_seconds}초`;
    return option;
  }));
  if (current) el('candidate').value = current;
  el('count').textContent = `후보 ${rows.length} · 승인 ${approved.size}`;
  el('export').disabled = approved.size === 0;
  el('remove').disabled = !current || !approved.has(current);
}
function select(id) {
  const next = rows.find(row => row.proposal_id === id);
  if (!next) return;
  if (selected?.source_id !== next.source_id) clearVideo();
  video.pause(); clipEnd = null; selected = next;
  el('review-form').reset(); formEdited = false;
  const saved = approved.get(id);
  for (const field of fields) el(field).value = saved?.[field] ?? (field === 'split' ? 'train' : '');
  el('source').textContent = `원본 ${next.source_id} · 개 · 미보정 확신도 ${next.observation.confidence}`;
  el('citation').hidden = false;
  el('citation').href = `https://www.youtube.com/watch?v=${next.source_id}&t=${next.observation.start_seconds}s`;
  el('observation').textContent = next.observation.text;
  el('timing').textContent = `원본 구간 ${next.observation.start_seconds}–${next.observation.end_seconds}초`;
  refreshList(); refreshVideo();
}
function validate(data) {
  if (!Array.isArray(data) || !data.length || data.length > 6000) throw new Error();
  const ids = new Set();
  for (const row of data) {
    const o = row?.observation;
    if (row?.species !== 'dog' || typeof row.proposal_id !== 'string' || typeof row.source_id !== 'string' || !/^[a-f0-9]{64}$/.test(row.proposal_id) || ids.has(row.proposal_id)
      || !/^[A-Za-z0-9_-]{11}$/.test(row.source_id) || !Number.isFinite(row.analyzed_at) || row.analyzed_at <= 0 || row.analyzed_at > Date.now()/1000
      || o?.kind !== 'observation' || typeof o.text !== 'string' || !o.text.trim() || o.text.length > 1200
      || !Number.isInteger(o.start_seconds) || !Number.isInteger(o.end_seconds) || o.start_seconds < 0 || o.end_seconds <= o.start_seconds || o.end_seconds > 1800
      || !Number.isFinite(o.confidence) || o.confidence < 0 || o.confidence > 1) throw new Error();
    ids.add(row.proposal_id);
  }
  return data;
}
el('proposals').addEventListener('change', async () => {
  const file = el('proposals').files[0]; const attempt = ++generation;
  if (!file) return;
  if ((dirty || approved.size) && !window.confirm('현재 작업을 비우고 새 후보를 열까요? 먼저 내보내기를 완료했는지 확인하세요.')) { el('proposals').value = ''; return; }
  try {
    if (file.size > 8000000) throw new Error();
    const incoming = validate(JSON.parse(await file.text()));
    if (attempt !== generation) return;
    clearVideo(); rows = incoming; approved.clear(); dirty = false; selected = null;
    select(rows[0].proposal_id); status(`${rows.length}개 관찰을 열었습니다. 원본과 로컬 영상의 일치 여부를 확인하세요.`);
  } catch { if (attempt === generation) status('파일을 열지 못했습니다. 개 관찰 후보 JSON과 파일 크기(8 MB 이하)를 확인하세요.', true); }
});
el('candidate').addEventListener('change', () => {
  if (formEdited && !window.confirm('승인 버튼을 누르지 않은 변경사항을 버리고 이동할까요?')) { el('candidate').value = selected.proposal_id; return; }
  select(el('candidate').value);
});
el('video-file').addEventListener('change', () => {
  const file = el('video-file').files[0]; clearVideo(false);
  if (!file || !selected) return;
  if (file.size > 128 * 1024 * 1024 || file.size === 0) { status('영상은 128 MiB 이하의 파일을 선택하세요.', true); return; }
  videoURL = URL.createObjectURL(file); videoSource = selected.source_id;
  video.src = videoURL; el('confirmed').checked = false;
});
video.addEventListener('loadedmetadata', refreshVideo);
video.addEventListener('error', () => { el('confirmed').checked = false; el('approve').disabled = true; el('play').disabled = true; status('이 브라우저에서 영상을 재생할 수 없습니다.', true); });
el('offset').addEventListener('input', () => { video.pause(); clipEnd = null; el('confirmed').checked = false; refreshVideo(); });
el('play').addEventListener('click', async () => {
  const range = interval(); if (!range) return;
  video.currentTime = range.start; clipEnd = range.end;
  try { await video.play(); } catch { status('영상 재생을 시작하지 못했습니다.', true); }
});
video.addEventListener('timeupdate', () => { if (clipEnd !== null && video.currentTime >= clipEnd) { video.pause(); clipEnd = null; } });
el('review-form').addEventListener('input', () => { dirty = true; formEdited = true; });
el('review-form').addEventListener('submit', event => {
  event.preventDefault();
  if (!selected || !interval() || !el('confirmed').checked || !el('review-form').reportValidity()) return;
  const record = {proposal_id: selected.proposal_id, decision: 'approved'};
  for (const field of fields) {
    const value = el(field).value.trim();
    if (!value || ['unknown','none','null','pending'].includes(value.toLowerCase())) { status('식별자와 검수 근거를 구체적으로 입력하세요.', true); return; }
    record[field] = value;
  }
  record.reviewed_at = Math.floor(Date.now()/1000);
  if (record.reviewed_at < selected.analyzed_at) { status('분석 이후 시각에 검수해야 합니다.', true); return; }
  approved.set(selected.proposal_id, record); dirty = true; formEdited = false; refreshList(); status('검수 기록을 승인 목록에 담았습니다. 파일로 내보내 주세요.');
});
el('remove').addEventListener('click', () => { if (!selected) return; approved.delete(selected.proposal_id); dirty = true; el('confirmed').checked = false; refreshList(); status('승인을 취소했습니다. 변경된 목록을 다시 내보내세요.'); });
el('export').addEventListener('click', () => {
  if (!approved.size) return;
  if (formEdited) { status('입력 중인 변경사항을 승인하거나 취소한 뒤 내보내세요.', true); return; }
  const url = URL.createObjectURL(new Blob([JSON.stringify([...approved.values()], null, 2)], {type:'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = 'video-reviews.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
  status('다운로드 파일을 확인하세요. 현재 권한·분할·영상 검증은 CLI에서 다시 실행해야 합니다.');
});
el('reset').addEventListener('click', () => {
  if ((dirty || approved.size) && !window.confirm('다운로드한 파일을 확인했나요? 현재 작업을 모두 비웁니다.')) return;
  generation++; clearVideo(); rows = []; selected = null; approved.clear(); dirty = false;
  el('proposals').value = ''; el('review-form').reset(); formEdited = false; refreshList(); el('citation').hidden = true;
  el('source').textContent = '선택한 관찰이 없습니다.'; el('observation').textContent = 'VLM 관찰이 여기에 표시됩니다.'; el('timing').textContent = ''; status('작업을 초기화했습니다.');
});
window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
