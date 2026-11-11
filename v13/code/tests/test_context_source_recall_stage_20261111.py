"""Bounded old-source ContextOS consumption in the actual staged composite."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_context_recall_on_real_staged_runtime(tmp_path):
    path = CODE / 'scripts/stage_integrated_candidate.py'
    spec = importlib.util.spec_from_file_location('context_stage', path)
    stager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stager)
    dest = tmp_path / 'candidate'
    manifest = stager.stage(CODE, dest)
    assert manifest['status'] == 'SHADOW_REVIEW_ONLY'
    (dest / 'tests').mkdir(exist_ok=True)
    name = 'context_source_recall_disposable_cases_20261111.py'
    shutil.copy(CODE / 'tests' / name, dest / 'tests' / name)
    env = dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests/' + name],
                            cwd=dest, env=env, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    print('staged ContextOS source recall:', next(line for line in reversed(result.stdout.splitlines()) if 'passed' in line))
