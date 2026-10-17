# PetSense AI remaining work

Execution order and acceptance criteria: [작업지시서](../docs/WORK_ORDER.md).

## Implemented and locally verified
- [x] Review develop AGENTS.md, Sprint 02 and issue #1; report missing prior ZIP.
- [x] Install five pinned addyosmani skills and verify eleven skill/reference files.
- [x] Bootstrap FastAPI, dependency pins, unittest and GitHub Actions configuration.
- [x] Audit dataset sources/terms and implement a fail-closed rights gate.
- [x] Build WAV features, animal-disjoint partitions and deterministic CPU baseline.
- [x] Save model/splits/provenance; report F1, confusion, calibration and abstention.
- [x] Implement opt-in structured VLM adapter; validate consent and failure paths.
- [x] Run 22 tests, synthetic dog/cat CLI training and held-out replay; mutation probe.
- [x] Record owner's commercial-training approval separately from external rights.

## First PR delivery
- [x] Verify fresh dependency installation in [GitHub CI](https://github.com/coba8002-code/presense-ai/actions/runs/39018838044).
- [x] HTTP socket-server health verified by browser smoke in [CI](https://github.com/coba8002-code/presense-ai/actions/runs/39023577386).
- [ ] Run dependency vulnerability audit (pip-audit unavailable here).
- [x] Publish draft PR [#2](https://github.com/coba8002-code/presense-ai/pull/2) targeting develop.
- [x] Confirm backend GitHub CI passes on 7e23171: [successful run](https://github.com/coba8002-code/presense-ai/actions/runs/39018838044).
- [ ] Review and merge PR after remaining gates; merge not performed.

## Data and real model work
- [ ] Obtain prior PetSense_AI_AgentSkills_Integration.zip and reconcile with bootstrap.
- [ ] Barkopedia: select subset/revision, verify source-media rights and platform permissions.
- [ ] CatMeows/Meow-Net: obtain commercial permission or select an approved replacement.
- [ ] AP-10K: pin release, attribution, provenance and animal-identity mapping.
- [ ] Animal Kingdom: review access terms and commercial/source-media rights.
- [ ] Import approved media with global animal IDs and grounded labels; verify preprocessing.
- [ ] Train dog/cat models on approved real data; publish held-out metrics/model cards.
- [ ] Add and compare a PyTorch baseline; current baseline is NumPy softmax.

## Product development after baseline
- [ ] Validate VLM against real labeled images; paid calls require separate approval.
- [ ] Implement and compare audio-only / vision-only / fusion on the same held-out animals.
- [ ] Build per-pet history/feedback, retention, export and deletion controls.
- [ ] Flutter: recording/video, consent, results and history flows.
- [ ] Production authentication, distributed rate limits, privacy/security QA.
- [ ] Reproducible Android/iOS builds and device validation; Flutter SDK absent here.

## Work-order execution update

- [x] WO-02: add training.preflight CLI and malformed-policy/identity/path regression tests.
- [x] WO-01 partial: add offline dependency/environment diagnostics and CI push/manual entrypoints.
- [x] Full offline suite: 30 tests passed; synthetic dog/cat preflight passed.
- [x] WO-01 external checks: fresh dependency install and remote CI passed.
- [x] WO-01 socket smoke passed in Chromium/HTTP CI.
- [ ] WO-01 remaining: dependency vulnerability audit.
- [ ] WO-03 onward: follow the prerequisites in WORK_ORDER.md; no real-data or paid calls claimed.

## Near-real-time audio slice

- [x] One-second PCM capture, local sound-activity gate and bounded uploads.
- [x] Authenticated/consented chunk API, request limits and explicit model-unavailable status.
- [x] Shared training/serving features; reviewed-model loader rejects synthetic artifacts.
- [x] Local Python suite: 44 passed; AudioWorklet Node checks passed.
- [x] Real Chromium/fake microphone/HTTP smoke passed in [CI](https://github.com/coba8002-code/presense-ai/actions/runs/39023577386).
- [ ] Physical microphone/device latency and behavior model validation.
- [ ] Flutter streaming capture and event-triggered VLM video sampling.

### Automatic learning (2026-10-17)

- [x] Local watched job queue, rights/acquisition/label-review gates, content-addressed results.
- [x] Animal/session/content isolation, snapshot verification, job locking and safe retries.
- [x] Re-evaluate candidate/incumbent on one acceptance benchmark; preserve artifacts without deployment.
- [x] Synthetic CLI smoke and 12 new regression tests (56 total Python tests).
- [ ] Licensed real audio/video intake and expert annotation workflow.
- [ ] Pretrained audio adapter and multimodal/video training.
- [ ] Locked final real-world evaluation, service installation and resource quotas.

### Automated video-link knowledge (2026-10-17)

- [x] Official YouTube/Gemini/Notebook Enterprise adapters with validated payloads.
- [x] Persistent discovery/analysis, quota budget, deduplication and policy/expiry checks.
- [x] Source-linked local retrieval and optional approved audio queue execution.
- [ ] Offline transport tests, docs, current-head CI and PR update.
- [ ] Live credentials/Enterprise provisioning and authorized source policies (external prerequisite).

### Broader video candidate intake

- [x] Discovery-only mode and offline candidate review status.
- [x] Regression tests distinguish analyzed evidence from training-ready labels.
- [ ] General web source connectors, multilingual rotation and paginated discovery.
- [ ] Expert video annotation, training rights and authorized media acquisition workflow.
- [ ] Video training export, animal-disjoint evaluation and gated model release.
- [ ] Google AI Studio credentials connection (browser access unavailable).

## VLM 활용·학습 우선순위

구체적인 완료 기준: [VLM_TRAINING_TODO.md](../docs/VLM_TRAINING_TODO.md).

- [x] VLM-01: 유효한 영상 관찰을 해시·출처·시각과 함께 검수 후보로 내보내기.
- [x] VLM-02: 검수된 행동 라벨·전역 동물 ID·촬영 세션 계약.
- [x] VLM-03: 변경/철회/중복 후보와 개체·영상·세션 분할 누출 차단.
- [ ] VLM-04/05: 승인된 로컬 영상 연결, 중복 검사 및 검수 UI.
- [ ] VLM-06/07: 실제 VLM 평가와 AST·자세 모델 설치/추론 검증.
- [ ] VLM-08/09: 행동 전이학습·융합 비교 및 실시간 영상 구간 처리.
