"""Run real source-bound JEPA update/holdout/restart in disposable integrated copy."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]

def test_integrated_runtime_jepa_holdout_restart(tmp_path):
    builder_path = CODE / 'scripts/stage_integrated_candidate.py'
    spec = importlib.util.spec_from_file_location('world_integration', builder_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stage = tmp_path / 'candidate'
    manifest = module.stage(CODE, stage)
    assert manifest['status'] == 'SHADOW_REVIEW_ONLY'
    (stage / 'tests').mkdir(exist_ok=True)
    for name in ('integrated_jepa_disposable_cases.py','integrated_online_world_disposable_cases.py'):
        shutil.copy(CODE / 'tests' / name, stage / 'tests' / name)
    shutil.copy(CODE / 'tests/runtime_jepa_utility_disposable_cases_20261111.py',
                stage / 'tests/runtime_jepa_utility_disposable_cases_20261111.py')
    env = dict(os.environ, PYTHONPATH=str(stage) + os.pathsep + str(stage / 'tests'))
    command = [sys.executable, '-m', 'pytest', '-q', '-s',
               'tests/runtime_jepa_utility_disposable_cases_20261111.py']
    result = subprocess.run(command, cwd=stage, env=env,
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'JEPA_HOLDOUT' in result.stdout
    print(result.stdout)
