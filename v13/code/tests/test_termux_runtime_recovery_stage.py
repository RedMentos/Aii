"""Real composed stage, coordinator and SQLite; no downloaded/native models."""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_recovery_composes_with_existing_learning_and_preserves_frozen_sources(tmp_path):
    frozen = ('runtime.py', 'store.py', 'operator.py', 'scheduler.py', 'ui.py', 'verification.py')
    before = {name: hashlib.sha256((CODE / 'v13' / name).read_bytes()).hexdigest()
              for name in frozen}
    spec = importlib.util.spec_from_file_location('recovery_stage', CODE / 'scripts/stage_integrated_candidate.py')
    stage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage)
    dest = tmp_path / 'review'
    manifest = stage.stage(CODE, dest)
    assert manifest['status'] == 'SHADOW_REVIEW_ONLY'
    assert manifest['builder'].endswith('termux_runtime_recovery_candidate_20261121.py')
    assert b'onlineworld' in (dest / 'v13/agi/__init__.py').read_bytes()
    assert (dest / 'scripts/ask_verified_budget.py').is_file()
    assert (dest / 'scripts/native_prefill_stream_client.py').is_file()
    semantic = (dest / 'v13/world_semantic_evidence_candidate.py').read_bytes()
    local_error = (dest / 'v13/local_error_route_shadow_candidate.py').read_bytes()
    store = (dest / 'v13/store.py').read_bytes()
    assert b'safe source read primitives unavailable' in store
    assert b'Source blob is not a regular file' in store
    def source_pin(raw, name):
        needle = b"'" + name.encode('ascii') + b"':"
        assert raw.count(needle) == 1
        start = raw.index(needle) + len(needle)
        quote = raw.find(b"'", start)
        value = raw[quote + 1:quote + 65]
        assert len(value) == 64 and raw[quote + 65:quote + 66] == b"'"
        return value.decode('ascii')
    assert source_pin(semantic, 'store.py') == hashlib.sha256(store).hexdigest()
    assert source_pin(local_error, 'world_semantic_evidence_candidate.py') == hashlib.sha256(semantic).hexdigest()
    budget_source = (dest / 'v13/native_turn_budget.py').read_text(encoding='utf-8')
    cognition_source = (dest / 'v13/cognition.py').read_text(encoding='utf-8')
    assert 'observer_deadline=None' in budget_source
    assert 'minimum_role_slice_s' in cognition_source
    assert 'c4_offer_context_ready' in cognition_source
    assert 'audio_context_refs' in cognition_source
    assert 'def _audio_context_query' in cognition_source
    helper_spec = importlib.util.spec_from_file_location('activation_validate', CODE / 'scripts/activate_termux_recovery.py')
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    assert helper.validate_stage(dest)[0] == dest
    script = '''
import json
from pathlib import Path
import sys
from v13.runtime import Runtime
from v13.operator import Operator
home=Path(sys.argv[1])
r=Runtime(home)
try:
    r.sleep.cycle.set_policy('enabled','off')
    op=Operator(r)
    mode=r.cfg['learning_mode']
    before=json.loads(op.run(':idle status'))
    assert before['enabled'] is False
    enabled=json.loads(op.run(':idle on'))
    assert enabled['enabled'] is True and enabled['worker_alive'] is True
    assert enabled['quota']['mode']=='ROLLING_HOUR'
    assert r.cfg['learning_mode']==mode=='RECORD_ONLY'
    assert json.loads(op.run(':learning'))['learning_mode']==mode
    assert r.store.one('SELECT COUNT(*) n FROM accepted_turns')['n']==0
    assert r.store.one('SELECT COUNT(*) n FROM messages')['n']==0
    assert r.pool.pids()==[] and r.needle.pids()==[]
    assert enabled['last_real_learning']['parameters_fitted'] is False
finally:
    r.close()
r=Runtime(home)
try:
    op=Operator(r)
    assert json.loads(op.run(':idle status'))['enabled'] is True
    assert json.loads(op.run(':idle off'))['enabled'] is False
    print('PASS: composed idle policy persists; no fabricated input or native model runs')
finally:
    r.close()
'''
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path / 'private-home')],
                            cwd=dest, env=dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1'),
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    for name, expected in before.items():
        assert hashlib.sha256((CODE / 'v13' / name).read_bytes()).hexdigest() == expected
