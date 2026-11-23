"""Review-only integration of JEPA policy, lineage and private restart."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

CODE = Path(__file__).resolve().parents[1]


def builder():
    spec = importlib.util.spec_from_file_location('integrated_jepa_builder', CODE / 'scripts/integrated_jepa_guard_candidate_20261110.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_rejects_changed_guard_bytes(monkeypatch):
    module = builder()
    assert b'world_jepa_runtime_guard_candidate' in module.build_sources(CODE)['v13/runtime.py']
    monkeypatch.setattr(module, 'GUARD_SHA', '0' * 64)
    with pytest.raises(ValueError, match='guard source changed'):
        module.build_sources(CODE)


def test_builder_rejects_changed_checkpoint_bytes(monkeypatch):
    module = builder()
    monkeypatch.setattr(module, 'CHECKPOINT_SHA', '0' * 64)
    with pytest.raises(ValueError, match='checkpoint source changed'):
        module.build_sources(CODE)


def test_real_runtime_world_paths_in_a_disposable_copy(tmp_path):
    module = builder()
    shutil.copytree(CODE / 'v13', tmp_path / 'v13', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(CODE / 'specs', tmp_path / 'specs')
    (tmp_path / 'tests').mkdir()
    for name in ('test_continuous_predictor_20261108.py', 'integrated_online_world_disposable_cases.py',
                 'integrated_jepa_disposable_cases.py'):
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
        'tests/integrated_online_world_disposable_cases.py', 'tests/integrated_jepa_disposable_cases.py'],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    print('layered integration:', next(line for line in reversed(result.stdout.splitlines()) if 'passed' in line))
