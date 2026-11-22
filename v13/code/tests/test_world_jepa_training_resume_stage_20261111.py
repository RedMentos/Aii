"""Exercise optimizer-bound World-JEPA through the single current stager."""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


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


def _load_qa_builder(path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_lifecycle_pins_and_downstream_builder_chain_match_exact_files():
    failures = []

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def git_blob_sha1(path):
        raw = path.read_bytes()
        return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\\0' + raw).hexdigest()

    def check(label, expected, actual):
        print(f'QA_BUILDER_PIN {label} expected={expected} actual={actual}')
        if expected != actual:
            failures.append(f'{label}: expected {expected}, actual {actual}')

    lifecycle_path = CODE / 'scripts/source_lifecycle_lock_integration_candidate.py'
    lifecycle = _load_qa_builder(lifecycle_path, 'qa_source_lifecycle')
    for name, expected in lifecycle.PINS.items():
        actual = digest(CODE / 'v13' / name)
        print(f'QA_SOURCE_PIN {name} expected={expected} actual={actual}')
        if expected != actual:
            failures.append(f'source {name}: expected {expected}, actual {actual}')

    memory_world_path = CODE / 'scripts/integrated_memory_world_candidate_20261111.py'
    memory_world = _load_qa_builder(memory_world_path, 'qa_memory_world')
    c3_base_path = CODE / 'scripts/integrated_c3_resume_candidate_20261110.py'
    check('memory_world_base', memory_world.BASE_BUILDER_SHA, digest(c3_base_path))
    check('lifecycle', memory_world.LIFECYCLE_BUILDER_SHA, digest(lifecycle_path))

    feedback_path = CODE / 'scripts/integrated_feedback_bootstrap_candidate_20261111.py'
    feedback = _load_qa_builder(feedback_path, 'qa_feedback')
    check('feedback', feedback.BASE_BUILDER_SHA, digest(memory_world_path))

    context_path = CODE / 'scripts/integrated_context_recall_candidate_20261111.py'
    context = _load_qa_builder(context_path, 'qa_context')
    check('context', context.BASE_BUILDER_SHA, digest(feedback_path))

    training_path = CODE / 'scripts/integrated_world_training_resume_candidate_20261111.py'
    training = _load_qa_builder(training_path, 'qa_world_training')
    check('training', training.BASE_SHA, digest(context_path))

    termux12_path = CODE / 'scripts/termux_runtime_recovery_candidate_20261112.py'
    termux12 = _load_qa_builder(termux12_path, 'qa_termux12')
    training_key = 'scripts/integrated_world_training_resume_candidate_20261111.py'
    check('termux12', termux12.BUILDERS[training_key], digest(training_path))

    termux21_path = CODE / 'scripts/termux_runtime_recovery_candidate_20261121.py'
    termux21 = _load_qa_builder(termux21_path, 'qa_termux21')
    check('termux21', termux21.BASE_BUILDER_BLOB_SHA1, git_blob_sha1(termux12_path))

    stage_path = CODE / 'scripts/stage_integrated_candidate.py'
    stage = _load_qa_builder(stage_path, 'qa_integrated_stage')
    check('stage', stage.BUILDER_SHA, digest(termux21_path))

    deploy_path = CODE / 'v13' / 'runtime_deploy.py'
    deploy = _load_qa_builder(deploy_path, 'qa_runtime_deploy')
    check('runtime_deploy_stager', deploy.STAGER_SHA256, digest(stage_path))

    assert not failures, '\\n'.join(failures)
