"""Review-only composition against the exact newer Runtime Git object."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

CODE = Path(__file__).resolve().parents[1]
ROOT = CODE.parents[1]
SCRIPT = CODE / 'scripts/world_jepa_replay_runtime_compat_20261110.py'
COMMIT = '9c38cc3d54d3345c5a4375f651467d00b7db683c'


def has_commit():
    return subprocess.run(['git', '-C', str(ROOT), 'cat-file', '-e', COMMIT + '^{commit}'],
                          capture_output=True).returncode == 0


def test_exact_runtime_method_and_detached_preview_compose_without_publication():
    if not has_commit():
        pytest.skip('reviewed #1661 Git object not locally fetched')
    result = subprocess.run([sys.executable, str(SCRIPT), '--integration-checkout', str(ROOT)],
                            env=dict(os.environ, PYTHONPATH=str(CODE)), capture_output=True,
                            text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['integration_commit'] == COMMIT
    assert receipt['feed'] == 'MOCK_TRANSITIONS_NOT_REAL_STORE'
    assert receipt['actual_runtime_method_invoked'] is True
    assert receipt['runtime_model_unchanged_by_preview'] is True
    assert receipt['source_digest_unchanged_by_preview'] is True
    assert receipt['proposal_weight_changed'] is True
    assert receipt['injected_invalid_history_deepcopy_mutated_runtime_on_failure'] is True
    assert receipt['preview']['source_id_disjointness_verified'] is False


def test_composition_rejects_unreviewed_candidate_bytes(monkeypatch):
    if not has_commit():
        pytest.skip('reviewed #1661 Git object not locally fetched')
    spec = importlib.util.spec_from_file_location('replay_runtime_compat', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setitem(module.LOCAL_PINS, 'world_jepa_replay_shadow_candidate.py', '0' * 64)
    monkeypatch.setattr(sys, 'argv', [str(SCRIPT), '--integration-checkout', str(ROOT)])
    with pytest.raises(ValueError, match='candidate changed'):
        module.main()
