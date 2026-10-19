"""Snapshot the installed dependency closure for this Python 3.12 environment."""
from importlib.metadata import distribution
from pathlib import Path
from packaging.requirements import Requirement

pending = Path('requirements.in').read_text().splitlines()
resolved = {}
while pending:
    req = Requirement(pending.pop())
    if req.marker and not req.marker.evaluate({'extra': ''}):
        continue
    dist = distribution(req.name)
    name = dist.metadata['Name'].lower().replace('_', '-')
    if name in resolved:
        continue
    if not req.specifier.contains(dist.version):
        raise ValueError(f'Installed version violates {req}')
    resolved[name] = dist.version
    pending.extend(dist.requires or [])
Path('requirements.lock').write_text(
    '# Generated from installed metadata by scripts/lock_environment.py; Python 3.12\n'
    + ''.join(f'{name}=={version}\n' for name, version in sorted(resolved.items()))
)
