#!/usr/bin/env python3
"""Read-only source-bound audit for historical native-firing candidate drift.

A successful audit execution never grants native candidate authority.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def compare(expected, actual):
    """Return closed digest report and complete unified diffs; no source mutation."""
    if set(expected) != set(actual):
        raise ValueError('Expected/live source file sets differ')
    files = {}
    diffs = []
    for name in sorted(expected):
        left, right = expected[name], actual[name]
        diff = list(difflib.unified_diff(
            left.splitlines(keepends=True), right.splitlines(keepends=True),
            fromfile='historical-integrated/' + name,
            tofile='current-live/' + name,
            lineterm='\n',
        ))
        files[name] = {
            'expected_sha256': sha(left),
            'live_sha256': sha(right),
            'byte_equal': left == right,
            'unified_diff_lines': len(diff),
            'expected_bytes': len(left.encode('utf-8')),
            'live_bytes': len(right.encode('utf-8')),
        }
        if diff:
            diffs.extend(diff)
            if diffs[-1] and not diffs[-1].endswith('\n'):
                diffs.append('\n')
    drift = any(not f['byte_equal'] for f in files.values())
    return ({
        'schema': 'V13_NATIVE_FIRING_SOURCE_DRIFT_AUDIT_V1',
        'status': 'DRIFT_DETECTED' if drift else 'BYTE_EXACT_MATCH',
        'candidate_gate': 'FAIL_SOURCE_DRIFT' if drift else 'SOURCE_MATCH_ONLY_NOT_NATIVE_PROOF',
        'source_paths': files,
        'native_executed': False,
        'phone_measured': False,
        'semantic_truth_authority': False,
        'selective_omission_enabled': False,
        'STEP2': 'UTILITY_FAIL',
        'B3_L1': 'FAIL',
        'Body_JEPA': 'UNAVAILABLE',
        'jepa_weight': 0,
        'whole_system_complete': False,
    }, ''.join(diffs))


def run(root, output):
    from scripts.integrated_candidates import NAMES, integrated_sources
    root = Path(root).resolve()
    expected = integrated_sources(root)
    actual = {name: (root / name).read_text(encoding='utf-8') for name in NAMES}
    report, unified = compare(expected, actual)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'manifest.json').write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    (output / 'historical-versus-live.diff').write_text(unified, encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root, args.output)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0  # Audit ran; FAIL_SOURCE_DRIFT is intentionally not promoted.


if __name__ == '__main__':
    raise SystemExit(main())
