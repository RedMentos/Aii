"""Authorized tiny C3/Body and numeric World learning after real compaction."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_actual_training_uses_compacted_source_in_shared_stage(tmp_path):
    spec = importlib.util.spec_from_file_location('compaction_training_stage', CODE/'scripts/stage_integrated_candidate.py')
    stager = importlib.util.module_from_spec(spec);spec.loader.exec_module(stager)
    dest = tmp_path/'candidate';stager.stage(CODE, dest)
    for name in ('user_compaction_training_disposable_cases_20261111.py',
                 'user_message_compaction_disposable_cases_20261111.py',
                 'body_role_runtime_disposable_cases_20261111.py',
                 'c3_resume_disposable_cases_20261110.py', 'test_body_jepa_checkpoint_fit.py',
                 'integrated_jepa_disposable_cases.py'):
        shutil.copyfile(CODE/'tests'/name, dest/'tests'/name)
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-s',
                             'tests/user_compaction_training_disposable_cases_20261111.py'], cwd=dest,
                            env=dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1'),
                            capture_output=True, text=True, timeout=180)
    print(result.stdout+result.stderr)
    assert result.returncode == 0, result.stdout+result.stderr
