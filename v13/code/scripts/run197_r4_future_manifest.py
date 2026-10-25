#!/usr/bin/env python3
"""Run197: source-bound R4 future tasks and fail-closed offline native-capture binder.

No model is run by this module. Caller must separately prove that the native
capture was produced by the registered binary, model and source revision.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import run196_r4_stratified_future as R

HISTORICAL_SEEDS = (7, 11)
RAW_KIND = 'V13_R4_C3_UNCERTAINTY_CAPTURE'


def _hash_text(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def _fixtures(seed, tasks):
    rows = []
    for fixture, prompt, nums, checks in tasks(seed):
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError('PROMPT_INVALID')
        if not isinstance(nums, list) or not all(type(n) is int for n in nums):
            raise ValueError('NUMERIC_SCORER_INVALID')
        if not isinstance(checks, dict) or not checks or not all(isinstance(k, str) and isinstance(v, str) for k, v in checks.items()):
            raise ValueError('REGEX_SCORER_INVALID')
        for pat in checks.values():
            re.compile(pat)
        rows.append({'seed': seed, 'fixture': fixture, 'prompt': prompt,
                     'task_sha256': _hash_text(prompt), 'expected_numbers': nums,
                     'expected_checks': checks})
    return rows


def make_manifest(generator_path, scorer_path, tasks=None):
    if tasks is None:
        # In a full checkout only. Do not silently replace the pinned generator.
        from scripts.utility_bench2 import tasks
    future = [r for seed in R.SEEDS for r in _fixtures(seed, tasks)]
    history = [r for seed in HISTORICAL_SEEDS for r in _fixtures(seed, tasks)]
    R._identity(future, task=True)
    historical_hashes = {r['task_sha256'] for r in history}
    if len(historical_hashes) != len(history):
        raise ValueError('HISTORICAL_PROMPT_COLLISION')
    if any(r['task_sha256'] in historical_hashes for r in future):
        raise ValueError('HISTORICAL_PROMPT_OVERLAP')
    return {'schema': R.TASK_SCHEMA, 'rows': future,
            'generator_sha256': R.sha(generator_path), 'scorer_sha256': R.sha(scorer_path),
            'historical_seeds': list(HISTORICAL_SEEDS),
            'historical_prompt_hashes': sorted(historical_hashes),
            'freshness_claim': 'NO_EXACT_PROMPT_OVERLAP_WITH_GENERATOR_SEEDS_7_11_ONLY',
            'production_authority': 0, 'canonical_gate_pass': False}


def _score(output, nums, checks):
    # Exact scoring semantics of utility_bench.score, without importing Runtime.
    flags = {k: re.search(pattern, output) is not None for k, pattern in checks.items()}
    numbers = {str(n): re.search(r'(?<![\d.,])' + str(n) + r'(?![\d])', output) is not None for n in nums}
    return all(flags.values()) and all(numbers.values())


def bind(reg_path, manifest_path, raw_paths, provenance_path, *, tasks=None, generator_path=None, scorer_path=None):
    reg = R.read_json(reg_path)
    R.validate_reg(reg)
    manifest = R.read_json(manifest_path)
    if manifest.get('schema') != R.TASK_SCHEMA or R.sha(manifest_path) != reg['task_manifest_sha256']:
        raise ValueError('MANIFEST_BINDING_MISMATCH')
    # Recompute every task and the historical overlap control from the pinned source.
    # A manifest that merely *claims* a historical hash list is not evidence.
    if tasks is None:
        from scripts.utility_bench2 import tasks
    if generator_path is None:
        generator_path = Path(__file__).resolve().parent / 'utility_bench2.py'
    if scorer_path is None:
        scorer_path = Path(__file__).resolve().parent / 'utility_bench.py'
    if make_manifest(generator_path, scorer_path, tasks=tasks) != manifest:
        raise ValueError('MANIFEST_GENERATOR_RECOMPUTE_MISMATCH')
    task_rows = R._identity(manifest.get('rows'), task=True)
    if not isinstance(manifest.get('historical_prompt_hashes'), list) or len(manifest['historical_prompt_hashes']) != 120:
        raise ValueError('HISTORICAL_NOVELTY_UNPROVEN')
    if manifest.get('historical_seeds') != list(HISTORICAL_SEEDS):
        raise ValueError('HISTORICAL_SEEDS_CHANGED')
    history = set(manifest['historical_prompt_hashes'])
    if any(not isinstance(h, str) or R.HEX64.fullmatch(h) is None for h in history) or len(history) != 120:
        raise ValueError('HISTORICAL_HASHES_INVALID')
    if history & {r['task_sha256'] for r in task_rows.values()}:
        raise ValueError('HISTORICAL_PROMPT_OVERLAP')
    prov = R.read_json(provenance_path)
    for k in ('model_sha256', 'runner_sha256', 'capture_script_sha256',
              'source_tree_sha256', 'source_commit', 'task_manifest_sha256'):
        if prov.get(k) != reg[k]:
            raise ValueError(f'PROVENANCE_{k.upper()}_MISMATCH')
    if prov.get('registration_sha256') != R.sha(reg_path):
        raise ValueError('PROVENANCE_REGISTRATION_MISMATCH')
    raw_hashes = prov.get('raw_capture_sha256s')
    if not isinstance(raw_hashes, dict) or set(raw_hashes) != {str(s) for s in R.SEEDS}:
        raise ValueError('RAW_CAPTURE_HASH_SET_INVALID')
    if len(raw_paths) != len(R.SEEDS):
        raise ValueError('RAW_CAPTURE_COUNT_INVALID')
    combined = []
    for seed, path in zip(R.SEEDS, raw_paths):
        if raw_hashes[str(seed)] != R.sha(path):
            raise ValueError('RAW_CAPTURE_HASH_MISMATCH')
        doc = R.read_json(path)
        if doc.get('kind') != RAW_KIND or type(doc.get('task_seed')) is not int or doc['task_seed'] != seed:
            raise ValueError('RAW_CAPTURE_IDENTITY_MISMATCH')
        rows = doc.get('rows')
        if not isinstance(rows, list) or len(rows) != 60:
            raise ValueError('RAW_CAPTURE_ROW_COUNT_INVALID')
        seen = set()
        for row in rows:
            fixture = row.get('fixture')
            key = (seed, fixture)
            if not isinstance(fixture, str) or key not in task_rows or key in seen:
                raise ValueError('RAW_CAPTURE_FIXTURE_INVALID')
            seen.add(key)
            task = task_rows[key]
            if task['task_sha256'] != reg['task_hashes'][f'{seed}:{fixture}']:
                raise ValueError('REGISTERED_TASK_MISMATCH')
            output = row.get('output')
            if not isinstance(output, str) or len(output) >= 400:
                raise ValueError('RAW_OUTPUT_TRUNCATED_OR_MISSING')
            if row.get('answer_stream_matches_output') is not True:
                raise ValueError('RAW_STREAM_MISMATCH')
            tokens = row.get('tokens')
            if not isinstance(tokens, list) or ''.join(t.get('token', '') for t in tokens).strip() != output.strip():
                raise ValueError('RAW_TOKEN_OUTPUT_MISMATCH')
            score = _score(output, task['expected_numbers'], task['expected_checks'])
            if type(row.get('pass')) is not bool or score != row['pass']:
                raise ValueError('RAW_SCORE_RECOMPUTE_MISMATCH')
            R._uncertainty(row)  # independently verify digit feature against raw token logprobs
            combined.append({'seed': seed, 'fixture': fixture,
                             'task_sha256': task['task_sha256'], 'pass': score,
                             'answer_stream_matches_output': True,
                             'features': row['features'], 'tokens': tokens})
        if len(seen) != 60:
            raise ValueError('RAW_CAPTURE_INCOMPLETE')
    R._identity(combined)
    return {'schema': R.CAPTURE_SCHEMA, 'registration_sha256': R.sha(reg_path),
            **{k: reg[k] for k in ('model_sha256', 'runner_sha256', 'capture_script_sha256',
                                   'source_tree_sha256', 'source_commit', 'task_manifest_sha256')},
            'rows': combined, 'raw_capture_sha256s': raw_hashes,
            'provenance_attestation_sha256': R.sha(provenance_path),
            'evidence_class': 'OFFLINE_BOUND_NATIVE_CAPTURE_CLAIM_UNVERIFIED_BY_ADAPTER',
            'native_executed_by_adapter': False, 'production_authority': 0,
            'canonical_gate_pass': False}


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=('manifest', 'bind'))
    p.add_argument('inputs', nargs='+')
    a = p.parse_args()
    if a.phase == 'manifest':
        if len(a.inputs) != 3: p.error('manifest generator.py scorer.py output.json')
        doc = make_manifest(a.inputs[0], a.inputs[1])
        out = a.inputs[2]
    else:
        if len(a.inputs) != 6: p.error('bind sealed.json tasks.json seed1.json seed2.json provenance.json output.json')
        doc = bind(a.inputs[0], a.inputs[1], a.inputs[2:4], a.inputs[4])
        out = a.inputs[5]
    R.write_once(out, doc)
    print(json.dumps({'phase': a.phase, 'output': out, 'production_authority': 0}))


if __name__ == '__main__': main()