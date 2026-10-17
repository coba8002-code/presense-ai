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
