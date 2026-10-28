"""Read-only paired C2 bilingual transfer64 audit; never trains or promotes a route.

Accepts privately retained, byte-pinned raw per-row observations.  It cannot
independently establish that supplied rows came from native Needle inference.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

ROUTES = ('simple', 'detail', 'gist', 'both')
FIXTURE_BLOB = 'e9aaae43f3313fbdc8e4b2fc870f2712a5557a66'
ITEMS_SHA256 = '12863402ffecef7565d23d1162fa061a1983ee92b46332c60adcfb3cd37ca9af'


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def registered_fixture(path, *, expected_blob=FIXTURE_BLOB, expected_items=ITEMS_SHA256):
    raw = Path(path).read_bytes()
    if git_blob(raw) != expected_blob:
        raise ValueError('frozen fixture blob mismatch')
    data = json.loads(raw)
    items = data.get('items')
    if data.get('schema') != 'v13.c2.bilingual_transfer64.v1' or not isinstance(items, list) or len(items) != 64:
        raise ValueError('invalid frozen fixture schema/count')
    if data.get('items_sha256') != expected_items or sha256(json.dumps(items, ensure_ascii=False, sort_keys=True).encode()) != expected_items:
        raise ValueError('frozen fixture item digest mismatch')
    expected_ids = [f'{route}-{lang}-{i:02d}' for route in ROUTES for lang in ('en', 'de') for i in range(8)]
    if [item.get('id') for item in items] != expected_ids:
        raise ValueError('frozen fixture ID/order mismatch')
    if any(item.get('label') != item['id'].split('-')[0] or item.get('lang') != item['id'].split('-')[1]
           or not isinstance(item.get('text'), str) or not item['text'].strip() for item in items):
        raise ValueError('frozen fixture label/language/text mismatch')
    return items


def read_pinned_rows(path, expected_sha, items, name):
    if not isinstance(expected_sha, str) or len(expected_sha) != 64 or any(c not in '0123456789abcdef' for c in expected_sha):
        raise ValueError(f'{name} requires an exact lowercase SHA256')
    raw = Path(path).read_bytes()
    if sha256(raw) != expected_sha:
        raise ValueError(f'{name} raw SHA256 mismatch')
    rows = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON constant')))
    if not isinstance(rows, list) or len(rows) != len(items):
        raise ValueError(f'{name} missing or extra rows')
    if [row.get('id') for row in rows if isinstance(row, dict)] != [item['id'] for item in items]:
        raise ValueError(f'{name} duplicate, missing or reordered IDs')
    for row, item in zip(rows, items):
        if not isinstance(row, dict) or row.get('label') != item['label'] or row.get('pred') not in (*ROUTES, None):
            raise ValueError(f'{name} invalid row label/prediction')
        latency = row.get('latency_s')
        if isinstance(latency, bool) or not isinstance(latency, (int, float)) or not math.isfinite(latency) or latency < 0:
            raise ValueError(f'{name} invalid latency')
        if name == 'needle':
            if not isinstance(row.get('validated'), bool):
                raise ValueError('needle validation flag missing')
            if not row['validated'] and row['pred'] is not None:
                raise ValueError('invalid native call cannot count as prediction')
            confidence = row.get('confidence')
            if confidence is not None and (isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(confidence)):
                raise ValueError('needle nonfinite or malformed confidence')
    return rows


def mcnemar_exact(needle_only, scaffold_only):
    """Exact two-sided conditional binomial McNemar p; no asymptotic shortcut."""
    if min(needle_only, scaffold_only) < 0 or any(isinstance(x, bool) or not isinstance(x, int) for x in (needle_only, scaffold_only)):
        raise ValueError('discordant counts must be nonnegative integers')
    n = needle_only + scaffold_only
    if n == 0:
        return 1.0
    k = min(needle_only, scaffold_only)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n))


def paired_counts(items, needle, scaffold):
    counts = Counter()
    for item, nr, sr in zip(items, needle, scaffold):
        nc = nr['pred'] == item['label']
        sc = sr['pred'] == item['label']
        outcome = 'both_correct' if nc and sc else 'needle_only' if nc else 'scaffold_only' if sc else 'both_wrong'
        counts[outcome] += 1
    return {key: counts[key] for key in ('both_correct', 'needle_only', 'scaffold_only', 'both_wrong')}


def audit(items, needle, scaffold, needle_sha, scaffold_sha):
    def one(subset):
        subset_items = [items[i] for i in subset]
        n = [needle[i] for i in subset]
        s = [scaffold[i] for i in subset]
        counts = paired_counts(subset_items, n, s)
        size = len(subset)
        return {**counts, 'n': size,
                'needle_correct': counts['both_correct'] + counts['needle_only'],
                'scaffold_correct': counts['both_correct'] + counts['scaffold_only'],
                'scaffold_minus_needle_accuracy': (counts['scaffold_only'] - counts['needle_only']) / size,
                'mcnemar_exact_two_sided_p': mcnemar_exact(counts['needle_only'], counts['scaffold_only'])}
    return {'schema': 'v13.c2.transfer64.paired_audit.v1', 'evidence_kind': 'OFFLINE_PINNED_INPUT_NOT_NATIVE_ATTESTATION',
            'fixture_blob': FIXTURE_BLOB, 'fixture_items_sha256': ITEMS_SHA256,
            'needle_rows_sha256': needle_sha, 'scaffold_rows_sha256': scaffold_sha,
            'overall': one(range(len(items))),
            'by_language': {lang: one([i for i, item in enumerate(items) if item['lang'] == lang]) for lang in ('en', 'de')},
            'by_route': {route: one([i for i, item in enumerate(items) if item['label'] == route]) for route in ROUTES},
            'gate': 'NOT_PROMOTED', 'age0': 'RECORD_ONLY', 'step2': 'UTILITY_FAIL', 'b3_l1': 'FAIL',
            'body_jepa': 'UNAVAILABLE', 'lp3_heldout': 'FAIL', 'jepa_weight': 0, 'phone_measured': False,
            'whole_system_complete': False,
            'claim_limit': 'Paired author-labelled route agreement only; p-value assumes fixed independent rows and labels; no native provenance, calibration, deployment, causality or Redmi proof'}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fixture', required=True, type=Path)
    ap.add_argument('--needle-rows', required=True, type=Path)
    ap.add_argument('--needle-sha256', required=True)
    ap.add_argument('--scaffold-rows', required=True, type=Path)
    ap.add_argument('--scaffold-sha256', required=True)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args(argv)
    items = registered_fixture(args.fixture)
    needle = read_pinned_rows(args.needle_rows, args.needle_sha256, items, 'needle')
    scaffold = read_pinned_rows(args.scaffold_rows, args.scaffold_sha256, items, 'scaffold')
    report = audit(items, needle, scaffold, args.needle_sha256, args.scaffold_sha256)
    # No-overwrite, closed file before reporting success; private input rows stay private.
    with args.out.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
        f.flush()
        import os
        os.fsync(f.fileno())
    print('C2_PAIRED_TRANSFER64_AUDIT_ONLY_NO_PROMOTION')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
