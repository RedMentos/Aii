"""Compare the original predictor counterexample with a pinned integration copy."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

CODE = Path(__file__).resolve().parents[1]


def builder(filename):
    spec = importlib.util.spec_from_file_location('reviewed_builder', CODE / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def materialize(path, module, test_files):
    shutil.copytree(CODE / 'v13', path / 'v13', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(CODE / 'specs', path / 'specs')
    (path / 'tests').mkdir()
    for name in test_files:
        shutil.copy(CODE / 'tests' / name, path / 'tests' / name)
    for name, data in module.build_sources(CODE).items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def run(path, tests):
    env = dict(os.environ, PYTHONPATH=str(path))
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', *tests], cwd=path,
                            env=env, capture_output=True, text=True, timeout=150)
    assert result.returncode == 0, result.stdout + result.stderr
    print(next(line for line in reversed(result.stdout.splitlines()) if 'passed' in line))


def test_rejects_wrong_jepa_builder_hash(monkeypatch):
    module = builder('integrated_predictor_stream_guard_20261110.py')
    monkeypatch.setattr(module, 'JEPA_BUILDER_SHA', '0' * 64)
    with pytest.raises(ValueError, match='builder source changed'):
        module.build_sources(CODE)


def test_original_bug_is_reproduced(tmp_path):
    module = builder('integrated_jepa_guard_candidate_20261110.py')
    materialize(tmp_path, module, ('integrated_online_world_disposable_cases.py',
                                   'predictor_stream_original_counterexample.py'))
    run(tmp_path, ['tests/predictor_stream_original_counterexample.py'])


def test_fixed_stream_composes_with_both_world_paths(tmp_path):
    module = builder('integrated_predictor_stream_guard_20261110.py')
    materialize(tmp_path, module, ('test_continuous_predictor_20261108.py',
        'integrated_online_world_disposable_cases.py', 'integrated_jepa_disposable_cases.py',
        'predictor_stream_guard_disposable_cases.py'))
    run(tmp_path, ['tests/test_online_world_20261108.py', 'tests/test_online_world_safety_20261109.py',
        'tests/test_continuous_predictor_20261108.py', 'tests/test_checkpoint_guards_1648.py',
        'tests/test_observe_atomic_1648.py', 'tests/test_known_revocation_window.py',
        'tests/integrated_online_world_disposable_cases.py', 'tests/integrated_jepa_disposable_cases.py',
        'tests/predictor_stream_guard_disposable_cases.py'])
