"""Verify pinned QA skill content without contacting upstream or executing helpers."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    manifest=json.loads((ROOT/'agent_skills/qa-skills-lock.json').read_text())
    for entry in manifest['files']:
        path=ROOT/entry['installed_path']
        if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            raise SystemExit('QA skill content mismatch: '+entry['installed_path'])
    print(f"Verified {len(manifest['files'])} pinned QA skill/license files")

if __name__=='__main__':main()
