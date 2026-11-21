"""Actual staged Runtime/SQLite/C5/C6/C7; no native inference or phone proof."""
import json
import time
from unittest.mock import Mock, patch

import pytest

from v13 import context_os, episodes, fastpolicy
from v13.broker import decide, egress_type
from v13.contracts import packet, validate
from v13.focal import ActionGate
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
    until = time.monotonic() + 8
    while not r.idle() and time.monotonic() < until:
        time.sleep(.005)
    assert r.idle(), 'coordinator did not settle'
    row = r.last_answer()
    assert row['status'] == 'FINAL', row
    return row, json.loads(row['metadata'])


def packets(r, event, kind):
    return [json.loads(row['payload']) for row in r.store.rows(
        'SELECT payload FROM packets WHERE event_id=? AND kind=? ORDER BY rowid',
        (event, kind))]


def test_real_arithmetic_source_action_egress_and_restart(runtime):
    r = runtime
    spies = [Mock(side_effect=AssertionError('optional native path entered')) for _ in range(9)]
    r.pool.get, r.needle.control, r.cognition.percept = spies[:3]
    r.learner.student_percept, r.learner.retrieve, r.learner.decide = spies[3:6]
    r.memory.recall = spies[6]
    r.world.forecast = Mock(wraps=r.world.forecast)
    with patch.object(fastpolicy, 'recall_plan', spies[7]), patch.object(episodes, 'recall_turn', spies[8]), \
            patch.object(context_os.controller(r), 'warm', side_effect=AssertionError('warm recall entered')) as warm:
        row, meta = turn(r, 'Was ist 2+2?')
        warm.assert_not_called()
    assert row['text'] == '4'
    assert meta['output_authority'] == 'LOCAL_EXACT_ARITHMETIC'
    assert meta['model_generated'] is False and meta['direct_source_copy'] is False
    assert r.store.read_source(meta['arithmetic_reflex']['source_ref']) == 'Was ist 2+2?'
    assert meta['context_source_refs'] == [meta['arithmetic_reflex']['source_ref']]
    for spy in spies:
        spy.assert_not_called()
    assert r.world.forecast.call_args.kwargs['native_prediction'] is False
    eid = row['event_id']
    assert packets(r, eid, 'PerceptPacket')
    assert packets(r, eid, 'JEFBroadcastPacket')
    assert packets(r, eid, 'OfferPacket') == []
    c5 = packets(r, eid, 'ActionSelection')[-1]
    assert c5['selected']['action_id'] == 'LOCAL_EXACT_ARITHMETIC'
    assert c5['selected']['action_type'] == 'TEXT_REPORT'
    assert c5['permission_class'] == 'local_text_only'
    outcome = packets(r, eid, 'ActionOutcome')[-1]
    assert outcome['actual']['role'] == 'LOCAL_EXACT_ARITHMETIC'
    assert outcome['actual']['model_generated'] is False
    broker = packets(r, eid, 'OutputBrokerDecision')[-1]
    validate('OutputBrokerDecision', broker)
    assert broker['authority'] == 'LOCAL_EXACT_ARITHMETIC'
    assert broker['egress_type'] == 'TEXT_REPORT' and broker['conflicts'] == []
    assert all(p['action_type'] == 'TEXT_REPORT' and p['ok'] for p in packets(r, eid, 'EgressCheck'))
    assert r.cfg['learning_mode'] == 'RECORD_ONLY'
    assert r.store.integrity(True) == []
    home = r.home
    r.close()
    restored = Runtime(home)
    try:
        assert restored.last_answer()['text'] == '4'
        assert restored.store.read_source(meta['arithmetic_reflex']['source_ref']) == 'Was ist 2+2?'
        assert restored.store.integrity(True) == []
    finally:
        restored.close()


@pytest.mark.parametrize('question, answer', [('0*123', '0'), ('1/3', '1/3'), ('calculate -12 * 3', '-36')])
def test_zero_fraction_and_signed_output(runtime, question, answer):
    row, meta = turn(runtime, question)
    assert row['text'] == answer
    assert meta['output_authority'] == 'LOCAL_EXACT_ARITHMETIC'


def test_fixed_rule_and_explicit_copy_keep_their_own_authority(runtime):
    op = Operator(runtime)
    request = op.run(':rules fixed "2+2" "Approved operator answer"').split(';')[0]
    op.run(':approve ' + request)
    row, meta = turn(runtime, '2+2')
    assert row['text'] == 'Approved operator answer'
    assert meta['output_authority'] == 'APPROVED_FIXED_RULE'
    assert packets(runtime, row['event_id'], 'OutputBrokerDecision')[-1]['authority'] == 'APPROVED_FIXED_RULE'
    row, meta = turn(runtime, 'Copy exactly: 2+2')
    assert row['text'] == '2+2'
    assert 'arithmetic_reflex' not in meta
    assert packets(runtime, row['event_id'], 'ActionSelection')[-1]['selected']['action_id'] == 'SOURCE_COPY'
    assert packets(runtime, row['event_id'], 'OutputBrokerDecision')[-1]['authority'] == 'EXPLICIT_EXACT_COPY'


def test_broker_failure_keeps_computed_c6_type(runtime):
    with patch('v13.broker.Broker.finalize', side_effect=ValueError('test broker failure')):
        row, _ = turn(runtime, '7-12')
    assert row['text'] == '-5'
    checks = packets(runtime, row['event_id'], 'EgressCheck')
    assert checks and all(p['action_type'] == 'TEXT_REPORT' and p['ok'] for p in checks)


def test_unknown_authority_and_nondirect_arithmetic_action_rejected(runtime):
    assert decide(['MODEL_ANSWER', 'LOCAL_EXACT_ARITHMETIC'])['selected'] == 'LOCAL_EXACT_ARITHMETIC'
    assert decide(['APPROVED_FIXED_RULE', 'LOCAL_EXACT_ARITHMETIC'])['selected'] == 'APPROVED_FIXED_RULE'
    assert egress_type('LOCAL_EXACT_ARITHMETIC') == 'TEXT_REPORT'
    ref = runtime.store.source('synthetic question', 'USER')
    event = {'event_id': 'evt_contract', 'brain_generation_id': runtime.store.generation_id, 'source_ref': ref}
    with pytest.raises(ValueError, match='known authority'):
        packet('OutputBrokerDecision', 'C7_OUTPUT_BROKER', event['event_id'], event['brain_generation_id'], [ref],
               authority='UNREVIEWED_ARITHMETIC', egress_type='TEXT_REPORT', status='FINAL',
               overridden=[], conflicts=[], committed=True, late=[], rewrites=0)
    for direct, action in ((False, 'LOCAL_EXACT_ARITHMETIC'), (True, 'EXTERNAL_TOOL')):
        with pytest.raises(ValueError, match='deterministic C5'):
            ActionGate(runtime.store).select(event, route='simple', direct=direct,
                                             resource_state='NORMAL', direct_action=action)
