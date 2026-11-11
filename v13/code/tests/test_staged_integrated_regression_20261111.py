"""Run existing organ regressions and new recall/holdout cases on one real stage."""
import importlib.util
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_single_staged_tree_runs_selected_integrated_regressions(tmp_path):
    stager = load('regression_stage', CODE / 'scripts/stage_integrated_candidate.py')
    previous = load('previous_regression_selection', CODE / 'tests/test_integrated_feedback_bootstrap_candidate_20261111.py')
    names, world_tests, memory_tests, feedback_tests = previous.regression_selection()
    dest = tmp_path / 'candidate'
    manifest = stager.stage(CODE, dest)
    (dest / 'tests').mkdir(exist_ok=True)
    extra = ('context_source_recall_disposable_cases_20261111.py',
             'runtime_jepa_utility_disposable_cases_20261111.py',
             'world_jepa_training_resume_disposable_cases_20261111.py',
             'body_role_runtime_disposable_cases_20261111.py',
             'test_world_jepa.py', 'test_world_jepa_atomic_fit.py',
             'test_world_jepa_shadow_checkpoint_20261028.py', 'test_world_jepa_incremental_20261108.py',
             'test_world_jepa_fit_input_guard.py', 'test_world_jepa_reader_snapshot.py',
             'test_world_jepa_stale_fit_order.py', 'test_world_jepa_online_experiment_20261108.py')
    extra += ('test_weight_approval_atomic.py', 'test_ag6_second_tx_source_recheck_20261029.py',
              'test_ag6_approval_source_revocation_20261029.py', 'test_ag6_holdout_revalidate_run14r.py',
              'test_ag6_gate_request_atomic_20261029.py', 'test_ag6_reject_request_atomic_20261029.py',
              'test_ag6_staged_source_revocation_20261029.py', 'test_ag6_rated_answer_dependencies_20261029.py',
              'test_sparse_trainer_runtime_binding.py')
    for name in (*names, *extra):
        shutil.copy(CODE / 'tests' / name, dest / 'tests' / name)
    shim = runpy.run_path(str(CODE / 'tests/test_integrated_predictor_history_guard_20261110.py'))['SYNTHETIC_ONLY_SHIM']
    (dest / 'tests/conftest.py').write_text(shim)
    body_tests = sorted(name for name in manifest['replaced_files'] if name.startswith('tests/test_body_'))
    command = [sys.executable, '-m', 'pytest', '-q', '-s', *world_tests, *body_tests, *memory_tests, *feedback_tests,
               'tests/test_body_jepa_checkpoint_fit.py', 'tests/body_anchor_guard_disposable_cases_20261110.py',
               'tests/test_lora_resume_safety.py', 'tests/test_lora_trainer.py', 'tests/c3_resume_disposable_cases_20261110.py',
               *(('tests/' + name) for name in extra)]
    result = subprocess.run(command, cwd=dest,
                            env=dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1'),
                            capture_output=True, text=True, timeout=360)
    assert result.returncode == 0, result.stdout + result.stderr
    for line in result.stdout.splitlines():
        if 'JEPA_HOLDOUT' in line:
            print(line)
    print('single staged integrated regression:',
          next(line for line in reversed(result.stdout.splitlines()) if 'passed' in line))
