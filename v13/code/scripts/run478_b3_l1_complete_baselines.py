#!/usr/bin/env python3
"""Run478: fail-closed B3 L1 input-completeness candidate (no authority).

Production l1_gate skips missing baselines, zips unequal seed lengths and
uses zero bytes for absent channels. This isolated wrapper validates a full
registered measurement table before computing a *diagnostic* L1 result.
"""
import math
from v13.b3bridge import l1_gate

REQUIRED = ('NO_MESSAGE', 'LATENT', 'LATENT_SHUFFLED', 'LATENT_RANDOM',
            'EXACT', 'CONTROL', 'SYMBOLIC')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def evaluate(task):
    require(type(task) is dict, 'B3_TASK_NOT_OBJECT')
    acc, by = task.get('acc'), task.get('bytes')
    require(type(acc) is dict and type(by) is dict,
            'B3_ACC_OR_BYTES_NOT_OBJECT')
    require(all(k in acc and k in by for k in REQUIRED),
            'B3_REQUIRED_BASELINE_MISSING')
    require(set(acc) == set(REQUIRED) and set(by) == set(REQUIRED),
            'B3_CHANNEL_COHORT_MISMATCH')
    n = len(acc['NO_MESSAGE']) if type(acc['NO_MESSAGE']) in (list, tuple) else 0
    require(n >= 3, 'B3_TOO_FEW_SEEDS')
    for k in REQUIRED:
        values = acc[k]
        require(type(values) in (list, tuple) and len(values) == n,
                'B3_SEED_COVERAGE_MISMATCH:' + k)
        require(all(type(v) in (int, float) and math.isfinite(v) and
                    0 <= v <= 1 for v in values),
                'B3_ACC_NONFINITE_OR_INVALID:' + k)
        amount = by[k]
        require(type(amount) in (int, float) and math.isfinite(amount) and
                amount >= 0, 'B3_BYTES_INVALID:' + k)
    for key in ('role_drop', 'ood_rate'):
        value = task.get(key)
        require(type(value) in (int, float) and math.isfinite(value) and
                0 <= value <= 1, 'B3_MEASUREMENT_MISSING_OR_INVALID:' + key)
    require(type(task.get('reload_identical')) is bool,
            'B3_RELOAD_MEASUREMENT_MISSING')
    diagnostic = l1_gate(task)
    require(not diagnostic['missing_baselines'], 'B3_INTERNAL_BASELINE_GAP')
    return {'schema':'V13_RUN478_B3_L1_COMPLETE_INPUT_V1',
            'status':'B3_L1_DIAGNOSTIC_NO_AUTHORITY',
            'input_complete':True,
            'seed_count':n,
            'diagnostic_l1_verdict':diagnostic['verdict'],
            'diagnostic_criteria':diagnostic['criteria'],
            'canonical_gate_pass':False,
            'latent_authority':0,
            'b3_l1':'FAIL',
            'step2_exit':'UTILITY_FAIL',
            'body_jepa':'UNAVAILABLE',
            'jepa_weight':0,
            'redmi_measured':False,
            'claim_limit':'Complete synthetic/source table is not native receiver L1/retention proof or permission to activate LATENT.'}
