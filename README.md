# PetSense AI

Dog-only MVP for behavioral-context analysis. Cat support is deferred. This estimates observations and uncertain
context; it does not translate animal language or diagnose disease.

## Status

New Sprint 02 bootstrap based on `develop` documentation and [issue #1](https://github.com/coba8002-code/presense-ai/issues/1).
The prior `PetSense_AI_AgentSkills_Integration.zip` was not provided and has **not**
been imported. There was no application source on develop. Current code includes a
local FastAPI service, NumPy audio baseline and an opt-in VLM adapter. Flutter,
Production PyTorch models, fusion and pet memory remain follow-up work. An optional experimental SmolVLM2 LoRA trainer is available. No real-data training
or paid cloud inference has been performed. See [작업지시서](docs/WORK_ORDER.md) and [remaining tasks](tasks/todo.md).

## Setup and tests

Python 3.12, from repository root:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install --only-binary=:all: -r requirements.lock
python -m pip check
python scripts/verify_skills.py
python scripts/check_environment.py
python -m unittest discover -s tests -v
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

`GET /healthz` reports service health and `model_ready: false`. The dependency
closure is pinned from installed Python 3.12 metadata. Fresh dependency installation and all 30 tests passed in
[GitHub CI](https://github.com/coba8002-code/presense-ai/actions/runs/39018838044). Socket-server smoke subsequently passed in the real-time browser CI; dependency
vulnerability audit remains pending; the service is still a local-development prototype.

## Reproduce a synthetic smoke run

```sh
python -m training.synthetic --output data/smoke-dog --species dog
python -m training.preflight --manifest data/smoke-dog/manifest.json --registry data/smoke-dog/registry.json --species dog
python -m training.run --manifest data/smoke-dog/manifest.json --registry data/smoke-dog/registry.json --species dog --output artifacts/smoke-dog
python -m evaluation.evaluate --model artifacts/smoke-dog/model.json --manifest data/smoke-dog/manifest.json --registry data/smoke-dog/registry.json
```

Use new directories per run; existing outputs are never overwritten.
These are sine waves with artificial identities and low/
high-frequency labels, **not evidence of animal behavior accuracy**.

For real data, review [dataset terms](docs/DATASET_AUDIT.md) and supply a reviewed
registry and JSON manifest. Each row needs `path` (relative to manifest directory),
`animal_id` (globally consistent identity across datasets/sessions), `species`
(`dog` only), `label` (grounded event/context), and `dataset` (registry key).
WAV input must be PCM16, 16 kHz, mono/stereo, 0.1–10 seconds, under 2 MB.
Resampling/segmentation must be performed on approved source material and recorded
in its provenance. At least five animals and all labels in each partition are
required. Duplicate audio hashes, absolute paths and paths outside the manifest directory fail.
Leading/trailing whitespace in identity fields is rejected to prevent accidental
identity splitting. Run preflight before training; it checks WAVs and partitions
without fitting a model. It does not independently verify legal rights.

Train-only feature normalization; validation selects regularization; test animals
are held out. JSON outputs include model parameters, split membership, file hashes,
rights provenance, macro F1, confusion matrix, Brier/ECE and abstention coverage.
Calibration metrics do not make confidence a calibrated probability. Registry
approval is a trusted operator policy, not verification of entered legal claims.
The owner's commercial intent is approved; third-party rights gates still apply.

## Near-real-time microphone demo

[Browser and backend CI](https://github.com/coba8002-code/presense-ai/actions/runs/39023577386) passed with 44 Python tests and
a real Chromium/fake-microphone/HTTP integration check. A local browser demo
captures one-second audio chunks and sends sound-active
chunks to the backend. Start with PETSENSE_ENABLE_AUDIO=true and a private
PETSENSE_API_TOKEN, then open `/realtime` on the local server. No cloud API key is
needed. [Protocol, setup and limits](docs/REALTIME_AUDIO.md).

The RMS gate detects sound activity, not bark/meow identity. With no approved
real-data model, behavioral inference is explicitly unavailable. Audio is not
stored; stopping or revoking consent releases the microphone. This is a browser
development demo, not Flutter or a deployed service. No physical-device latency
or real-world behavior accuracy has been established.

## VLM integration

Default is disabled. `POST /v1/vision/observe` accepts JSON with `image_base64`
(PNG/JPEG, decoded size <=512 KB) and explicit `consent: true`.
It requires `Authorization: Bearer <PETSENSE_API_TOKEN>` plus operator environment
variables `PETSENSE_ENABLE_CLOUD=true`, `PETSENSE_VLM_MODEL`, `OPENAI_API_KEY`.
`.env.example` is documentation; the service does not auto-load .env files.
Choose a model supporting image input and strict Chat Completions JSON schemas.
Enabling the adapter makes paid calls: obtain separate approval before doing so.

Fixed OpenAI HTTPS endpoint, timeout, bounded response, no redirects/retries or
media persistence. Images are sent to the provider only with consent. Return value
separates observed posture/ears/tail from uncertain hypotheses; low-confidence,
unclear or unknown-species outputs abstain. Provider output is schema-validated.
Tests mock the HTTP boundary; provider/model compatibility and behavioral quality
have not been live-tested. PNG/JPEG checks validate signatures, not full decoding.

This is a localhost development API. A static development token is not mobile
production authentication. Do not publish it before shared rate limiting, per-user
authorization, provider privacy/retention review and deployment hardening.

## Engineering evidence

- [Pinned agent skills](agent_skills/README.md), [plan](tasks/plan.md), [constraints](CONSTRAINTS.md)
- [Verification and model limitations](docs/VERIFICATION.md)
- CI configuration: `.github/workflows/tests.yml`; no auto-merge or deployment.

## Automatic learning

Approved local manifests can now be watched for changes, retrained, and compared
against an incumbent on a separate animal/session-disjoint acceptance benchmark.
See [자동학습 실행 가이드](docs/AUTOLEARN.md). The worker saves candidate artifacts;
it does not download YouTube media or deploy models. Current trainer is the NumPy
baseline. Synthetic CLI smoke and all 56 Python tests passed locally.

## 영상 링크 자동 지식 갱신

공식 YouTube 검색·Gemini URL 분석·출처 검색·NotebookLM Enterprise 소스 등록 worker: [실행 및 제한](docs/VIDEO_KNOWLEDGE.md). 기본 비활성화이며 API 인증과 채널 이용 권한이 필요합니다. 지식 갱신과 오디오 모델 학습은 별도 경로입니다.

## VLM 검수 및 학습 준비

영상 관찰 후보를 검수한 뒤 개체·세션·영상 단위로 평가 데이터를 분리하는 CLI를 추가했습니다. 실행 방법과 다음 작업: [VLM 학습 TODO](docs/VLM_TRAINING_TODO.md). 검증 결과는 주석 데이터이며 실제 비디오 학습 완료를 의미하지 않습니다.

승인된 로컬 개 영상 연결·실제 디코딩·주석 구간 검증: [VIDEO_MEDIA.md](docs/VIDEO_MEDIA.md). FFmpeg/ffprobe가 필요합니다.

개 영상 검수 화면: 서버 실행 후 `/review`. 로컬 영상·후보를 열고 라벨을 승인하여 검수 JSON을 내보냅니다. [사용 방법과 제한](docs/REVIEW_UI.md).

제품·서버·앱·VLM 및 학습의 권장 설계: [개 전용 하이브리드 MVP 기획](docs/DOG_MVP_ARCHITECTURE.md). 실제 영상 평가를 우선하는 새 실행 순서는 tasks/todo.md를 따릅니다.

## Experimental lightweight VLM tuning

[SmolVLM2 256M selection and LoRA commands](docs/SMALL_VLM_TUNING.md) provide an
optional, isolated PyTorch experiment for reviewed dog posture frames. Synthetic
pretrained optimizer smoke is separate from real dog fine-tuning. This adapter is
not deployed to the API; real dog accuracy and mobile performance remain unverified.

## Pretrained dog sound-event inference

An optional [AST local-WAV adapter](docs/PRETRAINED_DOG_AUDIO.md) returns the seven
original dog-related AudioSet label scores using pinned safetensors weights.
Dog2vec/AVES weight-specific terms remain unresolved; they are not integrated.
Scores are uncalibrated, decisions abstain, and live audio routes are unchanged.

## 보호자 웹 앱 (2026-10-28)

`/app`에서 WAV 사건 점수와 상황 메모, 브라우저 기록 저장·삭제·JSON 내보내기를 사용할 수 있습니다.
AST 설치와 `PETSENSE_ENABLE_AST=true`, `PETSENSE_API_TOKEN` 설정이 필요합니다.
API: `POST /v1/audio/events`, 16kHz PCM16 WAV, 0.1~10초, 2MB 이하.
현재 개발 미리보기이며 감정/원인 판단은 보류합니다. 사용자 계정·영상 업로드·결제·전문가 연결은 후속입니다.

확장 기획: [사업](docs/strategy-20261028/01_BUSINESS_PLAN.md), [제품](docs/strategy-20261028/02_PRODUCT_PLAN.md), [개발](docs/strategy-20261028/03_DEVELOPMENT_PLAN.md).

### 보호자 앱 2차 개발

음성 파일(WAV/MP3/M4A 등 브라우저 지원 형식, 최대20MB)을 선택하거나 마이크로 최대10초 녹음할 수 있습니다.
선택 구간을 브라우저에서 16kHz mono PCM16 WAV로 변환해 `/v1/audio/events`로 전송합니다.
녹음은 HTTPS 또는 localhost와 브라우저 권한이 필요하며 동의 철회·화면 이탈 시 마이크를 해제합니다.
최근7일(KST 날짜)의 저장 기록 수/기록일 수와 상담 준비 텍스트 내보내기를 추가했습니다.
이 통계는 저장된 최대100개 기록만 반영하며 실제 행동 빈도·변화나 진단을 의미하지 않습니다.
Windows/iOS/Android 실제 기기와 Web Audio 코덱 검증은 별도입니다.

### 계정별 보호자 메모 (단일 PC 개발 기반)

`python -m backend.accounts --db data/private/notes.sqlite3 --token-file data/private/local-session.json`으로 개발 세션을 발급합니다.
서버에 `PETSENSE_ACCOUNT_DB=data/private/notes.sqlite3`을 지정하면 `/app`의 계정 메모 영역이 연결됩니다.
이름·상황만30일 보관하며 음성·분석 결과·세션은 서버 메모에 저장하지 않습니다.
현재 로그인 서비스·계정 동기화 완성이 아니며 운영 인증과 백업 포함 삭제 검증은 남아 있습니다.
앞으로의 실행 순서와 완료 조건은 [현재 TODO](tasks/todo.md)의 EXEC 항목을 따릅니다.

### 재현 가능한 검증
`python -m scripts.verify_release --output artifacts/verification-new.json`은 Python/Node/컴파일/기존 스킬 지문 검사를 수행하고 관측한 테스트 수와 소스 해시를 기록합니다. 실제 모델/휴대폰 정확도와는 별개입니다.
공개 음향 도구와 해석 범위는 [기준 평가](docs/PUBLIC_AUDIO_BENCHMARK.md), 실제 원격 실행 증거는 [진행 기록](docs/SELF_DIRECTED_PROGRESS.md)을 참고하세요.

### 분석 프로세스 분리
현재 오디오 API는 요청별 자식 프로세스로 AST를 실행합니다. 가중치는 사전에 캐시하며 런타임은 오프라인입니다. 타임아웃·연결 종료 시 자식을 종료·회수합니다. [준비 방법과 제한](docs/ISOLATED_AUDIO.md)을 확인하세요. 지속 작업 큐나 운영 보안 샌드박스가 완성된 것은 아닙니다.
