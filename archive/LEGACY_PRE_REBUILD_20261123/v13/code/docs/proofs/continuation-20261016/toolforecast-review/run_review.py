#!/usr/bin/env python3
"""Close exact baseline/fixed ToolForecast lifecycle evidence. No native jobs."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types
import unittest
from unittest.mock import patch

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p / 'v13/code/v13/toolforecast.py').is_file())
APP = ROOT / 'v13/code'
sys.path[:0] = [str(APP), str(APP / 'tests')]
import test_toolforecast_review_20261016 as review

BASE = '1941d07afeb57299d7d5a466fd1eb44ec2569dfe'
BASE_SHA = 'b3ff2494cd0a54005942d36839ca4ff8d6a9e41b73c003605dcd0c45514fad64'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(names, output):
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    stream = io.StringIO()
    start = time.monotonic()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (OUT / output).write_text(stream.getvalue())
    return {'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
            'expected_failures': len(result.expectedFailures), 'skipped': len(result.skipped),
            'seconds': round(time.monotonic() - start, 3), 'success': result.wasSuccessful()}


def main():
    tracked = ['v13/toolforecast.py', 'scripts/install_tool_forecast.py', 'tests/test_toolforecast.py',
               'tests/test_toolforecast_review_20261016.py', 'specs/tool-forecast.json']
    before = {name: sha(APP / name) for name in tracked}
    path = OUT / 'baseline-toolforecast-1941d07.py'
    if not path.exists():
        blob = subprocess.check_output(['git', 'show', BASE + ':v13/code/v13/toolforecast.py'], cwd=ROOT)
        path.write_bytes(blob)
    if sha(path) != BASE_SHA:
        raise ValueError('Baseline bytes are not the reviewed M commit')
    baseline = types.ModuleType('v13._toolforecast_review_baseline_20261016')
    baseline.__file__ = str(path)
    baseline.__package__ = 'v13'
    exec(compile(path.read_text(), str(path), 'exec'), baseline.__dict__)
    regression = 'test_toolforecast_review_20261016.ToolForecastReview20261016.test_outcome_encoder_change_after_initial_guard_must_not_score_or_append'
    with patch.object(review, 'F', baseline):
        original_result = run([regression], 'baseline-regression.txt')
        original = review.reproduce_outcome_encoder_window()
    selected = ['test_toolforecast_review_20261016',
                'test_toolforecast.CheckpointTests.test_adaptation_bound_to_competence_encoder_and_retention',
                'test_toolforecast.CheckpointTests.test_experience_never_mixes_encoders',
                'test_toolforecast.CheckpointTests.test_missing_or_failed_encoder_gives_no_forecast',
                'test_toolforecast.LivePathTests.test_damaged_encoder_config_status_and_no_forecast',
                'test_toolforecast.LivePathTests.test_checkpoint_changed_since_forecast_is_not_scored',
                'test_toolforecast.LivePathTests.test_pending_capacity_removes_evicted_context_taps',
                'test_toolforecast.InstallLifecycleTests.test_failed_or_interrupted_reinstall_keeps_previous_generation']
    fixed_result = run(selected, 'tests.txt')
    fixed = review.reproduce_outcome_encoder_window()
    after = {name: sha(APP / name) for name in tracked}
    (OUT / 'reproduction-before.json').write_text(json.dumps(original, indent=2) + '\n')
    (OUT / 'reproduction-after.json').write_text(json.dumps(fixed, indent=2) + '\n')
    report = {'schema': 'V13_TOOLFORECAST_REVIEW_20261016_V1', 'baseline_commit': BASE,
              'baseline_runtime_sha256': BASE_SHA, 'evidence': 'SYNTHETIC_SOFTWARE_ONLY', 'native_jobs': 0,
              'redmi_measurements': False, 'numerical_training_gate_changes': False,
              'source_unchanged_during_validation': before == after, 'source_hashes': after,
              'baseline_regression': original_result, 'fixed_tests': fixed_result,
              'reproduction_before': original, 'reproduction_after': fixed,
              'limits': ['filesystem snapshot is not an atomic read transaction or race-freedom proof',
                         'binary/model hashes cached by path/dev/inode/size/mtime/ctime; unchanged files avoid full GGUF rehash',
                         'checkpoint/competence file hashes are read before and after outcome tap; Redmi IO cost unmeasured',
                         'dynamic backend/shared-library identity is not supplied by current encoder records',
                         'existing telemetry persistence failure may propagate; pending context safety tested',
                         'new uncommitted context may remain after failed prediction persistence']}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    assert original_result['failures'] == 1 and original_result['errors'] == 0
    assert original['status'] == 'SCORED' and original['experience_rows'] == 1
    assert original['actual_outcome_tool_sha256'] != original['experience_tool_sha256']
    assert fixed_result['success'] and fixed_result['expected_failures'] == 0
    assert fixed['status'] == 'SOURCE_CHANGED_DURING_OBSERVE' and fixed['experience_rows'] == 0
    assert before == after
    files = {p.name: sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'SHA256SUMS.json'}
    (OUT / 'SHA256SUMS.json').write_text(json.dumps(files, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
