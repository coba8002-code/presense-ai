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
