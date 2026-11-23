"""Exact-head integration of #1631 and #1648 in an isolated Runtime copy."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

CODE = Path(__file__).resolve().parents[1]


def builder():
    spec = importlib.util.spec_from_file_location('integrated_world_candidate', CODE / 'scripts/integrated_online_world_candidate_20261110.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_input_and_asset_pins_reject_unreviewed_sources(tmp_path):
    module = builder()
    result = module.build_sources(CODE)
    assert b'world_jepa_update' in result['v13/runtime.py']
    assert b'world_jepa_restore' in result['v13/runtime.py']
    assert b'should_continue=check,authority=authority' in result['v13/runtime.py']
    for name in module.FILES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((CODE / name).read_bytes())
    (tmp_path / 'v13/runtime.py').write_bytes(b'unreviewed')
    with pytest.raises(ValueError, match='runtime.py'):
        module.build_sources(tmp_path)


def test_operator_runtime_and_reviewed_guards_compose_in_disposable_copy(tmp_path):
    module = builder()
    shutil.copytree(CODE / 'v13', tmp_path / 'v13', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(CODE / 'specs', tmp_path / 'specs')
    (tmp_path / 'tests').mkdir()
    for name in ('test_continuous_predictor_20261108.py', 'test_runtime_jepa_integration_20261110.py',
                 'integrated_online_world_disposable_cases.py'):
        shutil.copy(CODE / 'tests' / name, tmp_path / 'tests' / name)
    for name, data in module.build_sources(CODE).items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    env = dict(os.environ, PYTHONPATH=str(tmp_path))
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q',
        'tests/test_online_world_20261108.py', 'tests/test_online_world_safety_20261109.py',
        'tests/test_continuous_predictor_20261108.py', 'tests/test_checkpoint_guards_1648.py',
        'tests/test_observe_atomic_1648.py', 'tests/test_known_revocation_window.py',
        'tests/test_runtime_jepa_integration_20261110.py',
        'tests/integrated_online_world_disposable_cases.py'],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    print('materialized integration:', next(line for line in reversed(result.stdout.splitlines()) if 'passed' in line))
