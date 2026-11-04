"""Inventory routing only: a license category is never a training authorization."""
import argparse
import json
from pathlib import Path
import re


def route(policy):
    license = re.sub(r'[^a-z0-9]', '', str(policy.get('license', '')).lower())
    if 'nd' in license and license.startswith('ccby'):
        return 'permission_required'
    if license.startswith('ccbync') or 'noncommercial' in license or 'researchonly' in license:
        return 'research_review'
    if license in ('ccby40', 'ccby30', 'cc010', 'cc0'):
        return 'commercial_candidate'
    return 'permission_required'


def restricted_license(policy):
    license = re.sub(r'[^a-z0-9]', '', str(policy.get('license', '')).lower())
    return (license.startswith('ccby') and ('nc' in license or 'nd' in license)
            or 'noncommercial' in license or 'researchonly' in license)


def report(registry):
    sources = []; requests = []
    for name, policy in sorted(registry.items()):
        if policy.get('species') == 'cat':
            continue
        lane = route(policy)
        sources.append({'dataset': name, 'source': policy.get('source'), 'license': policy.get('license'),
                        'lane': lane, 'training_ready': False,
                        'next_action': 'validate provenance, labels and independent identities' if lane == 'commercial_candidate'
                        else 'review actual purpose and obtain applicable use rights before training'})
        if lane != 'commercial_candidate':
            requests.append({'dataset': name, 'source': policy.get('source'), 'sent': False,
                             'requested_scope': ['commercial model training', 'commercial use of resulting weights',
                                                 'media acquisition and preprocessing', 'attribution and redistribution terms'],
                             'grant_received': False})
    return {'training_performed': False, 'sources': sources, 'permission_requests': requests,
            'note': 'Research review is not permission: business R&D may still be commercial use. No messages sent.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registry', default='datasets/registry.json'); p.add_argument('--output', required=True)
    args = p.parse_args(); path = Path(args.registry)
    if path.stat().st_size > 1_000_000: raise ValueError('Registry too large')
    registry = json.loads(path.read_text())
    if not isinstance(registry, dict) or not all(isinstance(v, dict) for v in registry.values()):
        raise ValueError('Registry object required')
    result = report(registry)
    with Path(args.output).open('x') as f: json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({'sources': len(result['sources']), 'permission_requests': len(result['permission_requests']),
                      'training_performed': False}))


if __name__ == '__main__': main()
