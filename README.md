# PetSense AI

Dog/cat behavioral-context analysis. This estimates observations and uncertain
context; it does not translate animal language or diagnose disease.

## Status

New Sprint 02 bootstrap based on `develop` documentation and [issue #1](https://github.com/coba8002-code/presense-ai/issues/1).
The prior `PetSense_AI_AgentSkills_Integration.zip` was not provided and has **not**
been imported. There was no application source on develop. Current code includes a
local FastAPI service, NumPy audio baseline and an opt-in VLM adapter. Flutter,
PyTorch models, fusion and pet memory remain follow-up work. No real-data training
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

Use new directories per run; existing outputs are never overwritten. For cats,
replace `dog` with `cat`. These are sine waves with artificial identities and low/
high-frequency labels, **not evidence of animal behavior accuracy**.

For real data, review [dataset terms](docs/DATASET_AUDIT.md) and supply a reviewed
registry and JSON manifest. Each row needs `path` (relative to manifest directory),
`animal_id` (globally consistent identity across datasets/sessions), `species`
(`dog`/`cat`), `label` (grounded event/context), and `dataset` (registry key).
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
