# Verification — 2026-10-17

Local Python 3.12.14, installed dependencies captured in requirements.lock.

- `python -m unittest discover -s tests -v`: **22 tests passed**, 0 skipped.
- Feature slices first failed on missing modules, then passed after implementation.
- `python scripts/verify_skills.py`: 11 pinned files, five SKILL.md entrypoints verified.
- `python -m pip check`: no broken installed requirements.
- `python -m compileall -q backend training evaluation`: passed.
- Training/evaluation CLI help and dog/cat synthetic smoke runs: passed.
- Saved-model evaluation exactly reproduced held-out test metrics.
- Mutation probe inverted the dataset approval condition: suite failed (6 errors),
  demonstrating that the guard is exercised. Restored source and cleared affected
  bytecode cache; all 22 tests passed again.

Synthetic run details (each species): nine artificial identities, two sine-wave
labels, 18 clips; 14 train / 2 validation / 2 test clips. Test accuracy/F1 1.0,
confusion [[1,0],[0,1]], Brier ~0.000019, ECE ~0.00289, coverage 1.0 at threshold .7.
These numbers only verify plumbing on separable generated tones. They say nothing
about dog/cat emotion, intent, health or real-world performance. Artifacts/media
remain ignored locally, not in the repository.

## Limitations and blockers

- Git clone and external HTTP from the default execution sandbox failed to reach
  its proxy. GitHub connector reads work. An additional-network request was
  interrupted by the user; no network-policy bypass was attempted.
- Fresh dependency resolution reported no available distribution for the first
  pin in this environment. A no-change install check only confirmed packages
  already present. Clean installation is **not verified**; CI must establish it.
- pip-audit is not installed; vulnerability audit is pending.
- Local socket health smoke did not become ready; ASGI in-process route tests pass.
- VLM only tested with HTTP mocks: no live inference, API charges or model-quality claim.
- Missing ZIP/Flutter SDK; no mobile app or mobile build claimed.
- External dataset use remains blocked pending commercial/media rights evidence.

## Initial model card

Model: CPU NumPy spectral softmax regression; one species per run. Fixed log spectral
band means/stds, RMS and zero-crossing features; train-only standardization;
validation chooses L2 penalty from 0, .01, .1. JSON serialization avoids pickle.
No pretrained weights. No PyTorch/Meow-Net replication claimed. Intended use is an
engineering baseline on approved, grounded labels. Not for production, diagnosis,
or literal translation. Identity metadata must be correct; byte-identical duplicate
detection cannot identify all overlapping/edited recordings. A future benchmark
must audit sessions/households and domain shifts as well as individual identities.

## Work-order execution update

- Added docs/WORK_ORDER.md with task ordering, acceptance criteria and blockers.
- Full suite now **30 tests passed**, 0 skipped. Eight new tests first failed,
  then passed with the preflight CLI, strict manifest/policy checks and environment diagnostics.
- Synthetic dog and cat preflight: 18 records, nine identities, disjoint partitions; passed.
- Offline environment diagnostic: all 17 installed dependency pins match; Python 3.12.14.
  PyTorch, Flutter and pip-audit are absent. This is not a fresh-install claim.
- Skill integrity and compileall passed. CI now also listens to codex/** pushes
  and supports workflow_dispatch, but remote execution success is still unverified.
- Follow-up shell network permission request was interrupted while pending.
  No dependency install, paid provider call, real-data training or deployment occurred.

### Remote CI diagnosis

Push run 39008879809 failed before creating any jobs. Local YAML parsing reproduced
`mapping values are not allowed here` at the unquoted `--only-binary=:all:` command.
Quoted the command and verified YAML parsing; fix committed as 4cf6d34.
A subsequent run is required to establish installation/test success.

The next run reached setup-python but its cache searched for requirements.txt or
pyproject.toml. Set cache-dependency-path to requirements.lock (7e23171).
Both CI configuration failures were diagnosed from actual execution evidence.

### CI verified on 7e23171

[GitHub Actions](https://github.com/coba8002-code/presense-ai/actions/runs/39018838044) completed successfully: fresh Python 3.12 runner,
binary-only dependency installation, pip check, installed-version check, skill
integrity, full unittest suite and compileall all passed. This resolves the
fresh-install and remote-test blockers above. Socket-server smoke and dependency
vulnerability audit remain pending. No live provider or real-data run occurred.

## Near-real-time audio slice

- Local Python suite: **44 tests passed**, 0 skipped.
- Node AudioWorklet capture checks passed: one-second PCM16 framing, signed
  little-endian samples, sequence rollover and silent output.
- Client JS syntax, Python compileall, skill integrity and workflow YAML checks passed.
- Runtime dependencies unchanged. Browser-only test dependencies are pinned in
  requirements-browser.lock. Chromium unavailable locally; CI browser check pending.
- No physical microphone, animal-model accuracy or end-to-end latency claim.

### Real-time browser and HTTP verification completed

[Run 39023577386](https://github.com/coba8002-code/presense-ai/actions/runs/39023577386), commit 21b2bf3: both test and browser jobs passed.
The clean runner installed runtime/browser dependencies, passed 44 Python tests and
AudioWorklet checks, and launched a real HTTP server plus Chromium with a synthetic
microphone. Verified capture/upload/result, consent stop, released microphone tracks,
no post-stop requests, slow-response chunk dropping and no page errors. This resolves
the HTTP socket smoke blocker. Physical-device latency and model quality remain unverified.
