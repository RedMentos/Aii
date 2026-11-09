"""Hash-bound candidate checks; the frozen runtime is never overwritten."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

from scripts.online_world_integration_candidate import DEPENDENCIES,FILES,build_sources


CODE=Path(__file__).resolve().parents[1]


def test_candidate_rejects_changed_source_and_existing_target(tmp_path):
    for name in (*FILES,*DEPENDENCIES):
        dest=tmp_path/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(CODE/name,dest)
    runtime=tmp_path/'v13/runtime.py'
    runtime.write_bytes(runtime.read_bytes()+b'\n# changed source\n')
    with pytest.raises(ValueError,match='hash mismatch'):build_sources(tmp_path)
    shutil.copy2(CODE/'v13/runtime.py',runtime)
    helper=tmp_path/'v13/world_model.py'
    helper.write_bytes(helper.read_bytes()+b'\n# changed dependency\n')
    with pytest.raises(ValueError,match='hash mismatch'):build_sources(tmp_path)
    shutil.copy2(CODE/'v13/world_model.py',helper)
    (tmp_path/'v13/online_world_policy.py').write_text('existing unrelated work')
    with pytest.raises(ValueError,match='already exists'):build_sources(tmp_path)


def test_candidate_suite_against_real_runtime_in_isolated_copy():
    overlay=build_sources(CODE)
    with tempfile.TemporaryDirectory(prefix='v13-online-world-test-') as home:
        target=Path(home)
        shutil.copytree(CODE/'v13',target/'v13',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copytree(CODE/'specs',target/'specs')
        (target/'tests').mkdir()
        shutil.copy2(CODE/'tests/test_continuous_predictor_20261108.py',target/'tests')
        for name,data in overlay.items():
            dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        env=dict(os.environ,PYTHONPATH=str(target))
        command=[sys.executable,'-m','pytest','-q','tests/test_online_world_20261108.py',
                 'tests/test_continuous_predictor_20261108.py','tests/test_online_world_safety_20261109.py']
        run=subprocess.run(command,cwd=target,env=env,capture_output=True,text=True,timeout=120)
        assert run.returncode==0,run.stdout+'\n'+run.stderr
        assert '30 passed' in run.stdout,run.stdout
