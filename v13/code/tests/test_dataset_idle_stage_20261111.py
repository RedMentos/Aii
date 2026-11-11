"""Actual local dataset consumer in the pinned shared Runtime composition."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_dataset_record_in_current_stage(tmp_path):
    spec = importlib.util.spec_from_file_location('dataset_stage', CODE/'scripts/stage_integrated_candidate.py')
    stager = importlib.util.module_from_spec(spec);spec.loader.exec_module(stager)
    dest = tmp_path/'candidate';stager.stage(CODE, dest)
    name = 'dataset_idle_import_disposable_cases_20261111.py'
    shutil.copyfile(CODE/'tests'/name, dest/'tests'/name)
    log = tmp_path/'dataset-subprocess.log'
    with log.open('w') as output:
        try:
            result = subprocess.run([sys.executable, '-m', 'pytest', '-v', '-s', 'tests/'+name], cwd=dest,
                                    env=dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1'),
                                    stdout=output, stderr=subprocess.STDOUT, text=True, timeout=180)
        finally:
            print(log.read_text())
    assert result.returncode == 0, log.read_text()
