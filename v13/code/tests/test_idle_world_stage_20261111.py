"""Actual bounded idle jobs and the preserved legacy counterexample."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def staged(tmp_path, original=False):
    spec = importlib.util.spec_from_file_location('idle_stage', CODE/'scripts/stage_integrated_candidate.py')
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if original:
        module.BUILDER = 'scripts/integrated_c3_consent_candidate_20261111.py'
        module.BUILDER_SHA = 'cc581a85f131417af184f38b86f732ce4bafc4e49a51bd55c89afad78f21ff4a'
    dest = tmp_path/'candidate'
    module.stage(CODE, dest)
    for name in ('integrated_jepa_disposable_cases.py', 'idle_world_disposable_cases_20261111.py',
                 'legacy_learning_disposable_cases_20261111.py', 'legacy_learning_record_repro_cases_20261111.py',
                 'test_authority.py', 'test_authority_live.py', 'test_sleep_scheduler.py',
                 'test_scheduler_dispatch_clock_20261030.py', 'test_scheduler_finite_boundary_20261029.py'):
        shutil.copyfile(CODE/'tests'/name, dest/'tests'/name)
    return dest


def run(dest, *tests):
    log = dest.parent/'idle-subprocess.log'
    with log.open('w') as output:
        try:
            result = subprocess.run([sys.executable, '-m', 'pytest', '-v', '-s', *tests], cwd=dest,
                                    env=dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1',
                                             OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1'),
                                    stdout=output, stderr=subprocess.STDOUT, text=True, timeout=300)
        finally:
            print(log.read_text())
    assert result.returncode == 0, log.read_text()


def test_original_stage_reproduces_record_only_numeric_mutation(tmp_path):
    run(staged(tmp_path, original=True),
        'tests/legacy_learning_record_repro_cases_20261111.py')


def test_idle_and_legacy_safety_in_current_composition(tmp_path):
    run(staged(tmp_path), 'tests/idle_world_disposable_cases_20261111.py',
        'tests/legacy_learning_disposable_cases_20261111.py', 'tests/test_authority.py',
        'tests/test_authority_live.py', 'tests/test_sleep_scheduler.py',
        'tests/test_scheduler_dispatch_clock_20261030.py', 'tests/test_scheduler_finite_boundary_20261029.py')
