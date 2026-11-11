"""Run the actual Body/AG6 route on the single pinned staged Runtime."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_body_role_training_in_current_real_stage(tmp_path):
    spec = importlib.util.spec_from_file_location('body_stage', CODE / 'scripts/stage_integrated_candidate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    dest = tmp_path / 'candidate'
    module.stage(CODE, dest)
    for name in ('body_role_runtime_disposable_cases_20261111.py', 'test_body_jepa_checkpoint_fit.py'):
        shutil.copyfile(CODE / 'tests' / name, dest / 'tests' / name)
    result = subprocess.run([sys.executable,'-m','pytest','-q','-s','tests/body_role_runtime_disposable_cases_20261111.py'],
                            cwd=dest, capture_output=True, text=True, timeout=180,
                            env=dict(os.environ,PYTHONPATH=str(dest),PYTHONDONTWRITEBYTECODE='1'))
    assert result.returncode == 0, result.stdout + result.stderr
    print(result.stdout)
