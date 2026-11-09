"""Exercise source-lifecycle changes only in a materialized, pinned copy."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

CODE = Path(__file__).resolve().parents[1]


def materializer():
    spec = importlib.util.spec_from_file_location('reviewed_lifecycle_materializer', CODE / 'scripts/source_lifecycle_lock_integration_candidate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('changed', ['vision.py', 'source_lifecycle_candidate.py'])
def test_all_original_sources_are_bound_and_modified_sources_refused(tmp_path, changed):
    module = materializer()
    patched = module.build_sources(CODE / 'v13')
    assert set(patched) == {'archive.py', 'store.py', 'memory.py', 'vision.py',
                            'archive_reader_guard_candidate.py', 'archive_stream_range_candidate.py',
                            'source_lifecycle_candidate.py'}
    for name in module.PINS:
        shutil.copy(CODE / 'v13' / name, tmp_path / name)
    (tmp_path / changed).write_bytes(b'unreviewed')
    with pytest.raises(ValueError, match=changed):
        module.build_sources(tmp_path)


def test_disposable_composed_runtime_and_existing_archive_vision_tests(tmp_path):
    module = materializer()
    shutil.copytree(CODE / 'v13', tmp_path / 'v13', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(CODE / 'specs', tmp_path / 'specs')
    for name, value in module.build_sources(CODE / 'v13').items():
        (tmp_path / 'v13' / name).write_bytes(value)
    for name in ('test_archive.py', 'test_vision.py', 'test_context_os.py', 'test_episodes.py',
                 'test_semantic_memory.py', 'source_lifecycle_disposable_cases.py'):
        shutil.copy(CODE / 'tests' / name, tmp_path / name)
    env = dict(os.environ, PYTHONPATH=str(tmp_path))
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'source_lifecycle_disposable_cases.py',
                             'test_archive.py', 'test_vision.py', 'test_context_os.py',
                             'test_episodes.py', 'test_semantic_memory.py'],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'passed' in result.stdout
    print('materialized suite:', next(line for line in reversed(result.stdout.splitlines()) if 'passed' in line))
