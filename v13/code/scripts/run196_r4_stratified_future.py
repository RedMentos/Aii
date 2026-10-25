#!/usr/bin/env python3
"""V13 Run196: prospective R4 selective-abstention protocol; no model or runtime authority.

This intentionally cannot evaluate Run195 seed7/seed11 again. A future task manifest,
model/runner/source hashes, and a new native capture must be independently sealed and
published in that order. This code only provides fail-closed preparation and scoring.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile

SCHEMA = 'V13_R4_PROSPECTIVE_STRATIFIED_V1'
CAPTURE_SCHEMA = 'V13_R4_PROSPECTIVE_CAPTURE_V1'
TASK_SCHEMA = 'V13_R4_PROSPECTIVE_TASKS_V1'
SEEDS = (20261101, 20261103)
KINDS = ('summary', 'long', 'notes', 'compare')
PER_KIND = 15
THRESHOLD = 0.5803461074829102  # Run195 seed7-only selection; NEVER refit here
RUN195_PREREG_SHA256 = 'f501313e9daee53080d4f3ebe8e8e26394a40917085abe05d07a1f49df6200e4'
RUN195_SCRIPT_SHA256 = 'a2613d698b5258416294b37d3d7e0e7a1f106f6458b7c0c8937d729289bbbaae'
HEX64 = re.compile(r'^[0-9a-f]{64}$')
HEX40 = re.compile(r'^[0-9a-f]{40}$')
EXPECTED = {(seed, f'{kind}{i:02d}') for seed in SEEDS for kind in KINDS for i in range(PER_KIND)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _digest(value, label):
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise ValueError(f'{label}_SHA256_INVALID')
    return value


def _identity(rows, *, task=False):
    if not isinstance(rows, list) or len(rows) != len(EXPECTED):
        raise ValueError('ROW_COUNT_INVALID')
    by_key = {}
    for r in rows:
        if not isinstance(r, dict) or type(r.get('seed')) is not int or not isinstance(r.get('fixture'), str):
            raise ValueError('ROW_ID_INVALID')
        key = (r['seed'], r['fixture'])
        if key in by_key:
            raise ValueError('DUPLICATE_FIXTURE')
        by_key[key] = r
        _digest(r.get('task_sha256'), 'TASK')
        if task and (not isinstance(r.get('prompt'), str) or not r['prompt'].strip()
                     or hashlib.sha256(r['prompt'].encode('utf-8')).hexdigest() != r['task_sha256']):
            raise ValueError('TASK_PROMPT_HASH_MISMATCH')
    if set(by_key) != EXPECTED:
        raise ValueError('TASK_SET_MISMATCH')
    if task and len({r['task_sha256'] for r in rows}) != len(rows):
        raise ValueError('DUPLICATE_TASK_PROMPT')
    return by_key


def prepare(tasks_path, pins):
    """Generate a *candidate* registration; independent commit must precede inference."""
    tasks = read_json(tasks_path)
    if tasks.get('schema') != TASK_SCHEMA:
        raise ValueError('TASK_SCHEMA_INVALID')
    entries = _identity(tasks.get('rows'), task=True)
    required = ('model_sha256', 'runner_sha256', 'capture_script_sha256', 'source_tree_sha256')
    for k in required:
        _digest(pins.get(k), k.upper())
    if not isinstance(pins.get('source_commit'), str) or HEX40.fullmatch(pins['source_commit']) is None:
        raise ValueError('SOURCE_COMMIT_INVALID')
    return {
        'schema': SCHEMA, 'phase': 'REGISTRATION_CANDIDATE_NOT_YET_SEALED',
        'protocol_script_sha256': sha(__file__),
        'task_manifest_sha256': sha(tasks_path),
        'task_hashes': {f'{seed}:{fixture}': entries[(seed, fixture)]['task_sha256']
                        for seed, fixture in sorted(EXPECTED)},
        'seeds': list(SEEDS), 'strata': list(KINDS), 'per_stratum_per_seed': PER_KIND,
        'threshold': THRESHOLD, 'threshold_prereg_sha256': RUN195_PREREG_SHA256,
        'threshold_script_sha256': RUN195_SCRIPT_SHA256,
        'feature': 'digit_min_logprob',
        'min_global_coverage': .70, 'min_stratum_coverage': .60,
        'max_stratum_selective_error': .20, 'min_global_risk_reduction': .10,
        'min_utility_delta_quarters': 1,
        'utility_quarters': {'correct_answered': 4, 'wrong_answered': -8,
                             'correct_abstained': -2, 'wrong_abstained': -1},
        'baseline_utility_quarters': {'correct': 4, 'wrong': -8},
        'required_publication_order': ['task_manifest_and_registration', 'native_capture', 'evaluation'],
        'production_authority': 0, 'canonical_gate_pass': False,
        **{k: pins[k] for k in (*required, 'source_commit')},
    }


def validate_reg(reg):
    if not isinstance(reg, dict) or reg.get('schema') != SCHEMA or reg.get('phase') != 'SEALED_BEFORE_NATIVE':
        raise ValueError('REGISTRATION_NOT_SEALED')
    if reg.get('protocol_script_sha256') != sha(__file__):
        raise ValueError('PROTOCOL_SOURCE_CHANGED')
    for k in ('model_sha256', 'runner_sha256', 'capture_script_sha256', 'source_tree_sha256',
              'task_manifest_sha256'):
        _digest(reg.get(k), k.upper())
    if not isinstance(reg.get('source_commit'), str) or not HEX40.fullmatch(reg['source_commit']):
        raise ValueError('SOURCE_COMMIT_INVALID')
    if reg.get('threshold') != THRESHOLD or reg.get('threshold_prereg_sha256') != RUN195_PREREG_SHA256:
        raise ValueError('THRESHOLD_RESELECTED')
    if reg.get('threshold_script_sha256') != RUN195_SCRIPT_SHA256 or reg.get('feature') != 'digit_min_logprob':
        raise ValueError('FEATURE_RESELECTED')
    if reg.get('seeds') != list(SEEDS) or reg.get('strata') != list(KINDS) or reg.get('per_stratum_per_seed') != PER_KIND:
        raise ValueError('COHORT_CHANGED')
    fixed = {'min_global_coverage': .70, 'min_stratum_coverage': .60,
             'max_stratum_selective_error': .20, 'min_global_risk_reduction': .10,
             'min_utility_delta_quarters': 1,
             'utility_quarters': {'correct_answered': 4, 'wrong_answered': -8,
                                  'correct_abstained': -2, 'wrong_abstained': -1},
             'baseline_utility_quarters': {'correct': 4, 'wrong': -8}}
    if any(reg.get(k) != v for k, v in fixed.items()):
        raise ValueError('DECISION_RULE_CHANGED')
    if reg.get('production_authority') != 0 or reg.get('canonical_gate_pass') is not False:
        raise ValueError('AUTHORITY_CHANGED')
    hashes = reg.get('task_hashes')
    if not isinstance(hashes, dict) or set(hashes) != {f'{s}:{f}' for s, f in EXPECTED}:
        raise ValueError('TASK_BINDINGS_CHANGED')
    for h in hashes.values():
        _digest(h, 'TASK')


def _uncertainty(row):
    tokens = row.get('tokens')
    feats = row.get('features')
    if not isinstance(tokens, list) or not isinstance(feats, dict):
        raise ValueError('TOKEN_FEATURE_MISSING')
    for t in tokens:
        if (not isinstance(t, dict) or not isinstance(t.get('token'), str)
                or type(t.get('logprob')) not in (float, int) or not math.isfinite(t['logprob'])
                or t['logprob'] > 0):
            raise ValueError('TOKEN_INVALID')
    lp = feats.get('digit_min_logprob')
    if type(lp) not in (float, int) or not math.isfinite(lp) or lp > 0:
        raise ValueError('FEATURE_INVALID')
    digit_lps = [t['logprob'] for t in tokens if any(ch.isdigit() for ch in t['token'])]
    if not digit_lps:
        if lp != 0.0:
            raise ValueError('NO_DIGIT_FEATURE_MISMATCH')
        return math.inf
    if abs(min(digit_lps)-lp) > 1e-8:
        raise ValueError('FEATURE_TOKEN_MISMATCH')
    return -lp


def _metrics(rows):
    selected = [r for r in rows if r['_selected']]
    answered = len(selected)
    correct = sum(r['pass'] for r in selected)
    raw_correct = sum(r['pass'] for r in rows)
    wrong = answered - correct
    ca = raw_correct - correct
    wa = len(rows) - raw_correct - wrong
    util = 4*correct - 8*wrong - 2*ca - wa
    base = 4*raw_correct - 8*(len(rows)-raw_correct)
    return {'n': len(rows), 'answered': answered, 'wrong_answered': wrong,
            'correct_answered': correct, 'correct_abstained': ca, 'wrong_abstained': wa,
            'coverage': answered/len(rows),
            'selective_error_rate': wrong/answered if answered else None,
            'raw_error_rate': (len(rows)-raw_correct)/len(rows),
            'utility_quarters': util, 'raw_utility_quarters': base,
            'utility_delta_quarters': util-base}


def seal(candidate_path):
    candidate = read_json(candidate_path)
    if candidate.get('phase') != 'REGISTRATION_CANDIDATE_NOT_YET_SEALED':
        raise ValueError('NOT_A_REGISTRATION_CANDIDATE')
    sealed = dict(candidate, phase='SEALED_BEFORE_NATIVE')
    validate_reg(sealed)
    return sealed


def evaluate(reg_path, capture_path):
    reg = read_json(reg_path)
    validate_reg(reg)
    capture = read_json(capture_path)
    if capture.get('schema') != CAPTURE_SCHEMA:
        raise ValueError('CAPTURE_SCHEMA_INVALID')
    if capture.get('registration_sha256') != sha(reg_path):
        raise ValueError('REGISTRATION_HASH_MISMATCH')
    for k in ('model_sha256', 'runner_sha256', 'capture_script_sha256', 'source_tree_sha256',
              'source_commit', 'task_manifest_sha256'):
        if capture.get(k) != reg[k]:
            raise ValueError(f'CAPTURE_{k.upper()}_MISMATCH')
    by_key = _identity(capture.get('rows'))
    rows = []
    for key in sorted(EXPECTED):
        r = dict(by_key[key])
        if r['task_sha256'] != reg['task_hashes'][f'{key[0]}:{key[1]}']:
            raise ValueError('CAPTURE_TASK_MISMATCH')
        if type(r.get('pass')) is not bool or r.get('answer_stream_matches_output') is not True:
            raise ValueError('CAPTURE_LABEL_INVALID')
        r['_selected'] = _uncertainty(r) <= THRESHOLD
        rows.append(r)
    combined = _metrics(rows)
    by_kind = {kind: _metrics([r for r in rows if r['fixture'].startswith(kind)]) for kind in KINDS}
    by_seed = {str(seed): _metrics([r for r in rows if r['seed'] == seed]) for seed in SEEDS}
    by_seed_kind = {str(seed): {kind: _metrics([r for r in rows if r['seed'] == seed and r['fixture'].startswith(kind)])
                                for kind in KINDS} for seed in SEEDS}
    reasons = []
    if combined['coverage'] < .70:
        reasons.append('GLOBAL_COVERAGE_FAIL')
    risk = combined['selective_error_rate']
    if risk is None or combined['raw_error_rate']-risk < .10:
        reasons.append('GLOBAL_RISK_REDUCTION_FAIL')
    if combined['utility_delta_quarters'] < 1:
        reasons.append('ABSTENTION_UTILITY_FAIL')
    for kind, m in by_kind.items():
        if m['coverage'] < .60:
            reasons.append(f'{kind.upper()}_COVERAGE_FAIL')
        if m['selective_error_rate'] is None or m['selective_error_rate'] > .20:
            reasons.append(f'{kind.upper()}_RISK_FAIL')
        if m['utility_delta_quarters'] < 0:
            reasons.append(f'{kind.upper()}_UTILITY_FAIL')
    for seed, m in by_seed.items():
        if m['coverage'] < .70:
            reasons.append(f'SEED_{seed}_COVERAGE_FAIL')
        for kind, sm in by_seed_kind[seed].items():
            if sm['coverage'] < .60:
                reasons.append(f'SEED_{seed}_{kind.upper()}_COVERAGE_FAIL')
            if sm['selective_error_rate'] is None or sm['selective_error_rate'] > .20:
                reasons.append(f'SEED_{seed}_{kind.upper()}_RISK_FAIL')
    return {'schema': SCHEMA, 'phase': 'FUTURE_CAPTURE_OFFLINE_EVALUATION',
            'registration_sha256': sha(reg_path), 'capture_sha256': sha(capture_path),
            'combined': combined, 'by_kind': by_kind, 'by_seed': by_seed, 'by_seed_kind': by_seed_kind,
            'failure_reasons': reasons, 'verdict': 'PROSPECTIVE_CRITERIA_MET_NO_DEPLOYMENT' if not reasons else 'NOT_SUPPORTED',
            'production_authority': 0, 'canonical_gate_pass': False,
            'evidence_class': 'OFFLINE_REPLAY_OF_FUTURE_NATIVE_OUTPUTS_NOT_REDRMI',
            'native_executed_by_this_script': False, 'redmi_measured_by_this_script': False,
            'claim_limit': 'Even a prospective PASS cannot enable runtime policy without independent review.'}


def write_once(path, data):
    p = Path(path)
    if p.exists():
        raise ValueError('REFUSE_OVERWRITE')
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=p.parent, prefix='.partial-', delete=False) as f:
        tmp = Path(f.name)
        json.dump(data, f, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    try:
        os.link(tmp, p)
    finally:
        tmp.unlink(missing_ok=True)
    fd = os.open(p.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=('prepare', 'seal', 'evaluate'))
    ap.add_argument('first', type=Path)
    ap.add_argument('second', type=Path)
    ap.add_argument('output', nargs='?', type=Path)
    args = ap.parse_args()
    if args.phase == 'prepare':
        if args.output is None: ap.error('prepare requires task_manifest.json pins.json candidate.json')
        doc = prepare(args.first, read_json(args.second))
        out = args.output
    elif args.phase == 'seal':
        if args.output is not None: ap.error('seal requires candidate.json sealed.json')
        doc = seal(args.first)
        out = args.second
    else:
        if args.output is None: ap.error('evaluate requires sealed.json capture.json report.json')
        doc = evaluate(args.first, args.second)
        out = args.output
    write_once(out, doc)
    print(json.dumps({'phase': doc['phase'], 'output': str(out),
                      'verdict': doc.get('verdict'), 'production_authority': 0}))


if __name__ == '__main__':
    main()