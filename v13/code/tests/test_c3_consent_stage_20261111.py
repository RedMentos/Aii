"""Actual direct/SDFT C3 consent flow in the shared current stage."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE=Path(__file__).resolve().parents[1]


def test_c3_consent_in_current_stage(tmp_path):
    spec=importlib.util.spec_from_file_location('c3_consent_stage',CODE/'scripts/stage_integrated_candidate.py')
    stager=importlib.util.module_from_spec(spec);spec.loader.exec_module(stager)
    dest=tmp_path/'candidate';stager.stage(CODE,dest)
    for name in ('c3_consent_disposable_cases_20261111.py','c3_resume_disposable_cases_20261110.py','test_body_jepa_checkpoint_fit.py'):
        shutil.copyfile(CODE/'tests'/name,dest/'tests'/name)
    result=subprocess.run([sys.executable,'-m','pytest','-q','-s','tests/c3_consent_disposable_cases_20261111.py'],cwd=dest,
                          env=dict(os.environ,PYTHONPATH=str(dest),PYTHONDONTWRITEBYTECODE='1'),
                          capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+result.stderr
    print(result.stdout)
