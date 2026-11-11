"""Exercise optimizer-bound World-JEPA through the single current stager."""
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
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-s',
                             'tests/world_jepa_training_resume_disposable_cases_20261111.py'],
                            cwd=dest, capture_output=True, text=True, timeout=120,
                            env=dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1'))
    assert result.returncode == 0, result.stdout + result.stderr
    print(result.stdout)
