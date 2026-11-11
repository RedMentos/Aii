"""Replay on/off retention ablation on the real integrated T8/JEPA source copy."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_integrated_runtime_jepa_replay_ablation(tmp_path):
    builder = CODE / 'scripts/integrated_predictor_history_guard_20261110.py'
    spec = importlib.util.spec_from_file_location('world_integration', builder)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    shutil.copytree(CODE / 'v13', tmp_path / 'v13',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(CODE / 'specs', tmp_path / 'specs')
    (tmp_path / 'tests').mkdir()
    for name in ('integrated_jepa_disposable_cases.py',
                 'integrated_online_world_disposable_cases.py',
                 'runtime_jepa_replay_ablation_disposable_cases_20261111.py'):
        shutil.copy(CODE / 'tests' / name, tmp_path / 'tests' / name)
    for name, data in module.build_sources(CODE).items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    env = dict(os.environ, PYTHONPATH=str(tmp_path) + os.pathsep + str(tmp_path / 'tests'),
               PYTHONDONTWRITEBYTECODE='1')
    command = [sys.executable, '-m', 'pytest', '-q', '-s',
               'tests/runtime_jepa_replay_ablation_disposable_cases_20261111.py']
    result = subprocess.run(command, cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'JEPA_REPLAY_RETENTION' in result.stdout
    print(result.stdout)
