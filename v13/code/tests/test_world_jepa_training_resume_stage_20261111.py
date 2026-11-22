"""Exercise optimizer-bound World-JEPA through the single current stager."""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_stream_guard_world_pin_matches_integrated_jepa_output():
    # Expose the exact upstream composer output before the full stager fails.
    spec = importlib.util.spec_from_file_location(
        'jepa_guard_pin_probe', CODE / 'scripts/integrated_jepa_guard_candidate_20261110.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.build_sources(CODE)
    actual = hashlib.sha256(result['v13/online_world.py']).hexdigest()
    stream = (CODE / 'scripts/integrated_predictor_stream_guard_20261110.py').read_text()
    marker = "PREVIOUS_WORLD_SHA = '"
    start = stream.index(marker) + len(marker)
    expected = stream[start:start + 64]
    assert actual == expected, f'JEPA stream pin mismatch: expected={expected} actual={actual}'


def test_world_jepa_training_state_in_real_staged_runtime(tmp_path):
    spec = importlib.util.spec_from_file_location('resume_stage', CODE / 'scripts/stage_integrated_candidate.py')
    stager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stager)
    dest = tmp_path / 'candidate'
    stager.stage(CODE, dest)
    (dest / 'tests').mkdir(exist_ok=True)
    for name in ('integrated_jepa_disposable_cases.py', 'world_jepa_training_resume_disposable_cases_20261111.py'):
        shutil.copyfile(CODE / 'tests' / name, dest / 'tests' / name)
    shutil.copyfile(CODE / 'tests' / 'test_v14_world_jepa_postcommit_runtime.py',
                    dest / 'tests' / 'test_v14_world_jepa_postcommit_runtime.py')
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-s',
                             'tests/world_jepa_training_resume_disposable_cases_20261111.py'],
                            cwd=dest, capture_output=True, text=True, timeout=120,
                            env=dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1'))
    assert result.returncode == 0, result.stdout + result.stderr
    print(result.stdout)
    staged_consumer = subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', '-s',
         'tests/test_v14_world_jepa_postcommit_runtime.py'],
        cwd=dest, capture_output=True, text=True, timeout=120,
        env=dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1'))
    assert staged_consumer.returncode == 0, staged_consumer.stdout + staged_consumer.stderr
    print(staged_consumer.stdout)
