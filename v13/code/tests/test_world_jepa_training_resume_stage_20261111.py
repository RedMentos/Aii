"""Exercise optimizer-bound World-JEPA through the single current stager."""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_prepostcommit_runtime_hash_and_replacement_four_diagnostic():
    builder_path = CODE / 'scripts/termux_runtime_recovery_candidate_20261112.py'
    spec = importlib.util.spec_from_file_location('prepostcommit_builder', builder_path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    result = builder.build_sources(CODE, include_postcommit=False)
    runtime = result['v13/runtime.py']
    assert hashlib.sha256(runtime).hexdigest() == '650f78dc277cc06d23f9c0776bae7168b2bb7878e778a2fb01b5203aba86c4e4'

    post_path = CODE / 'scripts/postcommit_observer_candidate_20261116.py'
    post_spec = importlib.util.spec_from_file_location('postcommit_diagnostic', post_path)
    post = importlib.util.module_from_spec(post_spec)
    post_spec.loader.exec_module(post)
    before, after = post.REPLACEMENTS[4]
    old_count = runtime.count(before.encode('utf-8'))
    new_count = runtime.count(after.encode('utf-8'))
    print('POSTCOMMIT_REPLACEMENT_4_COUNTS', old_count, new_count)
    for number, line in enumerate(runtime.decode('utf-8', 'replace').splitlines(), 1):
        if "if status=='FINAL'" in line:
            print('PRE_POSTCOMMIT_FINAL_CONDITION', number, line[:1400])


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
