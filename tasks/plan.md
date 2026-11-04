# Sprint 02 implementation plan

Source of requirements: AGENTS.md, docs/SPRINT02.md and issue #1.
The user explicitly authorized fresh bootstrap when source is missing and delivery
through a PR. The prior ZIP is unavailable; this is new code, not an import.

Build order: engineering skills -> backend/test foundation -> rights gate -> audio
training/evaluation -> VLM contract/adapter -> verification and PR against develop.

- Python 3.12, FastAPI, Pydantic, NumPy, httpx; stdlib unittest for offline tests.
- First transparent CPU baseline: standardized spectral features + softmax regression
  in NumPy. PyTorch deep models remain a later baseline, not a claimed delivery.
- One dog model per run (current dog-only scope); grounded event/context labels only. Local PCM WAV.
- Split globally by animal identity, never recordings; reject duplicate audio and
  unknown identity. Train normalization only on training animals. Validation selects
  regularization; test animals are evaluated once. Persist partitions and provenance.
- Registry must explicitly approve training and commercial rights and record consent,
  version, source and reviewer. Unknown rights fail closed before reading media.
- Report accuracy, macro F1, confusion matrix, per-class counts, Brier/ECE,
  abstention coverage and selective accuracy; no invented real-data scores.
- Cloud VLM disabled by default. Operator opt-in and per-request sharing consent,
  fixed HTTPS provider endpoint, bounded payloads, strict observed-posture enums,
  separate uncertain hypotheses, no free-form veterinary diagnosis fields.
- Stateless local development API; no media retention or public deployment.

Commands: `python -m unittest discover -s tests -v`,
`python -m uvicorn backend.app:app --host 127.0.0.1`,
`python -m training.run --help`, `python -m evaluation.evaluate --help`.

Boundary tests cover denied rights, split leakage, corrupt files, known metric
answers, deterministic synthetic training and VLM failure/consent paths. Tests
precede implementation; network mocks are only used at the paid provider boundary.

Threat model: untrusted manifests (path escape, duplicate media, forged metadata),
HTTP bodies (resource exhaustion), provider output (schema/prompt injection), and
API credentials (error leakage). Local registry is trusted reviewer policy, not
an authorization system for untrusted users. No external data downloads or paid calls.

Not included: missing ZIP recovery, real dataset access/approval, PyTorch model
training, fusion benchmarks, pet memory, Flutter capture/history, signed mobile
builds. These require the missing artifacts/data and subsequent focused PRs.

## 2026-10-17: automatic link knowledge and Notebook integration

User authorizes automated discovery, URL analysis and Notebook-style knowledge updates.
Implement official YouTube search/videos metadata -> policy-gated Gemini URL analysis ->
SQLite evidence store/search, with optional NotebookLM Enterprise source sync and local
approved audio-job scan. No browser-session scraping, credential acquisition or invented
rights. External keys/Enterprise configuration are absent; validate transports with mocks.

Slices: (1) strict schemas/providers and contract tests; (2) persistent worker, quotas,
idempotence, expiry/revocation and retrieval; (3) authenticated retrieval route, CLI,
example configuration/docs and CI. Acceptance: unknown rights never invoke analysis;
source instructions cannot affect hosts/permissions; failures retry safely without duplicate
Notebook creates; citations point to verified video IDs/time bounds; no model-training claims.
Trust boundaries: untrusted API metadata/LLM text vs operator policy, secrets, SQLite and
external writes. Fix API hosts, bound calls/bytes/duration, parameterize SQL, separate raw
observations/speaker statements/inferences, and exclude expired/revoked knowledge at read time.

## Broader animal video candidate intake

Implement discovery-only execution without Gemini/Notebook credentials and a read-only candidate inventory. Keep rights, expert labels and actual training readiness distinct. Validate discovery cannot call inference or Notebook writes. Google account/key connection additionally requested; browser tools unavailable in this session, so no account access or key creation claimed.

## VLM review and annotation validation

Add a read-only CLI to export current timestamped observations from the knowledge DB. Require explicit human-reviewed behavior labels, global animal/session IDs, a source-channel-scoped commercial training policy, and train/validation/test isolation. Bind proposal IDs to full analysis hash, model and analysis timestamp so stale approvals fail. Keep outputs annotation-only until authorized local media and actual models are validated. No inference, acquisition or deployment in this slice. Tests cover withdrawn/stale sources, fabricated emotional labels, unreviewed input, rights scope, duplicate reviews, and split leakage.

## User scope decision: dog-only MVP

Restrict public audio/demo and local training to dog. Keep provider species recognition schemas capable of identifying unsupported cat output, but abstain and clear visual behavior; filter cat knowledge, review export and new Notebook synchronization. Preserve existing audit/data history. Add rejection regressions and a browser option assertion; move cat delivery to future scope.

## VLM-04 local media binding

Validate current review/rights before media access; require acquisition permission and source/alignment attestations. Snapshot bounded local files, verify declared SHA-256, block duplicate content across source IDs, restrict FFmpeg protocols/formats and runtime, fully decode video, map source timestamps with a reviewed offset, and recheck policies/files before output. No video downloads or training. Real synthetic-container CLI tests plus malicious path/hash/offset/duplicate/timeout regressions. Perceptual duplicates and frame-level mapping remain explicit follow-ups.

## Local dog video review interface

Implement /review as static local-file UI: validated dog proposals, local video/offset playback, human labels and identity fields, explicit approval/revoke, strict CLI-compatible JSON download. No upload API or persistence; CSP blocks network connections. Escape untrusted observations using textContent; bound inputs and guard unsaved edits. Add HTTP asset tests and real Chromium synthetic-video playback/download integration in CI. Server-backed audit/roles, review resume and frame-accurate editing remain future work.

## 2026-10-18: Hybrid dog MVP design and evidence-first reprioritization

Design: [DOG_MVP_ARCHITECTURE.md](../docs/DOG_MVP_ARCHITECTURE.md). Start with user-selected short dog videos, a server-held VLM credential, and measurable observations. Reorder existing follow-ups toward evaluation contract, review resume, one live private-sample evaluation adapter and an actual quality/cost report. Defer broad near-duplicate/frame infrastructure until pilot evidence identifies required work. Then build authenticated upload/job/result flow and Flutter; on-device events and fine-tuning follow real metrics. Existing incomplete tasks remain preserved. This turn is planning/documentation only; targets and new endpoints are proposals, not implemented behavior.

## Lightweight VLM implementation (2026-10-18)
User-authorized extension: select official SmolVLM2 256M at pinned revision, implement
optional local-frame LoRA trainer and adapter inference. Validate rights and animal,
recording and source isolation before model download. CPU CI executes synthetic
optimizer/save/reload smoke; it cannot establish dog accuracy. Static posture labels
only; temporal walking and production deployment remain separate gates.

## Pretrained dog audio inference (2026-10-19 KST)
Dog2vec weight terms remain unverified; AVES repository MIT alone is insufficient
weight-specific evidence. Implement the reviewed BSD-3-Clause HF AST release as
an explicit fallback baseline, pinned revision and safetensors only. Bounded local
PCM16 WAV -> original multi-label scores -> dog-event subset, no emotion inference.
Unit-test input boundaries and label mapping before implementation; CPU CI loads
real weights and executes deterministic synthetic WAV inference. No dog accuracy claim.

## 2026-10-28: 제품화 실행 재정렬
기존 미완료 항목은 유지한다. 실행 상태의 기준은 tasks/todo.md의 EXEC 항목이다.
순서: 현황 대조(EXEC-00) → 로컬 계정/세션과 기록 격리(EXEC-01) → 저장·삭제·만료 계약 검증(EXEC-02) → 앱 명시적 서버 보관 연결(EXEC-03) → 실제 브라우저/모델 E2E(EXEC-04) → 국내 PC 데이터/독립 평가(EXEC-05) → 비동기 분석·운영 인증/보관(EXEC-06) → 파일럿/유료 실험(EXEC-07).
계정 기반은 국내 단일 PC 개발용 세션 발급 CLI로 시작한다. 계정 셀프가입·비밀번호·외부 결제는 포함하지 않는다. 기존 개발 토큰과 별도의 세션을 사용하고 보관 자료는 보호자 제출 기록으로 표시하며 모델 검증 자료로 자동 전환하지 않는다. 운영 인증 완료와 데이터 정확도 검증 완료는 별도 게이트다.
