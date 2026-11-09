"""Exercise the capability-profile consumer in an isolated source copy."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

from scripts.body_port_openat_integration_candidate import HASHES,build_sources


CODE=Path(__file__).resolve().parents[1]
PROBE='''
from types import SimpleNamespace
from unittest.mock import patch
import test_body_training_port as fixtures
from v13 import body_port_openat_candidate as candidate
from v13.verification import native_capability_profile

def test_actual_capability_profile_does_not_bind_a_swapped_master(tmp_path):
    home=tmp_path/'home';home.mkdir()
    d=fixtures.BodyTrainingPortContract().make(home)
    master=home/d['master_artifact'];outside=tmp_path/'outside';outside.write_bytes(master.read_bytes())
    original=candidate._stream
    def swap(fd,relative,limit=None):
        if relative==d['master_artifact']:
            master.unlink();master.symlink_to(outside)
        return original(fd,relative,limit)
    with patch.object(candidate,'_stream',side_effect=swap):
        profile=native_capability_profile(SimpleNamespace(home=home))
    body=profile['body_training'];port=body['ports']['B1_DETAIL']
    assert body['status']=='UNAVAILABLE' and body['authority']=='NONE'
    assert port['reason']=='ARTIFACT_CHANGED_DURING_INSPECTION' and port['update_authority']==0
'''


def test_builder_rejects_changed_source(tmp_path):
    for name in HASHES:shutil.copy2(CODE/'v13'/name,tmp_path/name)
    path=tmp_path/'verification.py';path.write_bytes(path.read_bytes()+b'\n# changed source\n')
    with pytest.raises(ValueError,match='unsupported'):build_sources(tmp_path)


def test_isolated_capability_profile_uses_candidate():
    overlay=build_sources(CODE/'v13')
    with tempfile.TemporaryDirectory(prefix='v13-body-openat-copy-') as home:
        target=Path(home)
        shutil.copytree(CODE/'v13',target/'v13',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copytree(CODE/'specs',target/'specs')
        (target/'tests').mkdir()
        for name in ('test_body_training_port.py','test_body_port_openat_candidate_20261109.py'):
            shutil.copy2(CODE/'tests'/name,target/'tests'/name)
        for name,data in overlay.items():(target/'v13'/name).write_bytes(data)
        (target/'tests/test_actual_profile_probe.py').write_text(PROBE)
        env=dict(os.environ,PYTHONPATH=str(target)+os.pathsep+str(target/'tests'))
        command=[sys.executable,'-m','pytest','-q','tests/test_body_training_port.py',
                 'tests/test_body_port_openat_candidate_20261109.py','tests/test_actual_profile_probe.py']
        run=subprocess.run(command,cwd=target,env=env,capture_output=True,text=True,timeout=120)
        assert run.returncode==0,run.stdout+'\n'+run.stderr
        assert '22 passed' in run.stdout,run.stdout
