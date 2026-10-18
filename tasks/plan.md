# Sprint 02 implementation plan

Source of requirements: AGENTS.md, docs/SPRINT02.md and issue #1.
The user explicitly authorized fresh bootstrap when source is missing and delivery
through a PR. The prior ZIP is unavailable; this is new code, not an import.

Build order: engineering skills -> backend/test foundation -> rights gate -> audio
training/evaluation -> VLM contract/adapter -> verification and PR against develop.

- Python 3.12, FastAPI, Pydantic, NumPy, httpx; stdlib unittest for offline tests.
- First transparent CPU baseline: standardized spectral features + softmax regression
  in NumPy. PyTorch deep models remain a later baseline, not a claimed delivery.
- One dog or cat model per run; grounded event/context labels only. Local PCM WAV.
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
