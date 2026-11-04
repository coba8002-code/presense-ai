# Real-time audio development slice

> 현재 제품 범위: **개 전용 MVP**. 고양이 학습·분석은 후속 단계로 보류합니다.

## Contract and scope

One-second audio chunks are captured continuously and sent sequentially to
`POST /v1/audio/chunks`. This is near-real-time HTTP request/response, not a
continuous WebSocket or a finished mobile app. A local microphone demo at
`/realtime` is included. No cloud provider calls or API charges are involved.

- Body: little-endian signed PCM16, mono, exactly 16 kHz; 0.1–1 second per request.
- Content-Type: application/octet-stream.
- Headers: Authorization: Bearer <development token>, X-Audio-Consent: true,
  X-Audio-Species: dog|cat, X-Audio-Sequence: nonnegative integer.
- Server enablement: PETSENSE_ENABLE_AUDIO=true and PETSENSE_API_TOKEN.
- At most two active requests and five requests per second per server process.
  The shared development token and process-local limit are not multi-tenant security.
- The UI keeps at most one request in flight; extra chunks are dropped rather than
  queued indefinitely. Capture duration and network/model time add to latency.
- Raw audio is processed in memory and not saved or logged. Browser audio, token
  and consent remain in memory; stop/disconnect/hidden page releases the microphone.

## Detection and optional model

An RMS threshold of 0.02 is a simple sound-activity gate, not a trained bark/meow
classifier. Background sounds can trigger it. With no approved model, responses
explicitly say model_unavailable and abstain from behavioral predictions.

PETSENSE_AUDIO_MODEL may point to a trusted local baseline model.json, but use
requires PETSENSE_AUDIO_MODEL_APPROVED=true. This operational flag must only follow
review of the training rights and model quality; it cannot confer external rights.
Synthetic artifacts are rejected for live predictions. Species must match. Low
confidence causes abstention, and returned scores remain uncalibrated.

## Acceptance and tests

Verify unauthenticated/disabled/no-consent input, oversized or odd-length PCM,
invalid species/sequence, request rate, silence, model absence, synthetic model
rejection, species mismatch and threshold abstention. A PCM feature-equivalence
check prevents training/serving preprocessing drift. Validate browser worklet PCM
encoding and bounded upload behavior with automated tests where tooling permits.
No veterinary diagnosis, emotion-as-fact or real-world accuracy claims.

## Run

```sh
export PETSENSE_ENABLE_AUDIO=true
# Set PETSENSE_API_TOKEN to a private development token through your environment.
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/realtime, enter the development token, choose species,
check audio-sharing consent and press Start. Microphone access requires localhost
or HTTPS and browser permission. This slice requires AudioWorklet and a browser
that supports a 16 kHz AudioContext; unsupported sample rates fail explicitly.
Do not expose this prototype publicly. No Flutter or live VLM video streaming is
included in this slice; future video analysis should be sampled/event-triggered.

## Verification

[CI on 21b2bf3](https://github.com/coba8002-code/presense-ai/actions/runs/39023577386) passed both backend and browser jobs.
44 Python tests and AudioWorklet checks passed. Chromium used a generated sine-wave
microphone input with the actual local HTTP server; capture, upload, result display,
consent revocation, microphone release and slow-response dropping passed with no
page errors. This is not a physical-device or animal-behavior validation.

A local 100-chunk synthetic microbenchmark without a loaded classifier measured
feature/RMS processing p50 0.310 ms and p95 0.486 ms. Capture itself takes one second;
network and classifier time are excluded. Do not present these figures as user latency.
