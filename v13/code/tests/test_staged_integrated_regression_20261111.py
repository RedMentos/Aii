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
             'runtime_jepa_utility_disposable_cases_20261111.py')
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
                            capture_output=True, text=True, timeout=240)
    assert result.returncode == 0, result.stdout + result.stderr
    for line in result.stdout.splitlines():
        if 'JEPA_HOLDOUT' in line:
            print(line)
    print('single staged integrated regression:',
          next(line for line in reversed(result.stdout.splitlines()) if 'passed' in line))
