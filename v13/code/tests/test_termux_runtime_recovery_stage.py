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
    assert 'v13/fast_greeting.py' in manifest['replaced_files']
    assert b'EXACT_GREETING_ACK' in (dest / 'v13/runtime.py').read_bytes()
    greeting_script = r'''
import json
import shlex
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

from v13.runtime import Runtime
from v13.operator import Operator
from v13 import runtime as runtime_module
from v13 import output_policy as policy_module


def wait(runtime):
    deadline = time.monotonic() + 8
    while not runtime.idle() and time.monotonic() < deadline:
        time.sleep(.005)
    assert runtime.idle()
    return runtime.last_answer()


# Built-in acknowledgement: real staged Runtime + SQLite, no native or learning path.
r = Runtime(Path(sys.argv[1]))
try:
    r.sleep.cycle.set_policy('enabled', 'off')
    def forbidden(*args, **kwargs):
        raise AssertionError('native/learning path must not run for source-only greeting')
    for obj, attr in (
        (r.pool, 'get'), (r.needle, 'embed'), (r.needle, 'control'),
        (r.cognition, 'percept'), (r.cognition, 'offer'), (r.memory, 'recall'),
        (r.learner, 'decide'), (r.learner, 'output_delta'), (r.learner, 'world_predict'),
    ):
        setattr(obj, attr, forbidden)
    r.online_world_update = forbidden
    generation = r.store.generation_id
    event_id = r.submit('  HALLO… ')
    row = wait(r)
    assert row and (row['text'], row['status']) == ('Hallo.', 'FINAL')
    meta = json.loads(row['metadata'])
    assert meta['fastpath']['kind'] == 'EXACT_GREETING_ACK'
    assert meta['fastpath']['normalized_input'] == 'hallo'
    assert meta['output_policy_owner'] == 'SYSTEM_BUILTIN'
    assert meta['output_policy']['rule_id'] == 'BUILTIN_GREETING_ACK_V1'
    assert meta['model_generated'] is False
    assert meta['experience_eligible'] is False
    assert meta['learning_authority'] == 0
    assert meta['skip_online_world_update'] is True
    assert 'B1_DETAIL' in meta['fastpath']['skipped_organs']
    assert 'C3_DECODE' in meta['skipped_native_stages']
    policy_row = r.store.one(
        "SELECT payload FROM packets WHERE event_id=? AND kind='OutputPolicyDecision'",
        (event_id,),
    )
    policy = json.loads(policy_row['payload'])
    assert policy['rule_id'] == 'BUILTIN_GREETING_ACK_V1'
    assert policy['model_generated'] is False
    assert r.store.read_source(policy['answer_ref']) == 'Hallo.'
    broker_row = r.store.one(
        "SELECT payload FROM packets WHERE event_id=? AND kind='OutputBrokerDecision'",
        (event_id,),
    )
    assert broker_row and json.loads(broker_row['payload'])['committed'] is True
    for kind in ('ActionIntent', 'ActionOutcome', 'PredictionOutcome',
                 'ExperienceRecord', 'WorldTransition', 'CorollaryCopy'):
        assert r.store.one(
            'SELECT id FROM packets WHERE event_id=? AND kind=?', (event_id, kind)
        ) is None, kind
    assert r.store.one(
        'SELECT state FROM accepted_turns WHERE event_id=?', (event_id,)
    )['state'] == 'DONE'
    assert r.store.generation_id == generation
    assert r.pool.pids() == [] and r.needle.pids() == []
    assert r.store.integrity(True) == []
finally:
    r.close()


# A real approved user rule outranks the built-in matcher.
r = Runtime(Path(sys.argv[2]))
try:
    r.sleep.cycle.set_policy('enabled', 'off')
    op = Operator(r)
    rid = op.run(':rules fixed ' + shlex.quote('hi!') + ' ' +
                 shlex.quote('User rule wins.')).split(';')[0]
    op.run(':approve ' + rid)
    spies = []
    def forbidden(*args, **kwargs):
        raise AssertionError('approved fixed rule must not call native models')
    for obj, attr in (
        (r.pool, 'get'), (r.needle, 'embed'), (r.needle, 'control'),
        (r.cognition, 'percept'), (r.cognition, 'offer'), (r.memory, 'recall'),
        (r.learner, 'decide'), (r.learner, 'output_delta'), (r.learner, 'world_predict'),
    ):
        spy = Mock(side_effect=forbidden)
        setattr(obj, attr, spy)
        spies.append(spy)
    event_id = r.submit('hi!')
    row = wait(r)
    assert row and row['text'] == 'User rule wins.'
    meta = json.loads(row['metadata'])
    assert 'fastpath' not in meta
    assert meta['output_policy']['rule_id'] == rid
    policy = json.loads(r.store.one(
        "SELECT payload FROM packets WHERE event_id=? AND kind='OutputPolicyDecision'",
        (event_id,),
    )['payload'])
    assert policy['rule_id'] == rid
    assert all(spy.call_count == 0 for spy in spies)
    assert r.store.integrity(True) == []
finally:
    r.close()


# Failed durable commit must never expose the built-in answer.
r = Runtime(Path(sys.argv[3]))
try:
    r.sleep.cycle.set_policy('enabled', 'off')
    original_commit = runtime_module.txctl.commit_output
    calls = {'n': 0}
    def fail_first_commit(*args, **kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            return False
        return original_commit(*args, **kwargs)
    with patch.object(runtime_module.txctl, 'commit_output', side_effect=fail_first_commit):
        event_id = r.submit('hi!')
        wait(r)
    assert calls['n'] >= 1
    assert r.store.one(
        "SELECT COUNT(*) n FROM messages WHERE event_id=? AND text='Hi.' AND status='FINAL'",
        (event_id,),
    )['n'] == 0
finally:
    r.close()


# Cancellation after policy validation, and an expired deadline, both veto output.
r = Runtime(Path(sys.argv[4]))
try:
    r.sleep.cycle.set_policy('enabled', 'off')
    def cancel_after_policy(store, text):
        r.cancel_event.set()
        return None
    with patch.object(policy_module, 'match', side_effect=cancel_after_policy):
        event_id = r.submit('hi!')
        wait(r)
    assert r.store.one(
        "SELECT COUNT(*) n FROM messages WHERE event_id=? AND text='Hi.' AND status='FINAL'",
        (event_id,),
    )['n'] == 0
finally:
    r.close()

r = Runtime(Path(sys.argv[5]))
try:
    r.sleep.cycle.set_policy('enabled', 'off')
    r.cfg['deadline_seconds'] = -1
    event_id = r.submit('hi!')
    wait(r)
    assert r.store.one(
        "SELECT COUNT(*) n FROM messages WHERE event_id=? AND text='Hi.' AND status='FINAL'",
        (event_id,),
    )['n'] == 0
finally:
    r.close()

print('PASS: staged greeting, user-rule precedence, native/learning skip, commit/cancel/deadline negatives')
'''
    greeting_homes = [tmp_path / ('greeting-' + str(i)) for i in range(5)]
    result = subprocess.run(
        [sys.executable, '-c', greeting_script, *map(str, greeting_homes)],
        cwd=dest,
        env=dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1'),
        text=True, capture_output=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr

