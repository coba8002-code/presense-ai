# Sprint 02 — Reproducible Audio AI Baselines

## PS-001 Dataset audit
Review Barkopedia, Meow-Net/CatMeows, AP-10K, Animal Kingdom, licenses, commercial-use rights and download policies. Publish a registry with approved/not-approved/unknown status.

## PS-002 Dog audio
Build audio preprocessing, dog-bark event classifier baseline and a context classifier only where grounded labels exist. Split by animal identity. Report macro F1, class counts and failure cases.

## PS-003 Cat audio — deferred beyond MVP
The user selected dog-only support. Do not execute cat training in the current MVP. Future scope: replicate a CatMeows/Meow-Net baseline where rights permit. Evaluate on animal-disjoint splits; avoid treating recording context as inferred intent.

## PS-004+ Vision and fusion
Implement a VLM adapter extracting observations into structured JSON. Benchmark audio-only, vision-only and fusion on the same held-out animals.

## Deliverables
Reproducible training/evaluation scripts, environment lock, CI, model cards, license registry, PR with real test logs. Stop when permissions or data are unavailable.
