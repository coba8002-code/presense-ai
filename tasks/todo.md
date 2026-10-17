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
- [ ] Verify fresh dependency installation and local HTTP server in a network-capable environment.
- [ ] Run dependency vulnerability audit (pip-audit unavailable here).
- [x] Publish draft PR [#2](https://github.com/coba8002-code/presense-ai/pull/2) targeting develop.
- [ ] Confirm GitHub CI passes before merge; no successful run observed yet.

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
- [ ] WO-01 external checks: fresh install, socket smoke, vulnerability audit and remote CI.
- [ ] WO-03 onward: follow the prerequisites in WORK_ORDER.md; no real-data or paid calls claimed.
