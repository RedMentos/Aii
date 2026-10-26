#!/usr/bin/env python3
"""Run491: source-only held-out ten-episode STEP2 fixture registration.

Never calls a model, native runner, Runtime or a learning gate. Does not change
older registered cohorts. The native 1,050-row trial is NOT implemented here.
"""
import argparse
import hashlib
import json
from pathlib import Path

import step2_z2_timescale as z2

SPECS = (
    ('Vesper', 'SPLIT', (113, 6, True), (72, 5, True), (61, 7, False)),
    ('Willow', 'SPLIT', (96, 4, False), (80, 6, True), (92, 3, False)),
    ('Xenia', 'SPLIT', (88, 7, True), (62, 4, False), (73, 5, True)),
    ('Yarrow', 'SPLIT', (104, 3, True), (90, 2, False), (111, 2, True)),
    ('Crescent', 'SPLIT', (127, 8, False), (93, 7, False), (89, 6, True)),
    ('Asteria', 'SPLIT', (78, 5, True), (55, 4, True), (54, 5, True)),
    ('Boreal', 'RULE', (142, 4, True), (120, 3, True), (110, 5, False)),
    ('Cascade', 'RULE', (91, 6, False), (88, 5, False), (76, 7, True)),
    ('Drift', 'DETAIL', (107, 7, True), (103, 4, True), (95, 6, False)),
    ('Eon', 'DETAIL', (84, 4, False), (79, 3, False), (68, 4, True)),
)
FIXTURE_SHA256 = 'c434a5765ed85b7c51022c5aaea0ba4c3150ef0f1490f466b4a8833e41b44c63'
SEEDS = (31, 32, 33)
ARMS = ('A', 'B', 'C', 'D', 'E')
VARIANTS = ('b1_only', 'b2_only', 'both_none', 'both_exact', 'both_control',
            'same_policy_dual', 'prompt_only_dual')
MODEL_SHA256 = {
    'B1_DETAIL': 'bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1',
    'B2_GIST': '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf',
    'C3_LANGUAGE': '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d',
}
RUNNER_SHA256 = '79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39'


def require(ok, why):
    if not ok:
        raise ValueError(why)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def fixtures():
    result = [z2.episode(*spec) for spec in SPECS]
    validate(result)
    return result


def validate(rows):
    require(type(rows) is list and len(rows) == 10, 'TEN_EPISODES_REQUIRED')
    require([r['id'] for r in rows] == [s[0] for s in SPECS] and
            len({r['id'] for r in rows}) == 10, 'FROZEN_IDS_CHANGED')
    require([r['type'] for r in rows] == [s[1] for s in SPECS],
            'FROZEN_TYPES_CHANGED')
    require([r['oracle']['action'] for r in rows] ==
            ['A', 'B', 'B', 'NONE', 'B', 'B', 'A', 'A', 'A', 'B'],
            'FROZEN_ORACLE_ACTIONS_CHANGED')
    require(hashlib.sha256(canonical(rows)).hexdigest() == FIXTURE_SHA256,
            'FROZEN_FIXTURE_BYTES_CHANGED')
    for row in rows:
        kind = row['type']
        require(len(row['history']) == 3 and
                'Project Zenith' in row['history'][1], 'THREE_TURN_HISTORY_CHANGED')
        options = row['history'][2]
        current = row['current']
        rules = row['rules']
        rule_text = z2.rules_text(rules['budget'], rules['deadline'],
                                  rules['local_only'])
        if kind in ('SPLIT', 'DETAIL'):
            pos = options.find('Option A:')
            require(240 < pos < 360 and 'Option A:' not in options[:240] and
                    'Option B:' in options[:600], 'B1_B2_DETAIL_WINDOW_NOT_SEPARATED')
            require('cost ' not in current.lower(), 'OPTIONS_LEAKED_IN_CURRENT')
        if kind in ('SPLIT', 'RULE'):
            require(rule_text in row['history'][0] and
                    rule_text not in current, 'OLD_RULES_NOT_ISOLATED')
        else:
            require('Budget ' not in current and
                    'budget ' in current and 'deadline ' in current and
                    'local-only requirement:' in current,
                    'DETAIL_CURRENT_RULES_MISSING')
        if kind == 'RULE':
            require('Option A:' in current and 'Option B:' in current,
                    'RULE_CURRENT_OPTIONS_MISSING')
        require(row['oracle']['action'] != 'UNKNOWN',
                'ORACLE_UNKNOWN_WOULD_REWARD_MISSING_EVIDENCE')
    return True


def registration():
    rows = fixtures()
    return {
        'schema': 'V13_RUN491_HELDOUT10_SOURCE_ONLY_REGISTRATION_V1',
        'status': 'SOURCE_ONLY_PREREG_VALIDATED_NO_NATIVE',
        'fixtures': rows,
        'fixture_sha256': FIXTURE_SHA256,
        'seeds': list(SEEDS), 'arms': list(ARMS), 'variants': list(VARIANTS),
        'planned_native_consumer_rows': 1050,
        'source_constructor': 'step2_z2_timescale.episode',
        'model_sha256_expected_not_retrieved': MODEL_SHA256,
        'runner_sha256_expected_not_retrieved': RUNNER_SHA256,
        'native_executed': False, 'canonical_gate_pass': False,
        'step2_exit': 'UTILITY_FAIL', 'b3_l1': 'FAIL',
        'body_jepa': 'UNAVAILABLE', 'jepa_weight': 0,
        'redmi_measured': False,
        'claim_limit': 'Source-only prospective fixture registration. No models, no native, no STEP2 acceptance.'
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = registration()
    require(not args.output.exists(), 'REFUSE_OVERWRITE_PREVIOUS_REGISTRATION')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(result) + b'\n')
    print(json.dumps({'status': result['status'],
                      'fixture_sha256': result['fixture_sha256'],
                      'rows': len(result['fixtures']), 'native_executed': False}))


if __name__ == '__main__':
    main()
