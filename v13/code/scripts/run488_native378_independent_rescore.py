#!/usr/bin/env python3
"""Run488: independently rescore pinned native378 *answers*, not stored scores.

This diagnostic adds an independent answer->oracle scoring check to Run487's
raw-receipt/aggregate audit. No model call, cohort change or gate promotion.
"""
import json
import math
from pathlib import Path
import sys
import zipfile

import run487_native378_independent_raw_audit as previous

# Exact frozen Run394 six-fixture registration. Values: old rules, optional
# current revision, option A, option B (cost, days, local).
SPECS = {
    'Alder': ((140, 5, True), None, (90, 4, True), (110, 3, False)),
    'Beacon': ((105, 6, False), None, (75, 7, True), (100, 5, False)),
    'Cypress': ((95, 4, True), None, (80, 3, False), (90, 4, True)),
    'Delta': ((160, 8, False), (100, 4, True), (70, 5, True), (90, 3, True)),
    'Ember': ((70, 3, True), (130, 7, False), (95, 6, False), (120, 5, True)),
    'Fable': ((120, 6, False), (80, 3, True), (75, 2, False), (85, 2, True)),
}
FIELDS = ('cost', 'remaining', 'days', 'local', 'eligible')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def oracle(name):
    old, revision, a, b = SPECS[name]
    budget, deadline, local_only = revision if revision is not None else old
    options = []
    for entity, values in (('A', a), ('B', b)):
        cost, days, local = values
        options.append({'entity': entity, 'cost': cost,
                        'remaining': budget - cost, 'days': days,
                        'local': local,
                        'eligible': cost <= budget and days <= deadline and
                                    (local or not local_only)})
    eligible = [o for o in options if o['eligible']]
    action = min(eligible, key=lambda o: (o['cost'], o['entity']))['entity'] if eligible else 'NONE'
    return {'project': name, 'action': action, 'options': options}


def score_answer(raw, expected):
    """Standalone stdlib transcription of frozen field-exact scoring rules.

    The source implementation is *not imported*; independent expected fixture
    data and a deliberately different test suite detect stored-score drift.
    """
    checks = {}
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    try:
        obj = json.loads(raw, object_pairs_hook=unique) if isinstance(raw, str) else raw
        if not isinstance(obj, dict) or set(obj) != {'project', 'action', 'options'}:
            raise ValueError('top-level schema')
        if not isinstance(obj['options'], list) or len(obj['options']) != len(expected['options']):
            raise ValueError('option count')
        got = {}
        for item in obj['options']:
            if not isinstance(item, dict) or set(item) != {'entity', *FIELDS}:
                raise ValueError('option schema')
            entity = item['entity']
            if not isinstance(entity, str) or entity in got:
                raise ValueError('duplicate/invalid entity')
            got[entity] = item
        if set(got) != {o['entity'] for o in expected['options']}:
            raise ValueError('entity assignment')
        checks['project'] = type(obj['project']) is str and obj['project'] == expected['project']
        checks['action'] = type(obj['action']) is str and obj['action'] == expected['action']
        for opt in expected['options']:
            for field in FIELDS:
                actual, wanted = got[opt['entity']][field], opt[field]
                checks[opt['entity'] + '.' + field] = type(actual) is type(wanted) and actual == wanted
        errors = [key for key, valid in checks.items() if not valid]
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        errors = ['invalid:' + str(exc)]
        checks = {}
    n = 2 + len(FIELDS) * len(expected['options'])
    return {'utility': sum(checks.values()) / n,
            'exact': len(checks) == n and all(checks.values()),
            'field_checks': checks, 'contradictions': errors,
            'contradiction_count': len(errors), 'scored_fields': n}


def verify_row(row, name):
    require(row.get('fixture') == name and row.get('status') == 'RECORDED' and
            row.get('oracle_visible_to_native') is False, 'ROW_IDENTITY_OR_LEAK')
    require('answer' in row and type(row['answer']) is str, 'RAW_ANSWER_MISSING')
    recomputed = score_answer(row['answer'], oracle(name))
    require(type(row.get('score')) is dict and
            set(row['score']) == set(recomputed), 'SCORE_FIELDS_CHANGED')
    for key, value in recomputed.items():
        stored = row['score'][key]
        if key == 'utility':
            require(type(stored) in (float, int) and math.isfinite(stored) and
                    math.isclose(stored, value, rel_tol=0, abs_tol=1e-12),
                    'ANSWER_UTILITY_SCORE_MISMATCH')
        else:
            require(type(stored) is type(value) and stored == value,
                    'ANSWER_' + key.upper() + '_MISMATCH')
    return recomputed['utility']


def audit(path):
    # First verify original safe archive and its nine raw receipts with Run487.
    # Recompute the answer rubric separately, rather than trusting row.score.
    prior = previous.audit(path)
    require(prior['status'] == 'RAW_NATIVE378_RECOMPUTED_NO_GATE_PROMOTION' and
            prior['rows'] == 378 and prior['canonical_gate_pass'] is False and
            prior['step2_exit'] == 'UTILITY_FAIL', 'PREVIOUS_RAW_AUDIT_NOT_GREEN')
    counts = {name: 0 for name in SPECS}
    by_arm = {arm: [] for arm in previous.ARMS}
    with zipfile.ZipFile(path) as archive:
        progress = json.loads(archive.read('RUN397_PROGRESS.json'))
        for arm in previous.ARMS:
            for seed in previous.SEEDS:
                rid = f'{arm}_s{seed}'
                raw = archive.read(progress['completed'][rid]['attempt'] + '/tool_' + rid + '.json')
                report = json.loads(raw)
                for row in report['rows']:
                    name = row['fixture']
                    require(name in SPECS and row['variant'] in previous.VARIANTS,
                            'UNREGISTERED_FIXTURE_OR_VARIANT')
                    by_arm[arm].append(verify_row(row, name))
                    counts[name] += 1
    require(counts == {name: 63 for name in SPECS} and
            all(len(values) == 126 for values in by_arm.values()),
            'RESCORE_COHORT_INCOMPLETE')
    return {'schema': 'V13_RUN488_INDEPENDENT_NATIVE378_ANSWER_RESCORE_V1',
            'status': 'ORIGINAL_378_ANSWERS_RESCORED',
            'original_safe_zip_sha256': previous.EXPECTED_SAFE,
            'rows': 378, 'fixture_counts': counts,
            'arm_mean_answer_utility': {arm: math.fsum(values) / len(values)
                                        for arm, values in by_arm.items()},
            'canonical_gate_pass': False, 'step2_exit': 'UTILITY_FAIL',
            'b3_l1': 'FAIL', 'body_jepa': 'UNAVAILABLE',
            'jepa_weight': 0, 'redmi_measured': False,
            'claim_limit': 'Independent exact answer->oracle rescore of exploratory native378 only; no canonical ten-episode STEP2 acceptance, learned JEPA, or Redmi proof.'}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: run488_native378_independent_rescore.py <original-safe-zip>')
    print(json.dumps(audit(Path(sys.argv[1])), indent=2, sort_keys=True))
