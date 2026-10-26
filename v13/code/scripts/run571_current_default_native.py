#!/usr/bin/env python3
"""Run571: fail-stop executor for NEW Run570 current-default vs legacy cohort.

No inference happens without --execute and a previously persisted exact source
plan. This does not change or promote original frozen Run491/500/504/558.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import time

import run496_heldout10_native_pilot as original_native
import run570_current_default_cohort as new
import step2_z2_timescale as z2
import step2_z2b_seeds as z2b

PLAN = 'RUN570_PLAN.json'
RESULT = 'RUN571_RESULT.json'
PROGRESS = 'RUN571_PROGRESS.jsonl'
PREFLIGHT = 'RUN571_INSTALLED_PREFLIGHT.json'
ARMS = new.ARMS
VARIANTS = set(new.VARIANTS)
ROWS_PER_ARM = 6 * len(VARIANTS)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def write_new(path, data):
    path = Path(path)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2,
                                allow_nan=False) + '\n')


def prepare_plan(work):
    work = Path(work)
    require(not work.is_symlink(), 'WORK_SYMLINK_REFUSED')
    work.mkdir(parents=True, exist_ok=True)
    require(not any(work.iterdir()), 'FRESH_WORK_DIRECTORY_REQUIRED')
    data = new.registration()
    write_new(work / PLAN, data)
    return data


def exact_plan(work):
    path = Path(work) / PLAN
    require(path.is_file() and not path.is_symlink(), 'SOURCE_PLAN_MISSING')
    data = json.loads(path.read_text(encoding='utf-8'))
    require(data == new.registration(), 'SOURCE_PLAN_CHANGED')
    require(data['native_executed'] is False and
            data['planned_native_consumer_rows'] == 84 and
            data['canonical_gate_pass'] is False and
            data['step2_exit'] == 'UTILITY_FAIL', 'SOURCE_PLAN_AUTHORITY_CHANGED')
    return data


@contextmanager
def isolated_harness():
    """In-memory source/config swap only; restores even on native exceptions."""
    fixtures = z2.FIXTURES
    z2_arms = dict(z2.ARMS)
    z2b_arms = dict(z2b.ARMS)
    seeds = z2b.SEEDS
    try:
        z2.FIXTURES = [z2.episode(*spec) for spec in new.SPECS]
        new.validate_fixtures(z2.FIXTURES)
        for arm, cfg in new.configs().items():
            z2.ARMS[arm] = dict(cfg)
            z2b.ARMS[arm] = {'base': arm, 'query': False}
        z2b.SEEDS = (new.SEED,)
        yield
    finally:
        z2.FIXTURES = fixtures
        z2.ARMS.clear()
        z2.ARMS.update(z2_arms)
        z2b.ARMS.clear()
        z2b.ARMS.update(z2b_arms)
        z2b.SEEDS = seeds


def append_progress(path, record):
    path = Path(path)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def validate_arm(work, arm, summary):
    require(arm in ARMS, 'UNKNOWN_ARM')
    rid = z2b.run_id(arm, new.SEED)
    source_path = Path(work) / ('step2_' + rid + '.json')
    tool_path = Path(work) / ('tool_' + rid + '.json')
    summary_path = Path(work) / ('summary_' + rid + '.json')
    require(all(p.is_file() and not p.is_symlink()
                for p in (source_path, tool_path, summary_path)),
            'NATIVE_ARM_OUTPUT_MISSING')
    source = json.loads(source_path.read_text())
    tool = json.loads(tool_path.read_text())
    saved_summary = json.loads(summary_path.read_text())
    require(saved_summary == summary and
            summary.get('run') == rid and summary.get('arm') == arm and
            summary.get('seed') == new.SEED,
            'ARM_SUMMARY_IDENTITY_CHANGED')
    require(source.get('installed_artifacts_unchanged') is True and
            tool.get('installed_artifacts_unchanged') is True,
            'MODEL_ARTIFACT_CHANGED')
    source_rows = source.get('rows')
    tool_rows = tool.get('rows')
    require(type(source_rows) is list and type(tool_rows) is list and
            len(source_rows) == len(tool_rows) == ROWS_PER_ARM,
            'NATIVE_ROW_COUNT')
    expected = {(spec[0], variant) for spec in new.SPECS for variant in VARIANTS}
    sr = {(r.get('fixture'), r.get('variant')): r for r in source_rows}
    tr = {(r.get('fixture'), r.get('variant')): r for r in tool_rows}
    require(len(sr) == len(tr) == ROWS_PER_ARM and
            set(sr) == set(tr) == expected, 'NATIVE_ROW_KEYS')
    for key in expected:
        s, t = sr[key], tr[key]
        require(s.get('oracle_visible_to_native') is False and
                t.get('oracle_visible_to_native') is False and
                t.get('status') == 'RECORDED', 'ORACLE_OR_ROW_STATUS')
        require(t.get('consumer_messages_sha256') ==
                hashlib.sha256(new.canonical(s['consumer_messages'])).hexdigest(),
                'CONSUMER_SOURCE_BINDING_CHANGED')
        score = t.get('score', {}).get('utility')
        require(type(score) in (int, float) and math.isfinite(score) and
                0 <= score <= 1, 'NONFINITE_OR_INVALID_UTILITY')
    summaries = summary.get('tool_summary')
    require(type(summaries) is dict and set(summaries) == VARIANTS and
            all(type(v) is dict and v.get('wrong_committed') == 0
                for v in summaries.values()), 'WRONG_COMMITTED_OR_VARIANT_MISSING')
    return {'arm': arm, 'seed': new.SEED, 'rows': ROWS_PER_ARM,
            'source_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
            'tool_sha256': hashlib.sha256(tool_path.read_bytes()).hexdigest(),
            'summary_sha256': hashlib.sha256(summary_path.read_bytes()).hexdigest(),
            'mean_utility': {v: summaries[v]['mean_utility'] for v in sorted(VARIANTS)},
            'wrong_committed': 0}


def execute(work, installed):
    work = Path(work)
    require(not work.is_symlink() and work.is_dir(), 'WORK_DIRECTORY_REQUIRED')
    plan = exact_plan(work)
    require(not any((work / p).exists() for p in (RESULT, PROGRESS, PREFLIGHT)),
            'REFUSE_REUSE_OR_PARTIAL_NATIVE_ATTEMPT')
    require(not any((work / (z2b.run_id(arm, new.SEED) + '-home')).exists()
                    for arm in ARMS), 'REFUSE_REUSE_NATIVE_ARM_HOME')
    preflight = original_native.verify_installed(installed)
    require(preflight['model_sha256'] == plan['original_model_sha256_expected_not_retrieved'] and
            preflight['runner_sha256'] == plan['original_runner_sha256_expected_not_retrieved'] and
            bool(preflight['runtime_library_sha256']) and
            preflight['native_executed'] is False,
            'INSTALLED_PINNED_SOURCE_MISMATCH')
    write_new(work / PREFLIGHT, preflight)
    receipts = []
    with isolated_harness():
        for arm in ARMS:
            append_progress(work / PROGRESS, {'arm': arm, 'state': 'STARTED',
                                               'seed': new.SEED, 'time_ns': time.time_ns()})
            summary = z2b.run_one(installed, work, arm, new.SEED)
            receipt = validate_arm(work, arm, summary)
            receipts.append(receipt)
            append_progress(work / PROGRESS, {'arm': arm, 'state': 'FINISHED',
                                               'seed': new.SEED,
                                               'receipt_sha256': new.digest(receipt),
                                               'time_ns': time.time_ns()})
    require(len(receipts) == 2 and sum(r['rows'] for r in receipts) == 84,
            'NATIVE_COHORT_INCOMPLETE')
    result = {'schema': 'V13_RUN571_NEW_CURRENT_LEGACY_NATIVE_STRUCTURAL_V1',
              'status': 'STRUCTURALLY_VERIFIED_ONLY_NOT_CANONICAL',
              'source_plan_sha256': hashlib.sha256((work / PLAN).read_bytes()).hexdigest(),
              'row_keys_sha256': plan['row_keys_sha256'],
              'native_executed': True, 'rows_verified': 84, 'receipts': receipts,
              'canonical_gate_pass': False, 'step2_exit': 'UTILITY_FAIL',
              'b3_l1': 'FAIL', 'body_jepa': 'UNAVAILABLE',
              'jepa_weight': 0, 'redmi_measured': False,
              'claim_limit': 'New paired native cohort, requires independent original ZIP audit and separate canonical acceptance'}
    write_new(work / RESULT, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--plan', action='store_true')
    modes.add_argument('--execute', action='store_true')
    parser.add_argument('--installed-home', type=Path)
    args = parser.parse_args()
    if args.plan:
        require(args.installed_home is None, 'PLAN_MUST_NOT_LOAD_MODELS')
        result = prepare_plan(args.work)
        print(json.dumps({'status': result['status'], 'rows': 84, 'native_executed': False}))
    else:
        require(args.installed_home is not None, 'INSTALLED_HOME_REQUIRED')
        print(json.dumps(execute(args.work, args.installed_home), sort_keys=True))


if __name__ == '__main__':
    main()
