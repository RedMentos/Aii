#!/usr/bin/env python3
"""Descriptive, fail-closed comparisons for the preregistered Dream2 cohort.

No utility or architecture acceptance threshold is introduced here. Deltas
compare the original metrics against the same seed's two original controls.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ARMS = ('none', 'replay_exact', 'dream_validated', 'dream_self', 'dream_unanchored')
SEEDS = (13, 21, 34)
METRICS = {
    'A_recall': ('A', 'recall'),
    'A_paraphrase': ('A', 'paraphrase'),
    'B_recall': ('B', 'recall'),
    'B_paraphrase': ('B', 'paraphrase'),
    'probe_retention': ('probe_retention',),
    'near_miss_leak': ('near_miss_leak',),
    'kl_to_base': ('kl_to_base',),
}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode()


def metrics(evaluation):
    out = {}
    for name, keys in METRICS.items():
        value = evaluation
        for key in keys:
            value = value[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Missing or non-finite evaluation: '+name)
        if value < 0 or (name != 'kl_to_base' and value > 1):
            raise ValueError('Out-of-range evaluation: '+name)
        out[name] = float(value)
    return out


def analyze(doc, source_sha256):
    if doc.get('schema') != 'v13-dream-ablation-v1' or doc.get('proof_version') != 2:
        raise ValueError('Bound Dream2 proof_version 2 required')
    binding = doc['run_binding']
    config = binding['config']
    if config['seeds'] != list(SEEDS) or config['b_steps'] != 40 or binding['arms'] != list(ARMS):
        raise ValueError('Original Dream2 3-seed/5-arm/40-step cohort required')
    if doc.get('phone_measured') is not False or doc.get('canonical_gate_pass') is not False:
        raise ValueError('This cloud ablation cannot claim phone or canonical acceptance')
    rows = doc['runs']
    if doc.get('row_sha256') != [sha(encoded(row)) for row in rows]:
        raise ValueError('Completed arm bytes changed')
    expected = {(seed, arm) for seed in SEEDS for arm in ARMS}
    by_pair = {}
    for row in rows:
        pair = (row['seed'], row['arm'])
        if pair not in expected or pair in by_pair:
            raise ValueError('Unexpected or duplicate arm')
        phase_a = row.get('phase_a', {})
        if (not isinstance(phase_a.get('steps'), int) or isinstance(phase_a.get('steps'), bool)
                or phase_a['steps'] < 1 or phase_a.get('items') != 4
                or row['phase_b']['steps'] != 40
                or not isinstance(row.get('raw_generations'), list) or not row['raw_generations']):
            raise ValueError('Incomplete arm or absent raw generation evidence')
        metrics(row['after_a']); metrics(row['after_b'])
        by_pair[pair] = row
    if doc.get('status') not in {'RUNNING', 'COMPLETE'}:
        raise ValueError('Unknown cohort status')
    complete = len(by_pair) == len(expected) and doc['status'] == 'COMPLETE'
    if doc['status'] == 'COMPLETE' and not complete:
        raise ValueError('Complete marker lacks the full cohort')
    summary = {
        'schema': 'v13-dream2-comparisons-v1',
        'status': 'COMPLETE_SCOPED_COMPARISONS' if complete else 'RUNNING_PARTIAL',
        'source_sha256': source_sha256,
        'run_binding_sha256': sha(encoded(binding)),
        'completed_arms': len(by_pair), 'expected_arms': len(expected),
        'missing_arms': [{'seed': seed, 'arm': arm} for seed in SEEDS for arm in ARMS
                         if (seed, arm) not in by_pair],
        'phone_measured': False, 'canonical_gate_pass': False,
        'metric_direction': {'higher_is_better': list(METRICS)[:5],
                             'lower_is_better': ['near_miss_leak', 'kl_to_base']},
        'per_seed': [], 'complete_cohort_arm_means': None,
        'claim_limit': 'Descriptive comparisons only, no new acceptance threshold. Historical 230M LoRA/text-question rehearsal; does not prove deployed 350M memory, broader tasks, phone behavior or full architecture.',
    }
    for seed in SEEDS:
        seed_rows = {arm: by_pair[(seed, arm)] for arm in ARMS if (seed, arm) in by_pair}
        item = {'seed': seed, 'arms': {}, 'dream_control_deltas': []}
        for arm, row in seed_rows.items():
            a, b = metrics(row['after_a']), metrics(row['after_b'])
            item['arms'][arm] = {'after_a': a, 'after_b': b,
                'retention_change_during_B': {key: round(b[key]-a[key], 6)
                                             for key in ('A_recall', 'A_paraphrase')}}
        if 'none' in item['arms']:
            delta = item['arms']['none']['retention_change_during_B']
            item['forgetting_observed_without_rehearsal'] = any(v < 0 for v in delta.values())
        for arm in ARMS[2:]:
            if arm not in seed_rows:
                continue
            candidate = metrics(seed_rows[arm]['after_b'])
            for control in ARMS[:2]:
                if control not in seed_rows:
                    continue
                reference = metrics(seed_rows[control]['after_b'])
                item['dream_control_deltas'].append({'arm': arm, 'control': control,
                    'candidate_minus_control': {key: round(candidate[key]-reference[key], 6)
                                                for key in METRICS}})
        summary['per_seed'].append(item)
    if complete:
        summary['complete_cohort_arm_means'] = {
            arm: {key: round(sum(metrics(by_pair[(seed, arm)]['after_b'])[key]
                                 for seed in SEEDS)/len(SEEDS), 6)
                  for key in METRICS}
            for arm in ARMS
        }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    raw = Path(args.report).read_bytes()
    result = analyze(json.loads(raw), sha(raw))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_name(out.name+'.tmp')
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    temporary.replace(out)
    print(json.dumps({'status': result['status'], 'completed_arms': result['completed_arms'],
                      'expected_arms': result['expected_arms']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
