# Codex Agent Instructions — PetSense AI

Read README.md and issue #1. Work in small PRs with tests and evidence. Do not claim models have been trained until metrics and reproducible runs exist.

## Current product scope
- User decision: dog-only MVP. Cat support is deferred.
- Reject cat training and live audio requests; abstain on non-dog VLM observations.
- Retain prior dataset audit evidence; do not claim cat support from generic schemas.

## Architecture
- Flutter Android/iOS app
- FastAPI backend
- Python/PyTorch dog audio classifiers; cats are a later expansion
- Cloud VLM for observable postures, context, and environment
- Multimodal fusion, per-pet history, privacy-first data collection

## First task
Import previous PetSense_AI_AgentSkills_Integration.zip source from the user's conversation or request access to the archive. Never fabricate its contents. Then audit dependencies, tests, and build commands.

## Skill workflow
Review addyosmani/agent-skills, use compatible spec/planning/TDD/security/review skills in Codex. Verify installation in the actual execution environment.

## Quality gates
- Animal-disjoint train/validation/test splits
- Accuracy, macro F1, confusion matrix, calibration and abstention metrics
- Record source license, consent, rights, version and provenance for every dataset
- No unauthorized downloading, scraping or model training on TV/YouTube
- Separate observation from behavioral hypothesis
- No veterinary diagnosis; route urgent signs to veterinary professionals
- No secrets in source, no unapproved paid API usage or production deploy
- CI must run before merging PRs
