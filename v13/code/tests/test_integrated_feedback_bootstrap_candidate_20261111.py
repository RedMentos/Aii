"""Review catalog and event-bound feedback on the shared V13 test copy."""
import importlib.util
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import pytest

CODE = Path(__file__).resolve().parents[1]


def builder():
    spec = importlib.util.spec_from_file_location('integrated_feedback_bootstrap', CODE / 'scripts/integrated_feedback_bootstrap_candidate_20261111.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_rejects_changed_feedback_source(monkeypatch):
    module = builder()
    altered = dict(module.PINS)
    altered['v13/local_error_route_shadow_candidate.py'] = '0' * 64
    monkeypatch.setattr(module, 'PINS', altered)
    with pytest.raises(ValueError, match='source changed'):
        module.build_sources(CODE)


def regression_selection():
    names = ('test_continuous_predictor_20261108.py', 'integrated_online_world_disposable_cases.py',
             'integrated_jepa_disposable_cases.py', 'predictor_stream_guard_disposable_cases.py',
             'predictor_history_guard_disposable_cases.py', 'body_anchor_guard_disposable_cases_20261110.py',
             'test_body_jepa_checkpoint_fit.py', 'test_lora_resume_safety.py', 'test_lora_trainer.py',
             'c3_resume_disposable_cases_20261110.py', 'source_lifecycle_disposable_cases.py',
             'memory_world_disposable_cases_20261111.py', 'test_archive.py', 'test_vision.py',
             'test_context_os.py', 'test_episodes.py', 'test_semantic_memory.py',
             'test_dataset_probe_candidate_20261109.py', 'test_local_error_route_shadow_candidate_20261109.py',
             'test_world_semantic_evidence_candidate_20261109.py', 'test_feedback_shadow_runtime_integration_20261108.py',
             'test_rating_fanout_isolation_20261108.py', 'test_c5_feedback_shadow_store_candidate.py',
             'test_c5_feedback_ledger_candidate.py', 'test_c5_feedback_ledger_integrity.py',
             'feedback_bootstrap_disposable_cases_20261111.py', 'test_inputs.py')
    world_tests = ['tests/test_online_world_20261108.py', 'tests/test_online_world_safety_20261109.py',
                   'tests/test_continuous_predictor_20261108.py', 'tests/test_checkpoint_guards_1648.py',
                   'tests/test_observe_atomic_1648.py', 'tests/integrated_online_world_disposable_cases.py',
                   'tests/integrated_jepa_disposable_cases.py', 'tests/predictor_stream_guard_disposable_cases.py',
                   'tests/predictor_history_guard_disposable_cases.py']
    memory_tests = ['tests/source_lifecycle_disposable_cases.py', 'tests/memory_world_disposable_cases_20261111.py',
                    'tests/test_archive.py', 'tests/test_vision.py', 'tests/test_context_os.py',
                    'tests/test_episodes.py', 'tests/test_semantic_memory.py']
    feedback_tests = ['tests/test_dataset_probe_candidate_20261109.py', 'tests/test_local_error_route_shadow_candidate_20261109.py',
                      'tests/test_world_semantic_evidence_candidate_20261109.py',
                      'tests/test_feedback_shadow_runtime_integration_20261108.py',
                      'tests/test_rating_fanout_isolation_20261108.py', 'tests/test_c5_feedback_shadow_store_candidate.py',
                      'tests/test_c5_feedback_ledger_candidate.py', 'tests/test_c5_feedback_ledger_integrity.py',
                      'tests/feedback_bootstrap_disposable_cases_20261111.py', 'tests/test_inputs.py']
    return names, world_tests, memory_tests, feedback_tests


def test_feedback_catalog_memory_and_learning_in_one_disposable_copy(tmp_path):
    module = builder()
    shutil.copytree(CODE / 'v13', tmp_path / 'v13', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(CODE / 'specs', tmp_path / 'specs')
    (tmp_path / 'tests').mkdir()
    names, world_tests, memory_tests, feedback_tests = regression_selection()
    for name in names:
        shutil.copy(CODE / 'tests' / name, tmp_path / 'tests' / name)
    sources = module.build_sources(CODE)
    for name, data in sources.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    shim = runpy.run_path(str(CODE / 'tests/test_integrated_predictor_history_guard_20261110.py'))['SYNTHETIC_ONLY_SHIM']
    (tmp_path / 'tests/conftest.py').write_text(shim)
    body_tests = sorted(name for name in sources if name.startswith('tests/test_body_'))
    command = [sys.executable, '-m', 'pytest', '-q', *world_tests, *body_tests, *memory_tests, *feedback_tests,
               'tests/test_body_jepa_checkpoint_fit.py', 'tests/body_anchor_guard_disposable_cases_20261110.py',
               'tests/test_lora_resume_safety.py', 'tests/test_lora_trainer.py',
               'tests/c3_resume_disposable_cases_20261110.py']
    result = subprocess.run(command, cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(tmp_path)),
                            capture_output=True, text=True, timeout=240)
    assert result.returncode == 0, result.stdout + result.stderr
    print('combined feedback/catalog/memory/C3/Body/World copy:',
          next(line for line in reversed(result.stdout.splitlines()) if 'passed' in line))
