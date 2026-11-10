"""Reproduce old-window revocation and test the layered SQLite history fence."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

CODE = Path(__file__).resolve().parents[1]
SYNTHETIC_ONLY_SHIM = '''\
"""Retain legacy fabricated-row checks without pretending they test history."""
import pytest
from v13 import online_world_history_guard_candidate as history
from v13.store import Store

@pytest.fixture(autouse=True)
def synthetic_history_seam(request, monkeypatch):
    real = history.guarded
    def guarded(world, operation):
        if type(world.runtime.store) is not Store or 'synthetic_sources' in request.fixturenames:
            return operation()
        return real(world, operation)
    monkeypatch.setattr(history, 'guarded', guarded)
'''


def builder(filename):
    spec = importlib.util.spec_from_file_location('reviewed_history_builder', CODE / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def materialize(path, module, tests):
    shutil.copytree(CODE / 'v13', path / 'v13', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(CODE / 'specs', path / 'specs')
    (path / 'tests').mkdir()
    for name in tests:
        shutil.copy(CODE / 'tests' / name, path / 'tests' / name)
    for name, data in module.build_sources(CODE).items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def run(path, files):
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', *files], cwd=path,
                            env=dict(os.environ, PYTHONPATH=str(path)), capture_output=True,
                            text=True, timeout=150)
    assert result.returncode == 0, result.stdout + result.stderr
    print(next(line for line in reversed(result.stdout.splitlines()) if 'passed' in line))


def test_source_pins_reject_unreviewed_guard_and_builder(monkeypatch):
    module = builder('integrated_predictor_history_guard_20261110.py')
    with monkeypatch.context() as patch:
        patch.setattr(module, 'HISTORY_GUARD_SHA', '0' * 64)
        with pytest.raises(ValueError, match='history guard source changed'):
            module.build_sources(CODE)
    monkeypatch.setattr(module, 'STREAM_BUILDER_SHA', '0' * 64)
    with pytest.raises(ValueError, match='stream builder source changed'):
        module.build_sources(CODE)


def test_previous_copy_reproduces_old_revocation_gap(tmp_path):
    module = builder('integrated_predictor_stream_guard_20261110.py')
    materialize(tmp_path, module, ())
    run(tmp_path, ['tests/test_known_revocation_window.py'])


def test_history_fence_composes_with_world_and_jepa_runtime(tmp_path):
    module = builder('integrated_predictor_history_guard_20261110.py')
    materialize(tmp_path, module, ('test_continuous_predictor_20261108.py',
        'integrated_online_world_disposable_cases.py', 'integrated_jepa_disposable_cases.py',
        'predictor_stream_guard_disposable_cases.py', 'predictor_history_guard_disposable_cases.py'))
    # Retain older fabricated-row fixtures with a test-only seam. Actual
    # source-history and SQLite-fence tests always use the real guard.
    (tmp_path / 'tests/conftest.py').write_text(SYNTHETIC_ONLY_SHIM)
    run(tmp_path, ['tests/test_online_world_20261108.py', 'tests/test_online_world_safety_20261109.py',
        'tests/test_continuous_predictor_20261108.py', 'tests/test_checkpoint_guards_1648.py',
        'tests/test_observe_atomic_1648.py', 'tests/integrated_online_world_disposable_cases.py',
        'tests/integrated_jepa_disposable_cases.py', 'tests/predictor_stream_guard_disposable_cases.py',
        'tests/predictor_history_guard_disposable_cases.py'])
