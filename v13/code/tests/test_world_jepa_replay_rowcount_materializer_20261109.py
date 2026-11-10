"""The bounded #1652 row-count patch is tested in an isolated source copy."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

CODE = Path(__file__).resolve().parents[1]


def materializer():
    spec = importlib.util.spec_from_file_location('replay_rowcount_materializer', CODE / 'scripts/world_jepa_replay_rowcount_candidate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_and_original_fixture_pins_are_checked(tmp_path):
    module = materializer()
    patched = module.build_sources(CODE)
    assert b'len(n[0]) + len(r[0])' in patched['v13/world_jepa_replay.py']
    assert b'((n + 1) // 2, 1)' in patched['tests/test_world_jepa_replay_20261109.py']
    for name in module.PINS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((CODE / name).read_bytes())
    (tmp_path / 'v13/world_jepa_replay.py').write_bytes(b'changed')
    with pytest.raises(ValueError, match='unsupported'):
        module.build_sources(tmp_path)


def test_real_fixture_and_incremental_tests_run_in_isolated_copy(tmp_path):
    module = materializer()
    shutil.copytree(CODE / 'v13', tmp_path / 'v13', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (tmp_path / 'tests').mkdir()
    for name, value in module.build_sources(CODE).items():
        (tmp_path / name).write_bytes(value)
    shutil.copy(CODE / 'tests/test_world_jepa_incremental_20261108.py', tmp_path / 'tests')
    # The counting-only patch deliberately does not claim fail-atomic updates.
    (tmp_path / 'tests/test_postcheck_still_mutates.py').write_text('''\
import numpy as np
import pytest
from v13.world_jepa_replay import replay_update

def rows(n, offset):
    x=np.arange(n*2,dtype=float).reshape(n,2)+offset
    a=np.tile([[1.,0.],[0.,1.]],((n+1)//2,1))[:n]
    return x,a,x+a

class Model:
    def __init__(self): self.value=0
    def prediction_loss(self,*args): return float('nan') if self.value else 1.
    def partial_fit(self,*args,**kwargs): self.value=7

def test_row_count_only_patch_retains_postcheck_mutation():
    m=Model()
    with pytest.raises(ValueError,match='post-update'):
        replay_update(m,rows(12,0),rows(12,100),rows(8,200),rows(8,300),steps=1)
    assert m.value == 7
''')
    env = dict(os.environ, PYTHONPATH=str(tmp_path))
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests'], cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '9 passed' in result.stdout
