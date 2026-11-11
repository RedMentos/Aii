"""Run real source-bound JEPA update/holdout/restart in disposable integrated copy."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]

def test_integrated_runtime_jepa_holdout_restart(tmp_path):
    builder_path = CODE / 'scripts/integrated_predictor_history_guard_20261110.py'
    spec = importlib.util.spec_from_file_location('world_integration', builder_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    shutil.copytree(CODE / 'v13', tmp_path / 'v13', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(CODE / 'specs', tmp_path / 'specs')
    (tmp_path / 'tests').mkdir()
    for name in ('integrated_jepa_disposable_cases.py','integrated_online_world_disposable_cases.py'):
        shutil.copy(CODE / 'tests' / name, tmp_path / 'tests' / name)
    shutil.copy(CODE / 'tests/runtime_jepa_utility_disposable_cases_20261111.py',
                tmp_path / 'tests/runtime_jepa_utility_disposable_cases_20261111.py')
    for name, data in module.build_sources(CODE).items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    env = dict(os.environ, PYTHONPATH=str(tmp_path) + os.pathsep + str(tmp_path / 'tests'))
    command = [sys.executable, '-m', 'pytest', '-q', '-s',
               'tests/runtime_jepa_utility_disposable_cases_20261111.py']
    result = subprocess.run(command, cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'JEPA_HOLDOUT' in result.stdout
    print(result.stdout)
