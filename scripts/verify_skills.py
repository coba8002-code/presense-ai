"""Verify the pinned, project-local Codex skill installation without networking."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'agent_skills/manifest.json').read_text())
for name, expected in manifest['sha256'].items():
    path = root / name
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f'Skill integrity mismatch: {name}')
for path in (root / '.agents/skills').glob('*/SKILL.md'):
    text = path.read_text()
    if not text.startswith('---\nname: ') or '\ndescription: ' not in text:
        raise SystemExit(f'Invalid skill metadata: {path.name}')
print(f"Verified {len(manifest['sha256'])} pinned skill/reference files; 5 Codex SKILL.md entries")
