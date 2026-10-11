#!/usr/bin/env python3
"""Non-native guards for the authored baseline-norm numeric fixture."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_native_midlayer_effect import authored_numeric_delta, NUMERIC_DELTA_POLICY


def run_guards():
    checks = {}
    small = [0.02] * 1024
    large = [4.0] * 1024
    delta = authored_numeric_delta(small)
    scaled = authored_numeric_delta(large)
    l2 = float(np.linalg.norm(np.asarray(delta, dtype=np.float64)))
    baseline_l2 = float(np.linalg.norm(np.asarray(small, dtype=np.float64)))
    checks['exact_dimension'] = len(delta) == 1024
    checks['finite_f32_coordinates'] = bool(np.isfinite(np.asarray(delta, dtype=np.float32)).all())
    checks['actual_f32_encoding'] = all(float(np.float32(x)) == x for x in delta)
    checks['alternating_signs'] = all((x > 0) == (i % 2 == 0) for i, x in enumerate(delta))
    checks['equal_absolute_coordinates'] = all(abs(x) == abs(delta[0]) for x in delta)
    checks['baseline_norm_relative_rule'] = math.isclose(l2 / baseline_l2, .005, rel_tol=1e-6)
    checks['unchanged_relative_cap_headroom'] = 0 < l2 / baseline_l2 < .01
    checks['unchanged_absolute_cap_headroom'] = 0 < l2 < .125
    checks['absolute_rule_for_large_baseline'] = math.isclose(float(np.linalg.norm(scaled)), .0625, rel_tol=1e-6)
    checks['deterministic_repetition'] = delta == authored_numeric_delta(small)
    # The policy consumes the norm alone. Sign/permutation changes with the same
    # norm must produce the same fixture; native logits never enter this API.
    checks['baseline_sign_invariant'] = delta == authored_numeric_delta([-x for x in small])
    permutation = [float(i + 1) / 100000 for i in range(1024)]
    checks['baseline_permutation_invariant'] = authored_numeric_delta(permutation) == authored_numeric_delta(list(reversed(permutation)))
    checks['no_baseline_mutation'] = small == [0.02] * 1024
    malformed = {
        'wrong_shape_rejected': small[:-1],
        'matrix_rejected': [small],
        'bool_rejected': [True] + small[1:],
        'string_coercion_rejected': ['0.02'] + small[1:],
        'none_rejected': [None] + small[1:],
        'nan_rejected': [float('nan')] + small[1:],
        'positive_infinity_rejected': [float('inf')] + small[1:],
        'negative_infinity_rejected': [-float('inf')] + small[1:],
        'f32_overflow_rejected': [float(np.finfo(np.float32).max) * 2] + small[1:],
        'zero_state_rejected': [0.] * 1024,
        'unrepresentable_update_rejected': [1e-100] * 1024,
    }
    for name, value in malformed.items():
        try:
            authored_numeric_delta(value)
        except (ValueError, OverflowError):
            checks[name] = True
        else:
            checks[name] = False
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    args = parser.parse_args()
    checks = run_guards()
    source = Path(__file__).with_name('test_native_midlayer_effect.py')
    result = {'schema': 'V13_MIDLAYER_NUMERIC_POLICY_GUARDS_V1',
              'status': 'NON_NATIVE_POLICY_GUARDS_PASS' if all(checks.values()) else 'NON_NATIVE_POLICY_GUARDS_FAIL',
              'checks': checks, 'guard_count': len(checks), 'policy': NUMERIC_DELTA_POLICY,
              'helper_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'native_tensor_execution_performed': False,
              'native_rerun_status': 'ACTUAL_RERUN_PENDING',
              'production_authority': 0, 'receiver_authority': 0, 'training_authority': 0,
              'scope': 'Synthetic numeric policy guards only; no native output or receiver effect proof.'}
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
