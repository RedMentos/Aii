"""Compose real Body-JEPA tiny-fit tests and World Runtime tests in one copy."""
import importlib.util
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import pytest

CODE = Path(__file__).resolve().parents[1]


def builder():
    spec = importlib.util.spec_from_file_location('integrated_body_world', CODE / 'scripts/integrated_body_world_candidate_20261110.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_rejects_unreviewed_world_and_body(monkeypatch):
    module = builder()
    with monkeypatch.context() as patch:
        patch.setattr(module, 'WORLD_BUILDER_SHA', '0' * 64)
        with pytest.raises(ValueError, match='world builder source changed'):
            module.build_sources(CODE)
    monkeypatch.setattr(module, 'BODY_BUILDER_SHA', '0' * 64)
    with pytest.raises(ValueError, match='body builder source changed'):
        module.build_sources(CODE)


def test_real_world_and_body_paths_in_same_disposable_copy(tmp_path):
    module = builder()
    shutil.copytree(CODE / 'v13', tmp_path / 'v13', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(CODE / 'specs', tmp_path / 'specs')
    (tmp_path / 'tests').mkdir()
    names = ('test_continuous_predictor_20261108.py', 'integrated_online_world_disposable_cases.py',
             'integrated_jepa_disposable_cases.py', 'predictor_stream_guard_disposable_cases.py',
             'predictor_history_guard_disposable_cases.py', 'body_anchor_guard_disposable_cases_20261110.py',
             'test_body_jepa_checkpoint_fit.py')
    for name in names:
        shutil.copy(CODE / 'tests' / name, tmp_path / 'tests' / name)
    sources = module.build_sources(CODE)
    for name, data in sources.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    shim = runpy.run_path(str(CODE / 'tests/test_integrated_predictor_history_guard_20261110.py'))['SYNTHETIC_ONLY_SHIM']
    (tmp_path / 'tests/conftest.py').write_text(shim)
    body_tests = sorted(name for name in sources if name.startswith('tests/test_body_'))
    world_tests = ['tests/test_online_world_20261108.py', 'tests/test_online_world_safety_20261109.py',
                   'tests/test_continuous_predictor_20261108.py', 'tests/test_checkpoint_guards_1648.py',
                   'tests/test_observe_atomic_1648.py', 'tests/integrated_online_world_disposable_cases.py',
                   'tests/integrated_jepa_disposable_cases.py', 'tests/predictor_stream_guard_disposable_cases.py',
                   'tests/predictor_history_guard_disposable_cases.py']
    command = [sys.executable, '-m', 'pytest', '-q', *world_tests, *body_tests,
               'tests/test_body_jepa_checkpoint_fit.py', 'tests/body_anchor_guard_disposable_cases_20261110.py']
    result = subprocess.run(command, cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(tmp_path)),
                            capture_output=True, text=True, timeout=240)
    assert result.returncode == 0, result.stdout + result.stderr
    print('combined integrated copy:', next(line for line in reversed(result.stdout.splitlines()) if 'passed' in line))
