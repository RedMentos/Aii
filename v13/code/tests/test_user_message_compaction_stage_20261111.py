"""Exercise real old USER-text compaction on the shared Runtime candidate."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_user_message_compaction_in_shared_stage(tmp_path):
    spec = importlib.util.spec_from_file_location('compaction_stage', CODE/'scripts/stage_integrated_candidate.py')
    stager = importlib.util.module_from_spec(spec);spec.loader.exec_module(stager)
    dest = tmp_path/'candidate';stager.stage(CODE, dest)
    name = 'user_message_compaction_disposable_cases_20261111.py'
    shutil.copyfile(CODE/'tests'/name, dest/'tests'/name)
    log = tmp_path/'compaction-subprocess.log'
    with log.open('w') as output:
        try:
            result = subprocess.run([sys.executable, '-m', 'pytest', '-v', '-s', 'tests/'+name], cwd=dest,
                                    env=dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1'),
                                    stdout=output, stderr=subprocess.STDOUT, text=True, timeout=180)
        finally:
            print(log.read_text())
    assert result.returncode == 0, log.read_text()
