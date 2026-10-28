"""Disjoint frozen bilingual C2 route transfer64 evaluation, no calibration/training.

This is an opt-in offline Linux native benchmark. It reuses the existing
c2_benchmark Needle/scaffold execution and summary functions exactly.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'specs/c2-bilingual-transfer64-20261028.json'
FIXTURE_BLOB = 'e9aaae43f3313fbdc8e4b2fc870f2712a5557a66'
ITEMS_SHA = '12863402ffecef7565d23d1162fa061a1983ee92b46332c60adcfb3cd37ca9af'
ORIGINAL_SHA = '54f3da390fb79c3f966edd61d3390d94dc59d850987174c644ef45ef531a54e6'
MODEL_SHA = 'c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38'
CATALOG_BLOB = '7af05962af41d0bc3f7dd18ef01d4eba55eabf99'
C2_BENCHMARK_BLOB = '4668d0befe4b06b8713dae49c3619193beaae025'
ROUTES = ('simple', 'detail', 'gist', 'both')


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def fixture(path=FIXTURE, original=None):
    path = Path(path)
    raw = path.read_bytes()
    if git_blob(raw) != FIXTURE_BLOB:
        raise ValueError('Transfer64 fixture Git blob drift')
    data = json.loads(raw)
    if data.get('schema') != 'v13.c2.bilingual_transfer64.v1' or data.get('items_sha256') != ITEMS_SHA:
        raise ValueError('Transfer64 registration mismatch')
    items = data.get('items')
    if not isinstance(items, list) or len(items) != 64:
        raise ValueError('Transfer64 must contain exactly 64 rows')
    if hashlib.sha256(json.dumps(items, ensure_ascii=False, sort_keys=True).encode()).hexdigest() != ITEMS_SHA:
        raise ValueError('Transfer64 item hash mismatch')
    expected_ids = [f'{route}-{lang}-{i:02d}' for route in ROUTES for lang in ('en','de') for i in range(8)]
    if [x.get('id') for x in items] != expected_ids:
        raise ValueError('Transfer64 order/ID drift')
    if any(x.get('label') not in ROUTES or x.get('lang') not in ('en','de')
           or x['id'].split('-')[:2] != [x['label'], x['lang']]
           or not isinstance(x.get('text'), str) or not x['text'].strip() for x in items):
        raise ValueError('Transfer64 invalid label/language/text')
    texts = [x['text'].strip().casefold() for x in items]
    if len(set(texts)) != 64:
        raise ValueError('Transfer64 duplicate prompts')
    if Counter((x['label'], x['lang']) for x in items) != Counter({(r,l):8 for r in ROUTES for l in ('en','de')}):
        raise ValueError('Transfer64 route/language imbalance')
    if original is None:
        original = ROOT / 'specs/c2-benchmark.json'
    old = json.loads(Path(original).read_bytes())
    if old.get('items_sha256') != ORIGINAL_SHA or hashlib.sha256(
        json.dumps(old['items'], ensure_ascii=False, sort_keys=True).encode()).hexdigest() != ORIGINAL_SHA:
        raise ValueError('Original 96 cohort pin mismatch')
    prior = {x['text'].strip().casefold() for x in old['items']}
    if set(texts) & prior:
        raise ValueError('Transfer64 overlaps original 96 prompts')
    return items


def native_preflight(home):
    from v13.models import ModelManager
    from v13.common import file_hash
    if (platform.system() != 'Linux' or platform.machine().lower() not in ('x86_64', 'amd64')
            or os.environ.get('ANDROID_ROOT')):
        raise ValueError('Linux x86_64 only; Redmi is a separate proof')
    if git_blob((ROOT / 'specs/models.json').read_bytes()) != CATALOG_BLOB:
        raise ValueError('Model catalog drift')
    if git_blob((ROOT / 'scripts/c2_benchmark.py').read_bytes()) != C2_BENCHMARK_BLOB:
        raise ValueError('Frozen benchmark adapter drift')
    settings = json.loads((Path(home)/'config/settings.json').read_text())
    if (settings.get('seed') != 13 or settings.get('learning_mode') != 'RECORD_ONLY'
            or settings.get('system_stage') != 0 or settings.get('jepa_weight', 0) != 0
            or settings.get('latents_enabled', False)):
        raise ValueError('Age0/seed configuration mismatch')
    manager = ModelManager(Path(home))
    result = manager.verify(deep=True)
    if not result.get('needle', {}).get('ok') or not result['needle'].get('hash_checked'):
        raise ValueError('Needle native model verification missing')
    if file_hash(manager.path_for('C2_CONTROL')) != MODEL_SHA:
        raise ValueError('Needle model bytes mismatch')
    return subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT.parents[1], text=True).strip()


def save_new(path, data):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def report_from_rows(items, candidate, rows, extra, source=None):
    if len(rows) != len(items) or [x.get('id') for x in rows] != [x['id'] for x in items]:
        raise ValueError('Missing, duplicate, or reordered native rows')
    if any(x.get('label') != y['label'] or x.get('pred') not in ROUTES + (None,)
           or not isinstance(x.get('latency_s'), (int, float)) or x['latency_s'] < 0
           for x, y in zip(rows, items)):
        raise ValueError('Invalid benchmark observation')
    from scripts.c2_benchmark import summarize
    per_lang = {lang: summarize([row for row, item in zip(rows, items) if item['lang'] == lang])
                for lang in ('en', 'de')}
    return {'candidate': candidate, 'source_commit': source, 'evidence_kind':
            'LINUX_NATIVE_C2_ROUTE_IF_VERIFIED' if candidate == 'needle' else 'LINUX_SOFTWARE_SCAFFOLD',
            'n': len(rows), 'overall': summarize(rows, extra), 'per_language': per_lang,
            'fixture_git_blob': FIXTURE_BLOB, 'items_sha256': ITEMS_SHA,
            'original96_items_sha256': ORIGINAL_SHA, 'model_sha256': MODEL_SHA if candidate == 'needle' else None,
            'training_or_calibration_on_transfer_rows': False, 'age0_learning_mode': 'RECORD_ONLY',
            'jepa_weight': 0, 'step2_utility': 'FAIL', 'b3_l1': 'FAIL',
            'body_jepa': 'UNAVAILABLE', 'lp3_heldout': 'FAIL',
            'phone_measured': False, 'whole_system_complete': False,
            'claim_limit': 'Author-labelled 64-row route agreement only; no approval or deployment authority'}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--home', type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--only', choices=('scaffold', 'needle', 'both'), default='both')
    args = ap.parse_args(argv)
    items = fixture()
    if args.only in ('needle','both') and args.home is None:
        ap.error('--home required for native Needle')
    # Native identity and source pins are checked before creating output or launching.
    source = native_preflight(args.home) if args.only in ('needle','both') else None
    args.out.mkdir(parents=True, exist_ok=False)
    from scripts.c2_benchmark import run_needle, run_scaffold
    for name, fn in (('scaffold', lambda: run_scaffold(items)),
                     ('needle', lambda: run_needle(items, args.home))):
        if args.only != 'both' and args.only != name:
            continue
        try:
            rows, extra = fn()
            save_new(args.out / (name+'.rows.json'), rows)
            result = report_from_rows(items, name, rows, extra, source)
            save_new(args.out / (name+'.report.json'), result)
        except Exception as exc:
            save_new(args.out / (name+'.FAILED.json'), {'candidate': name, 'error_type': type(exc).__name__,
                      'error': str(exc)[:300], 'no_promotion': True})
            raise
    print('C2_TRANSFER64_EVALUATION_COMPLETE_NO_PROMOTION')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())