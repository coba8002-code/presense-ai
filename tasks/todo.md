# PetSense AI remaining work

Current scope: **dog-only MVP**. Historical completed work below may describe the earlier two-species bootstrap.

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
- [ ] AP-10K: pin release, attribution, provenance and animal-identity mapping.
- [ ] Animal Kingdom: review access terms and commercial/source-media rights.
- [ ] Import approved media with global animal IDs and grounded labels; verify preprocessing.
- [ ] Train dog models on approved real data; publish held-out metrics/model cards.
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
- [x] VLM-04: 승인된 로컬 영상 연결, 동일 파일 중복·디코딩·초 단위 주석 구간 검사.
- [x] VLM-05: 로컬 영상 검수 화면, 승인/취소 및 CLI 호환 JSON 출력.
- [ ] VLM-04/05 후속: 유사 영상 중복·프레임 정렬, 검수 재개·공동 저장·감사 인증.
- [ ] VLM-06/07: 실제 VLM 평가와 AST·자세 모델 설치/추론 검증.
- [ ] VLM-08/09: 행동 전이학습·융합 비교 및 실시간 영상 구간 처리.

## Dog-only MVP scope

- [x] Dog-only demo selection, live audio API/model and training/preflight gates.
- [x] Non-dog VLM abstention; exclude cat knowledge and review candidates.
- [x] Regression coverage for cat rejection and preserved dog behavior.
- [x] Authorized local dog video binding, SHA-256 duplicate checks, full decode and second-based annotation bounds.
- [ ] Next: perceptual duplicates, frame-level alignment and actual video model.

## Deferred: cat support

- [ ] CatMeows/Meow-Net commercial permissions or approved replacement.
- [ ] Cat-specific audio/behavior labels, expert review and separate evaluation.
- [ ] Re-enable product support only after cat validation.

## 하이브리드 개 MVP 실행 계획 — 2026-10-18 우선순위

설계 근거: [DOG_MVP_ARCHITECTURE.md](../docs/DOG_MVP_ARCHITECTURE.md). 기존 미완료 항목을 삭제하지 않고 아래 순서로 재정렬한다. 문서의 수치·인프라·API는 제안이며 아직 구현된 동작이 아니다.

### P0 — 실제 평가 계약과 정답 파일 (최우선, M)
- [ ] standing/sitting/lying/walking, unknown/유보, 평가 단위와 구간 매칭 규칙을 고정한다.
- [ ] 원본 권한·개체/가정/세션·분할·전문가 라벨의 JSON 계약과 소규모 합성 형식 예제를 만든다.
- [ ] 전문가가 VLM 답변을 보기 전 정답을 작성하고 일부 이중 검수·불일치 기록을 남기게 한다.
검증: 평가 계약 입력의 경계/분할 테스트와 검수 가능한 예제. 의존: 없음. 예상 파일: evaluation/video_contract.py, tests/test_video_contract.py, docs/VIDEO_EVALUATION.md. 실제 샘플은 별도 확보해야 한다.

### P1 — 검수 파일 작업 재개 (M)
- [ ] 승인 JSON을 현재 후보와 대조해 불러오고 변경/누락/중복 항목을 보고한다.
- [ ] 로컬 임시 저장은 명시적으로 선택하게 하고 저장 위치·삭제·복구를 제공한다.
- [ ] 영상 자체를 저장하거나 업로드하지 않으며 복구된 검수가 현재 권한 승인을 뜻하지 않도록 표시한다.
검증: 실제 브라우저 저장→재시작→복구→철회/변경 후보 처리. 의존: 현재 /review. 예상 파일: review.js, index.html, review_browser_smoke.py, REVIEW_UI.md.

### P2 — 실제 비공개 샘플 VLM 평가 CLI (M)
- [ ] 한 공급자의 실제 영상 입력 계약을 공식 문서로 확인하고 고정 모델/프롬프트/시간표시 결과를 저장한다.
- [ ] 운영자가 설정한 키·전송 동의·비용 한도 없이는 외부 호출하지 않고, 실패·유보·재시도를 구분한다.
- [ ] 사용량·시간·버전을 원본 개인정보 없이 기록하고 출력 필드를 평가 계약에 맞춘다.
검증: MockTransport 계약/비용 게이트 + 승인된 실제 샘플 1건 E2E. 의존: P0, 실제 인증·비용 범위·허가된 자료. 예상 파일: backend/video_provider.py, evaluation/video_run.py, tests/test_video_provider.py, VIDEO_EVALUATION.md.

### P3 — 실제 성능·비용 보고 (M)
- [ ] 전문가 정답과 예측을 비교해 행동별 성능·유보/coverage·시간 오차·실패 사례를 산출한다.
- [ ] 개체/가정 단위 분리와 신뢰구간, 요청 비용 및 p50/p95를 함께 보고한다.
- [ ] validation으로 정한 모델·임계값을 고정하고 최종 test를 개발용 반복 데이터로 쓰지 않는다.
검증: 알려진 정답의 지표 테스트, 실제 결과 재생으로 동일 보고서 생성. 의존: P0/P2 및 실제 정답 데이터. 예상 파일: evaluation/video_metrics.py, evaluation/video_report.py, tests/test_video_metrics.py, docs/VIDEO_BASELINE_REPORT.md.

### 체크포인트 A — 실제 제품 가치 판단
- [ ] 실제 분석이 기준을 충족하는지, 어떤 행동/환경을 제외해야 하는지 확인한다.
- [ ] 데이터가 부족하면 추가 학습보다 먼저 수집·검수 계획을 조정한다.
- [ ] 비용·품질 결과에 따라 다음 제품 구현 범위를 확정한다. 합성 테스트만으로 통과하지 않는다.

### P4a — 개인 인증과 개 소유권 (M)
- [ ] 앱용 사용자 인증을 도입하고 사용자/개/작업 소유권을 강제한다.
- [ ] 공유 개발 토큰이 운영 앱에 포함되지 않게 한다.
- [ ] 타 사용자 개/작업 접근과 만료된 인증의 차단을 검증한다.
검증: 사용자 A/B 격리·인증 만료 통합 테스트. 의존: 체크포인트 A. 예상 파일: backend/auth.py, backend/models.py, tests/test_auth.py, migration.

### P4b — 비공개 업로드와 동의 (M)
- [ ] 소유권·동의 버전·크기/길이·예산 검사를 거쳐 제한된 업로드를 허가한다.
- [ ] 서버가 파일을 재검증하고 고유 작업 ID/멱등성 키로 중복 생성을 차단한다.
- [ ] 원본 TTL·취소·삭제 요청의 상태를 기록한다.
검증: 잘못된 파일/초과 크기/다른 사용자/중복 요청·삭제 사례. 의존: P4a. 예상 파일: backend/uploads.py, backend/storage.py, backend/jobs.py, tests/test_uploads.py.

### P5a — 격리 작업자와 비용 원장 (M)
- [ ] 영상 디코딩·외부 호출을 API 프로세스와 격리하고 시간·메모리·네트워크를 제한한다.
- [ ] 작업 lease·원자적 비용 예약·중복 처리·최대 재시도를 구현한다.
- [ ] 취소 요청과 실행 중 작업의 경합, 결과가 불명확한 외부 호출을 처리한다.
검증: 작업자 중단/재시작·예산 경합·타임아웃·취소 통합 테스트. 의존: P2/P4b. 예상 파일: backend/worker.py, backend/budget.py, tests/test_worker.py, 배포 구성.

### P5b — 결과와 피드백 (M)
- [ ] 관찰/시간 구간/유보 사유를 계약에 맞춰 저장하고 소유자에게만 반환한다.
- [ ] 보호자 피드백을 정답과 구분하고 학습 동의 없는 자료를 검수 학습 큐에서 제외한다.
- [ ] 삭제·원본 만료와 결과 표시를 일관되게 처리한다.
검증: 전체 작업 상태 전이·권한 철회·삭제 후 접근. 의존: P5a. 예상 파일: backend/results.py, backend/feedback.py, tests/test_results.py, migration.

### P6a — Flutter 영상 선택→분석 요청 (M)
- [ ] 개인 인증, 개 프로필 선택, 영상 크기/길이 안내, 분석·학습 동의를 연결한다.
- [ ] 업로드/취소/네트워크 실패를 사용자에게 표시한다.
- [ ] 앱에 공급자 API 키를 포함하지 않는다.
검증: 첫 개발 기기에서 실제 소유자 요청·잘못된 입력·취소 흐름. 의존: P4/P5 및 Flutter 환경. 초기 앱 골격은 별도 작은 작업으로 먼저 생성한다.

### P6b — Flutter 결과·기록·삭제 (M)
- [ ] 관찰 구간 재생·불확실성·피드백·삭제를 제공한다.
- [ ] 원본이 만료되면 재생할 수 없음을 표시한다.
- [ ] Android/iOS 기기별 업로드·재생·백그라운드 복귀를 검증한다.
검증: 실제 기기에서 영상 선택부터 결과·삭제까지 E2E. 의존: P6a. 예상 범위: 결과/기록/피드백 화면 및 기기 테스트.

### 체크포인트 B — 제한 파일럿
- [ ] 품질·건당 비용·응답 시간·개인정보 삭제·사용성 기준을 실제 환경에서 검증한다.
- [ ] 배포 시 별도 운영 설정·예산·자격 증명을 연결하며 이 기획만으로 유료 호출이나 배포가 실행되지는 않는다.

### P7 — 폰 이벤트 감지와 전용 모델 (후속 실험으로 분할)
- [ ] 소리/움직임 이벤트 누락과 배터리를 측정한 뒤 전송 구간 선택을 도입한다.
- [ ] 검수 자료가 충분할 때 frozen embedding + 작은 행동 분류기를 비교한다.
- [ ] 오디오/영상/융합을 같은 독립 평가 세트에서 비교하고 개선된 후보만 제한 배포한다.
검증: 개체 분리 성능·기기 지연/발열·비용·회귀·롤백. 의존: 체크포인트 B 및 데이터 규모. 하나의 대형 작업으로 구현하지 않고 실험별 계약을 먼저 만든다.

## Lightweight VLM tuning slice (2026-10-18)
- [ ] Compare official lightweight model repositories and record selection.
- [ ] Add reviewed local-frame manifest gate, LoRA training and adapter inference.
- [ ] Verify rejection tests and pretrained CPU optimizer/save/reload in CI.
- [ ] Train/evaluate on licensed real dog frames; blocked until reviewed dataset exists.
