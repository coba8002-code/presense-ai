"""Offline backend readiness check; never reads secrets or attempts network access."""
import argparse
from importlib import metadata, util
import json
from pathlib import Path
import platform
import re
import shutil
import sys


def check_packages(lock: Path) -> list[dict]:
    results = []
    for line in lock.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)', line)
        if not match:
            raise ValueError('Expected exact name==version pins in requirements.lock')
        name, expected = match.groups()
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        results.append({'package': name, 'expected': expected, 'installed': installed,
                        'status': 'missing' if installed is None else
                                  'ok' if installed == expected else 'mismatch'})
    if not results:
        raise ValueError('Dependency lock is empty')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'requirements.lock')
    args = parser.parse_args()
    try:
        packages = check_packages(args.lock)
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Environment check blocked: {exc}\n')
    python_ok = sys.version_info[:2] == (3, 12)
    ready = python_ok and all(p['status'] == 'ok' for p in packages)
    report = {
        'status': 'installed_requirements_match' if ready else 'blocked',
        'python': platform.python_version(), 'python_supported': python_ok,
        'packages': packages,
        'optional_tools': {'pytorch': util.find_spec('torch') is not None,
                           'flutter': shutil.which('flutter') is not None,
                           'pip_audit': util.find_spec('pip_audit') is not None},
        'fresh_install': 'not_checked', 'network': 'not_checked',
        'notice': 'Installed metadata only; not evidence of clean installation, security audit or CI success.',
    }
    print(json.dumps(report, indent=2))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
