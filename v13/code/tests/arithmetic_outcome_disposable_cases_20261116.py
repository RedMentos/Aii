"""Real staged arithmetic World and failed-turn receipts; no model/phone proof."""
import json
from pathlib import Path
import shutil
import time
from unittest.mock import patch

import pytest

from v13.common import digest
from v13.operator import Operator
from v13.runtime import Runtime


@pytest.fixture
def runtime(tmp_path):
    r = Runtime(tmp_path / 'home')
    r.sleep.cycle.set_policy('enabled', 'off')
    try:
        yield r
    finally:
        r.close()


def turn(r, text):
    r.submit(text)
    until = time.monotonic() + 30
    while not r.idle() and time.monotonic() < until:
        time.sleep(.005)
    assert r.idle(), 'coordinator did not settle'
    row = r.last_answer()
    assert row is not None
    return row, json.loads(row['metadata'])


def latest_packet(r, eid, kind):
    row = r.store.one('SELECT payload FROM packets WHERE event_id=? AND kind=? ORDER BY rowid DESC LIMIT 1', (eid, kind))
    assert row is not None, kind
    return json.loads(row['payload'])


def test_arithmetic_world_source_transition_survives_restart(runtime):
    r = runtime
    row, meta = turn(r, 'calculate 8/4')
    assert row['status'] == 'FINAL' and row['text'] == '2'
    action = r.store.one('SELECT * FROM actions WHERE event_id=?', (row['event_id'],))
    forecast = json.loads(action['expected'])['forecast']
    assert forecast['profile']['role'] == 'LOCAL_EXACT_ARITHMETIC'
    assert forecast['profile']['model_revision'] is None
    with patch.object(r.models, 'revision', side_effect=AssertionError('deterministic action has no model')):
        assert r.world.profile('LOCAL_EXACT_ARITHMETIC')['model_revision'] is None
        transition = r.world.transition(action['id'])
    assert transition['source_ref'] == meta['arithmetic_reflex']['source_ref']
    assert transition['action_role'] == 'LOCAL_EXACT_ARITHMETIC'
    assert r.store.read_source(transition['source_ref']) == 'calculate 8/4'
    assert r.store.read_source(transition['outcome_source_ref']) == '2'
    assert transition['teacher_truth_authority'] is False
    assert transition['external_world_observation'] is False
    assert transition['semantic_success'] is None
    assert r.world.transition(action['id'])['packet_id'] == transition['packet_id']
    home = r.home
    r.close()
    restored = Runtime(home)
    try:
        resumed = restored.world.transition(action['id'])
        assert resumed == transition
        assert restored.store.read_source(resumed['source_ref']) == 'calculate 8/4'
        assert restored.store.read_source(resumed['outcome_source_ref']) == '2'
        assert restored.cfg['learning_mode'] == 'RECORD_ONLY'
        assert restored.store.integrity(True) == []
    finally:
        restored.close()


@pytest.mark.parametrize('fixed', [False, True])
@pytest.mark.parametrize('failure', ['c5', 'forecast'])
def test_source_diagnostic_wins_stale_direct_and_fixed_flags(runtime, fixed, failure):
    r = runtime
    if fixed:
        op = Operator(r)
        request = op.run(':rules fixed "2+2" "Approved operator answer"').split(';')[0]
        op.run(':approve ' + request)
    target = 'v13.focal.ActionGate.select' if failure == 'c5' else 'v13.world.WorldState.forecast'
    with patch(target, side_effect=ValueError('synthetic pre-output failure')):
        row, meta = turn(r, '2+2')
    assert row['status'] == 'ERROR'
    assert row['text'] != '4' and row['text'] != 'Approved operator answer'
    assert meta['model_generated'] is False
    assert meta['output_authority'] == 'SOURCE_SYSTEM_REPORT'
    assert bool(meta.get('exact_policy_matched')) is fixed
    broker = latest_packet(r, row['event_id'], 'OutputBrokerDecision')
    assert broker['authority'] == 'SOURCE_SYSTEM_REPORT'
    assert broker['egress_type'] == 'SYSTEM_REPORT'
    assert broker['overridden'] == []
    check = latest_packet(r, row['event_id'], 'EgressCheck')
    assert check['action_type'] == 'SYSTEM_REPORT' and check['ok']
    assert r.cfg['learning_mode'] == 'RECORD_ONLY'


def test_world_transition_still_rejects_unknown_and_forged_arithmetic(runtime):
    r = runtime
    row, _ = turn(r, '2+2')
    action = r.store.one('SELECT * FROM actions WHERE event_id=?', (row['event_id'],))
    with pytest.raises(ValueError, match='Unknown World action role'):
        r.world.profile('UNREVIEWED_ARITHMETIC')
    outcome = json.loads(action['outcome'])
    with r.store.tx() as c:
        c.execute('UPDATE actions SET outcome=? WHERE id=?', (json.dumps(outcome | {'role': 'UNREVIEWED_ARITHMETIC'}), action['id']))
    with pytest.raises(ValueError, match='measured action role mismatch'):
        r.world.transition(action['id'])
    # Even internally consistent replacement output/hash cannot acquire the
    # deterministic role without matching the bounded source computation.
    with r.store.tx() as c:
        c.execute('UPDATE actions SET outcome=? WHERE id=?', (json.dumps(outcome | {'self_candidate_hash': digest('5')}), action['id']))
        c.execute('UPDATE messages SET text=? WHERE id=?', ('5', row['id']))
    with pytest.raises(ValueError, match='arithmetic outcome/source mismatch'):
        r.world.transition(action['id'])


def test_record_only_world_receipt_does_not_allow_training(runtime):
    r = runtime
    row, _ = turn(r, '2+2')
    action = r.store.one('SELECT id FROM actions WHERE event_id=?', (row['event_id'],))
    r.world.transition(action['id'])
    with pytest.raises(ValueError, match='RECORD_ONLY'):
        r.learner.shadow_world()


def test_reviewed_semantic_dependency_binding_still_rejects_tampered_world(tmp_path):
    from v13 import local_error_route_shadow_candidate as local_error
    from v13 import world_semantic_evidence_candidate as semantic
    semantic.verify_sources()
    local_error._check_sources()
    original = Path(semantic.__file__).parent
    bound = tmp_path / 'bound'
    bound.mkdir()
    for name in semantic.SOURCE_HASHES:
        shutil.copyfile(original / name, bound / name)
    semantic.verify_sources(bound)
    world = bound / 'world.py'
    world.write_bytes(world.read_bytes() + b'\n# synthetic dependency corruption\n')
    with pytest.raises(ValueError, match='candidate source changed: world.py'):
        semantic.verify_sources(bound)
