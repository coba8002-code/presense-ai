# Agent skills integration

Pinned upstream: [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/aeac41d4d005999432bb7312f7ff06383a91d59d), MIT.

Five unchanged skill entrypoints are installed under `.agents/skills/`: spec-driven
-development, planning-and-task-breakdown, test-driven-development, security-and
-hardening, code-review-and-quality. Shared checklists preserve relative paths.
See `manifest.json` for commit and local SHA-256 integrity values.

Verify from repository root: `python scripts/verify_skills.py`.
These are project-local Codex skills, not a claim that plugin slash commands were
registered. Codex CLI 0.159.2 is present. Git/npx installation was unavailable due
to the execution proxy connection failure, so files were fetched through the
GitHub connector. Start a new Codex session in this repository for discovery;
this session read and applied the skill files directly.

Applied practices: requirements/plan before code; failing tests before each feature
slice; fail-closed external boundaries; five-axis code review and mutation probe.
The user's explicit request authorizes bootstrap, implementation and PR delivery;
we did not add a redundant intermediate spec approval gate. No paid API calls or
deployment were authorized or performed.
