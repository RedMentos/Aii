"""Exercise arithmetic in the ordinary pinned stage, without changing originals."""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys


CODE = Path(__file__).resolve().parents[1]


def test_actual_staged_arithmetic_and_existing_broker_contracts(tmp_path):
    frozen = ('runtime.py', 'store.py', 'operator.py', 'broker.py', 'contracts.py', 'focal.py', 'world.py')
    before = {name: hashlib.sha256((CODE / 'v13' / name).read_bytes()).hexdigest() for name in frozen}
    spec = importlib.util.spec_from_file_location('arithmetic_stage', CODE / 'scripts/stage_integrated_candidate.py')
    stager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stager)
    destination = tmp_path / 'stage'
    manifest = stager.stage(CODE, destination)
    assert manifest['status'] == 'SHADOW_REVIEW_ONLY'
    assert {'v13/runtime.py', 'v13/broker.py', 'v13/contracts.py', 'v13/focal.py'} <= set(manifest['replaced_files'])
    names = ('arithmetic_disposable_cases_20261116.py', 'arithmetic_outcome_disposable_cases_20261116.py',
             'test_arithmetic_reflex.py', 'test_broker.py', 'test_output_policy.py')
    (destination / 'tests').mkdir(exist_ok=True)
    for name in names:
        shutil.copyfile(CODE / 'tests' / name, destination / 'tests' / name)
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', *(('tests/' + name) for name in names)],
        cwd=destination, env=dict(os.environ, PYTHONPATH=str(destination), PYTHONDONTWRITEBYTECODE='1'),
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    print('staged arithmetic + existing broker/output-policy:', result.stdout.strip())
    for name, expected in before.items():
        assert hashlib.sha256((CODE / 'v13' / name).read_bytes()).hexdigest() == expected
