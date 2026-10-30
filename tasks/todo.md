# PetSense AI remaining work

Current scope: **dog-only MVP**. Historical completed work below may describe the earlier two-species bootstrap.

Execution order and acceptance criteria: [작업지시서](../docs/WORK_ORDER.md).

## 현재 실행 순서 — EXEC (2026-10-30 KST 갱신)
이 목록이 앞으로의 기준이다. 아래 과거 항목은 증거와 의존관계를 보존하기 위해 남긴다. 기능 구현, 모의 검증, 실기기 검증, 운영 출시를 각각 별도로 완료 처리한다.

### EXEC-00 현황·요구사항 대조 — 완료
- [x] Issue #1과 현재 dog-only 지시, 코드·기획서·과거 TODO 대조.
- [x] 브라우저 메모와 운영 계정, 소리 점수와 행동 정확도를 구분.
증거: docs/strategy-20261028 및 아래 날짜별 검증 기록. 로컬 Git은 커밋 없는 스냅샷이지만 변경 소스는 GitHub 커넥터로 PR #3·#4·#5에 반영했고 커밋별 원격 CI를 확인했다. 병합은 별도다.

### EXEC-01 계정별 저장 기반 — 개발용 완료
의존: EXEC-00. 목적: 공유 토큰과 별도로 사용자별 메모를 격리한다.
- [x] SQLite 스키마·무작위 세션·해시 저장·세션 만료.
- [x] 소유자 범위 목록/삭제, 보호자 메모만 입력 허용.
- [x] 세션 발급 CLI, 사용자별 500개 상한, 100개 페이지 조회.
인수: A/B 격리·없는/만료 세션 차단·DB에 원문 토큰 미저장. 증거: tests/test_accounts.py.
운영 인증 완료가 아니다. 셀프가입/복구/소셜로그인/개 프로필 ID는 후속.

### EXEC-02 보관·삭제 계약 — 개발용 완료
의존: EXEC-01.
- [x] 별도 서버 보관 동의, 30일 만료 데이터 조회 제외·정리.
- [x] 계정 메모 전체 삭제와 해당 계정의 모든 세션 철회.
- [x] 비공개 API no-store, 추가 owner/result 필드 주입 차단.
인수: 다른 사용자 자료 유지, 철회 후 새 메모 추가 거절, 30일 경계 검사.
물리 백업·로그·파생 미디어의 운영 삭제는 원본 보관 구조 구축 후 별도 검증.

### EXEC-03 앱 서버 메모 연결 — 개발용 완료
의존: EXEC-01/02.
- [x] 별도 기록 세션 입력·명시적 보관·내 메모 조회/개별 삭제/전체 삭제.
- [x] 세션을 저장소에 남기지 않고 서버 메모와 로컬 관찰 기록의 범위 표시.
- [x] 모의 DOM 저장/동의/세션 누락/전체 삭제 검증.
인수: 음성·토큰·모델 결과를 서버 메모 요청에 넣지 않는다. 실제 브라우저는 EXEC-04.

### EXEC-04 실제 사용자 흐름 검증 — 원격 Chromium 완료 / 국내 PC·실기기 대기
- [x] GitHub Linux의 고정 가중치 캐시에서 Chromium→계정 인증→HTTP→AST 독립 프로세스→결과→저장→삭제 E2E. 합성 음성 입력.
- [ ] 국내 PC의 캐시·Windows 프로세스·실제 소리로 같은 E2E 재현.
- [ ] iOS Safari/Android Chrome 녹음·코덱·HTTPS·권한 취소·백그라운드 복귀.
- [x] Chromium에서 모의429/503·브라우저 offline·주입된 저장 quota 오류 및 수동 복구 검사.
인수: 기기/OS/모델 revision·샘플 해시·지연·실패 증거 기록. 실제 AST 실행41051446917, 모의 오류/복구41051446920. ast-browser.json은 합성 입력 해시·모델 revision·단일 실행 소요시간을 담는다. 국내 PC/실기기 연결 없음; 통신망/기기 신뢰성이나 지연 분포를 증명한 것은 아니다.

### EXEC-05 데이터와 모델 평가 — 병행 준비 / 외부 연결 대기
- [x] 고정 영상 평가 계약·가상 예제·전역 개체/가정/세션/원본/내용 분할 검사와 검수/잠금 CLI 구현. 실제 정답/성능과 구분.
- [ ] 국내 PC AI-Hub59/71878 원본 수령·개 부분·라벨/개체/가정/세션 스키마 검사.
- [x] ESC-10 실제 AST400개 순위 평가 및 저장 결과 재생. AUROC/AP1.0; 개체 분리 검증이나 서비스 임계값의 오탐 성능으로 해석하지 않음.
- [ ] AP-10K 자세 추정 기준선, 실제 가정 외부 평가셋 구축.
- [ ] Dog2vec/AVES 가중치 조건, DogSpeak/InterPet4D 상업 허락 확인.
- [ ] 보듬TV 원본별 허락·제작자 제공 자료·전문가 사례 검수.
- [ ] 개체·가정 분리에서 audio/vision/fusion 비교와 calibration/coverage 측정.
인수: 권리 증거·파일 해시·개체 식별·분할·재현 명령·독립 결과표. 확보 목록은 artifacts/data-acquisition-20261028. 사용자 이용 승인 진술을 원본 수령 완료로 바꾸지 않는다.

### EXEC-06 운영 제품 기반 — 설계·구현 대기
의존: EXEC-04/05 품질 게이트. 기반 설계는 먼저 진행 가능.
- [ ] 인증 방식 선정: 국내 접근성·소셜로그인·탈퇴·복구·가격/개인정보 처리 비교.
- [ ] 사용자/개 프로필 소유권, 가족/기관 권한 및 감사 기록.
- [ ] 국내 저장소·원본 TTL·비동기 분석 job·멱등성·취소·공유 rate limit.
- [ ] 백업 포함 삭제·모니터링·비용 상한·장애/모델 롤백.
- [ ] Flutter 또는 웹앱 유지의 기기/운영비 비교 후 앱 배포 방식 확정.
인수: 공개 배포 전 타 사용자 접근/보관/삭제/비용/복구 체크 통과. 현재 개발 세션을 운영 인증으로 전환하지 않는다.

### EXEC-07 고객·사업 실증 — 모집/실증 대기
- [ ] 보호자20명·기관10곳 인터뷰와 경쟁 대안 비교.
- [ ] 30가정4주 파일럿: 첫 관찰 완료/4주 재사용/유용성 측정.
- [ ] 실제 건당 원가·무료 사용량·지원 부담으로 구독 한도 재산정.
- [ ] 3기관 유료 실증·상담 파트너 조건/환불/정산 검토.
- [ ] 가격/유료 전환 실험 후 확장/중단 결정.
인수: 동의된 실제 코호트의 분모·기간·표본 수·결제/비용 증거. 현재 사업 숫자는 가정이다.

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
- [x] 기본 서버 lock 취약점 감사 완료, certifi 권고 수정 후41032114483 성공. 선택 AI/브라우저 환경 전체 감사는 별도.
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
- [x] WO-01 기본 서버 lock 감사와 certifi 수정 완료. 선택 환경 전체 감사는 후속.
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
- [x] standing/sitting/lying/walking/unknown, 고정 구간 평가 단위와 정확 매칭 규칙 v1 문서화. 모델 예측·지표 실행은 후속.
- [x] 기존 권한 레지스트리·전역 개체/가정/세션·원본 SHA256·분할·검수/이중 검수·정답 잠금 JSON 계약과 가상 형식 예제 구현.
- [ ] 모델 답을 보지 않은 독립 검수자가 관찰 정답을 작성하고 일부 이중 검수·불일치 기록을 남긴다. 전문가는 기준·모호한 사례·표본 검수에 활용하며 모든 항목에 새 전문가 주석을 요구하지 않는다.
검증: tests/test_video_contract.py의 누출5종·시간/중첩·권한·블라인드·이중 검수·지문·비공개 CLI7개 및 전체153개 로컬 통과. evaluation/video_contract.py, docs/VIDEO_EVALUATION.md. 실제 독립 정답/동영상/예측 성능은 별도 확보해야 한다. 해시 검사만 성공해도 evaluation_ready=false를 유지한다.

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
- [ ] 독립 검수된 관찰 정답과 예측을 비교해 행동별 성능·유보/coverage·시간 오차·실패 사례를 산출한다. 전문 해석의 검증은 별도 범위다.
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
- [x] Compare official lightweight model repositories and record selection.
- [x] Add reviewed local-frame manifest gate, LoRA training and adapter inference.
- [x] Verify rejection tests and pretrained CPU optimizer/save/reload in CI (run 39128020164; 108 local tests).
- [ ] Train/evaluate on licensed real dog frames; blocked until reviewed dataset exists.

## 개 전문 자료 확대 조사 (2026-10-19 KST)
- [x] 음향·자세·멀티모달·훈련 지식 후보 14개 항목을 공식 출처와 함께 정리: docs/DOG_RESEARCH_EXPANSION.md.
- [x] DogSpeak/DigiDogs 비상업 조건 및 Pawgaze/InterPet4D 권한 확인 필요 상태 기록.
- [ ] Dog2vec/AVES 가중치 라이선스·해시·추론 재현 후 EfficientAT와 비교.
- [ ] 강형욱 출연 공식 영상의 사례 카드 필드와 관찰/전문가 해석 분리 검수 구현.
- [ ] 허가된 개 음향·영상의 독립 평가셋 확보 및 모델별 실제 비교.

## 사전학습 개 소리 추론 1차 (2026-10-19 KST)
- [x] Dog2vec/AVES 배포 조건 재확인; 가중치 상업 조건 미확정 상태 유지.
- [x] BSD-3-Clause 표기 AST를 명시적 대안 기준선으로 연결: 로컬 WAV → 개 관련 7개 원본 라벨 점수.
- [x] 입력/라벨 경계 테스트 포함 112개 로컬 테스트 통과.
- [x] 실제 가중치 CPU CI와 CLI 추론 성공: Actions 39213061875.
- [ ] Dog2vec/AVES 자체 연결 및 실제 개 정확도 평가 (이번 AST 적용과 구분).

## 국내 PC 데이터 실행 패키지 (2026-10-28 KST)
- [x] PC 사양 진단·공식 AI-Hub 선택 다운로드·로컬 inventory 명령 구현.
- [x] ESC-10 해시 검증·16kHz 변환·AST 점수 실행 명령 구현.
- [ ] 국내 PC에서 AI-Hub 승인 파일 다운로드 및 실제 스키마/개체 ID 검수.
- [ ] 국내 PC의 AST 점수 실행·CPU 지연 측정 및 GPU/VRAM 확인.
- [ ] 개체·가정 분리 실제 개 평가 및 검수 자료 학습.

## 보호자 앱 및 사업 확장 (2026-10-28)
- [x] /app 관찰·로컬 기록 UI와 /v1/audio/events 연결.
- [x] 사업·제품·개발 실행안, 경제성 가정, 전국 확대 단계 작성.
- [ ] 실제 가중치/국내 PC/휴대폰 E2E 검증.
- [ ] 모바일 입력·운영 인증·국내 보관/삭제·주간 리포트.
- [ ] 30가정 4주 파일럿 및 유료 전환 실험.

## 보호자 앱 2차: 입력·기록 활용
- [x] 브라우저 지원 음성 파일→선택10초→16kHz PCM16 WAV 변환.
- [x] 동의 기반 마이크 녹음·10초 종료·취소·권한 대기 중 철회 처리.
- [x] 최근7일 기록 수/기록일 수 및 상담 준비 텍스트 내보내기.
- [x] WAV 경계·변환·취소·동의·저장 흐름 모의 테스트 및 CI 명령 추가.
- [ ] iOS/Android 실기기 코덱·HTTPS 권한·마이크 해제 검증.
- [ ] 사용자 인증·가족 권한·비동기 분석 작업 및 서버 삭제 경로.

## 국내 PC 로커리 진행 보고 (2026-10-29 KST)
출처: 사용자가 전달한 로커리 보고. 이 환경에서 파일에 직접 접근하여 검증한 결과는 아니다.
- [x] 사용자에게서 작업 전달 완료와 로커리 실행 시작 보고 수령.
- [ ] 59번100개 파일 크기·SHA256·CRC 검사: 진행 중, 결과 미수령.
- [ ] 71878 TS.zip 부분 파일 시각별 .failed 격리·공간 점검: 예정 보고.
- [ ] 재시도 로직 수정 후 TS.zip 처음부터 재다운로드: 예정 보고.
- [ ] 병행 조사: 실제 원천/라벨 구조·개/개체/가정/세션 필드 확인.
이어받기 인수 기준: 206과 정확한 Content-Range 시작/전체 길이, 가능하면 ETag/Last-Modified 일치. 200 응답을 기존 파일에 이어붙이지 않는다. 416·길이/버전 불일치도 검사 없이 합치지 않는다. 제공자 체크섬이 없으면 자체 SHA256은 보존용 지문이며 원본 일치 검증으로 표현하지 않는다.

## 자율 개발 2026-10-30 KST
- [x] 공식 MDN/Python 문서 검토 후 AbortController·서버 업로드15초/추론60초 제한 적용.
- [x] 사용자 취소/동의 철회/파일 변경/화면 이탈 시 이전 분석 결과 차단.
- [x] 시간 초과/모델 혼잡/슬로 업로드 회귀 검사: Python133개 및 Node3종 통과.
- [x] 실제 Web Audio·HTTP 메모 API를 검사하는 Chromium CI 시나리오 작성(AST는 모의 응답).
- [x] 새 브라우저 CI 실행 성공 확인: 41023899244 및 41024327752(AST 응답 모의).
- [x] 최신 보호자 앱/메모/기획 변경의 별도 PR #3 반영 및 원격 CI 성공 확인.
다음: 국내 PC 실제 모델E2E, 수집 데이터 검수 결과 수령, 운영 인증/비동기 작업 설계.

## 원격 반영 및 공개 기준 평가 (2026-10-30 KST)
- [x] 최신 보호자 앱/메모/계획 33개 변경을 PR #3으로 반영. https://github.com/coba8002-code/presense-ai/pull/3
- [x] commit224f8d2의 backend/browser CI41023899244·41024327752 및 pretrained smoke41023899252 성공 확인.
- [x] 실제 Chromium의 Web Audio 변환·브라우저 저장·실제 메모 API 검사 성공(AST 응답은 모의).
- [x] 고정 revision ESC-10 부분집합 수집·원본/전처리 지문·400개 점수 재생 평가 도구 구현.
- [x] AUROC/AP의 완전/역순/동점/순열/잘못된 입력 검사 및 로컬137개 테스트 통과.
- [x] 공개 음향400개 실제 가중치 출력 검증41025543775 및 보정 점수 재생41032108181 성공.
- [ ] 국내 PC/실제 휴대폰 E2E·별도 개체/가정 평가: 기존 미완료 유지.

## 2026-10-30 최종 검증 기록
- [x] 실행 코드5cc47e5의 backend/browser41032114505·41032108034 성공.
- [x] 400개 공개 음성 재생 AUROC1.0/AP1.0 확인. 공개 사건 순위이며 개체/가정 행동 정확도가 아님.
- [x] certifi2026.10.23으로 기본 서버 감사41032114483 성공(알려진 취약점 없음).
- [x] 로컬138개·Node3종·컴파일·스킬 지문 검사 재실행 통과.
- [ ] 선택 torch/transformers/browser 환경 전체 의존성 감사.
- [ ] 실제 국내 PC/휴대폰/새 개체 평가와 로커리 데이터 검수 결과 수신.
- [ ] PR #2→#3→#4 사람 검토 및 병합. 자동 병합/배포 없음.

## 요청별 독립 분석 프로세스
- [x] 기존 모델 스레드를 stdin/stdout 프로토콜의 별도 자식으로 교체.
- [x] 입력/결과 크기·모델 지문·원본 해시·보류 계약 검증.
- [x] 실제 자식의 타임아웃/취소 종료·회수 및 HTTP 연결 종료 검사.
- [x] 런타임 오프라인 가중치·일반 자격 증명 환경변수 제거·캐시 준비 CLI.
- [x] 로컬146개 Python 검사 및 Node3종 통과.
- [x] 실제 AST Chromium/계정 세션/HTTP/독립 프로세스 CI41051446917 성공.
- [ ] 지속 job queue·사용자별 권한/예산·재시작 복구·OS 자원/네트워크 제한.

- [x] 분석의 계정 세션 모드와 공유 개발 토큰 우회 차단 구현.
- [x] 결과 반환 전 세션 철회/만료 재검사 및 브라우저 세션 비저장 검사.
- [ ] 운영 가입/복구/소셜로그인 및 사용자별 사용량 원장.

## 2026-10-30 요청별 분석 검증 완료
- [x] PR #5 https://github.com/coba8002-code/presense-ai/pull/5 생성; 실행 코드1ecab3b의 backend/browser41051446920·41051454144 및 실제 AST41051446917 성공.
- [x] 실제 AST 합성 Chromium 결과의 모델/revision/입력 해시/단일 실행 시간을 ast-browser.json artifact에 보존.
- [x] Chromium 모의429/503·offline·저장 quota 오류·수동 복구 검사 성공.
- [ ] PR #5 검토/병합, 국내 PC·실제 휴대폰·새 개체 행동 평가. 코드 검증 완료와 구분.

## 2026-10-30 독립 영상 평가 계약
- [x] PR #6 https://github.com/coba8002-code/presense-ai/pull/6 생성.
- [x] 실행 코드b0b9996의 backend/browser41053114599·41053123664 성공.
- [x] 로컬153개 Python·Node3종·컴파일·기존 스킬 지문 검사 통과.
- [x] 기존 주석·일반 검수·보호자 상황·모델 보조와 전문가 표본/불일치 검수를 구분한 LABEL_ACQUISITION.md, 담당/의존관계 NEXT_STEPS.md 작성.
- [ ] 실제 독립 관찰 정답·디코딩/정렬·동일 분할 모델 비교와 검수 자료 학습. 가상 예제나 모델 후보를 실제 정답으로 바꾸지 않음.

## 국내외 개 영상 조사 확장
- [x] 검색 대상명12개·검색어24개·국내/해외6배치 생성 CLI. 실제 발견한 영상과 구분.
- [x] 기존 공식 API 탐색기에 영속 순환 배치·공유 일일 한도·discovery-only 강제 연결.
- [x] 출처/시간·관찰/발언/가설 분리 사례 후보, 철회/기한/종/모델 변경 차단.
- [x] 사례 카드에 교정 효과·개체·배경음·발언자 검증을 확인 전 미확정으로 유지.
- [x] 로컬162개 Python·Node3종·knowledge 포함 컴파일/소스 지문 검사 통과. 실행 코드48d1e97의 backend/browser41055497784·41055998145 성공.
- [ ] 공식 YouTube API 환경에서 실제 영상 메타데이터 확보. 현재403·키/브라우저 미연결.
- [ ] 허용 범위 분석·사람 검수·원본/권한/개체 연결·독립 평가 후 실제 학습.
