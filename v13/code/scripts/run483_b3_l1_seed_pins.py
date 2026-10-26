#!/usr/bin/env python3
"""Run483 source-only: bind B3 L1 per-seed rows to external SHA256 pins.

The pins must come from an independently authenticated preregistration. This
module checks alignment/integrity, NOT whether a measurement really happened.
No production B3 gate or latent authority is changed.
"""
import hashlib
import json
import math
import re

REQUIRED = ('NO_MESSAGE', 'LATENT', 'LATENT_SHUFFLED', 'LATENT_RANDOM',
            'EXACT', 'CONTROL', 'SYMBOLIC')
HEX = re.compile(r'[0-9a-f]{64}\Z')
SEED = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,31}\Z')


def check(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def evaluate_pinned(rows, row_pins, metadata, metadata_pin, evaluator=None):
    """Require exact channel x seed matrix and externally pinned row contents."""
    check(type(rows) in (list, tuple) and 21 <= len(rows) <= 224,
          'B3_PINNED_ROW_BUDGET')
    check(type(row_pins) is dict and len(row_pins) == len(rows) and
          all(type(k) is str and type(v) is str and HEX.fullmatch(v)
              for k, v in row_pins.items()), 'B3_PINNED_ROW_MAP')
    check(type(metadata) is dict and set(metadata) ==
          {'role_drop', 'ood_rate', 'reload_identical'} and
          type(metadata_pin) is str and HEX.fullmatch(metadata_pin),
          'B3_PINNED_METADATA_SCHEMA')
    check(digest(metadata) == metadata_pin, 'B3_PINNED_METADATA_MISMATCH')
    for k in ('role_drop', 'ood_rate'):
        v = metadata[k]
        check(type(v) in (float, int) and math.isfinite(v) and 0 <= v <= 1,
              'B3_PINNED_METADATA_INVALID')
    check(type(metadata['reload_identical']) is bool,
          'B3_PINNED_RELOAD_INVALID')
    observed = {}
    for row in rows:
        check(type(row) is dict and set(row) ==
              {'channel', 'seed', 'accuracy', 'bytes', 'evidence_sha256'},
              'B3_PINNED_ROW_SCHEMA')
        ch, seed = row['channel'], row['seed']
        check(type(ch) is str and ch in REQUIRED and
              type(seed) is str and SEED.fullmatch(seed),
              'B3_PINNED_CHANNEL_OR_SEED')
        acc, size, proof = row['accuracy'], row['bytes'], row['evidence_sha256']
        check(type(acc) in (float, int) and math.isfinite(acc) and 0 <= acc <= 1
              and type(size) is int and 0 <= size <= 2**31 - 1 and
              type(proof) is str and HEX.fullmatch(proof),
              'B3_PINNED_MEASUREMENT_INVALID')
        key = ch + '/' + seed
        check(key not in observed, 'B3_PINNED_DUPLICATE_ROW')
        check(row_pins.get(key) == digest(row), 'B3_PINNED_ROW_MISMATCH')
        observed[key] = row
    check(set(observed) == set(row_pins), 'B3_PINNED_UNREGISTERED_OR_MISSING')
    seeds = sorted({r['seed'] for r in rows})
    check(3 <= len(seeds) <= 32 and
          set(observed) == {ch + '/' + s for ch in REQUIRED for s in seeds},
          'B3_PINNED_SEED_ALIGNMENT')
    # The frozen l1_gate accepts one byte cost per channel, not per seed.
    sizes = {}
    for ch in REQUIRED:
        values = {observed[ch + '/' + s]['bytes'] for s in seeds}
        check(len(values) == 1, 'B3_PINNED_BYTES_VARY_BY_SEED')
        sizes[ch] = values.pop()
    task = {'acc': {ch: [observed[ch + '/' + s]['accuracy'] for s in seeds]
                    for ch in REQUIRED}, 'bytes': sizes, **metadata}
    if evaluator is None:
        from scripts.run478_b3_l1_complete_baselines import evaluate
        evaluator = evaluate
    result = evaluator(task)
    check(type(result) is dict and result.get('canonical_gate_pass') is False
          and result.get('latent_authority') == 0 and result.get('b3_l1') == 'FAIL',
          'B3_PINNED_EVALUATOR_PROMOTED')
    return {'schema': 'V13_RUN483_B3_L1_PINNED_SEED_ALIGNMENT_V1',
            'status': 'B3_PINNED_SOURCE_DIAGNOSTIC_NO_AUTHORITY',
            'seed_ids': seeds, 'row_count': len(rows),
            'diagnostic_l1_verdict': result.get('diagnostic_l1_verdict'),
            'canonical_gate_pass': False, 'latent_authority': 0,
            'b3_l1': 'FAIL', 'step2_exit': 'UTILITY_FAIL',
            'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
            'redmi_measured': False,
            'claim_limit': 'Externally authenticated row and metadata pins required. No proof of native measurement, true seed pairing, causal gain, or latent authority.'}
