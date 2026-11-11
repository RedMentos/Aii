"""Real Runtime/SQLite provenance tests with a synthetic C3 response seam."""
import json
from pathlib import Path
import shutil
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from v13 import inputs,world_model
from v13 import world_semantic_evidence_candidate as candidate
from v13.runtime import Runtime


@pytest.fixture
def turn(tmp_path):
    r=Runtime(tmp_path)
    r.sleep.cycle.set_policy('enabled','off')
    r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
    r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},
                    generate=lambda *a,**k:iter(['2 + 2 = 5'])))
    r.learner.output_delta=Mock(return_value=None)
    event=r.submit('Check 2 + 2')
    deadline=time.monotonic()+10
    while not r.idle() and time.monotonic()<deadline:time.sleep(.005)
    assert r.idle() and r.last_answer()['status']=='FINAL'
    assert len(world_model.transitions(r.store))==1
    try:yield r,event
    finally:r.close()


def test_completion_and_implicit_feedback_do_not_create_factual_success(turn):
    r,event=turn
    first=candidate.snapshot(r.store,r.session,event)
    assert first['technical_completion']=='FINAL'
    assert first['fact_correction'] is None and first['quality_rating'] is None
    assert first['training_authority']==first['decision_authority']==0
    inputs.record_rating(r.store,event,8,'IMPLICIT_CHAT')
    implicit=candidate.snapshot(r.store,r.session,event)
    assert implicit['quality_rating'] is None
    assert implicit['fingerprint_sha256']==first['fingerprint_sha256']
    inputs.record_rating(r.store,event,8,'EXPLICIT_NOTE')
    explicit=candidate.snapshot(r.store,r.session,event)
    assert explicit['quality_rating']=={'kind':'EXPLICIT_USER_QUALITY_RATING','score':8,
                                        'fact_correctness_label':False}
    assert explicit['fact_correction'] is None
    assert not candidate.still_current(r.store,r.session,event,first['fingerprint_sha256'])


def test_correction_keeps_learning_permission_and_rating_distinct(turn):
    r,event=turn
    inputs.record_rating(r.store,event,8,'EXPLICIT_NOTE')
    r.memory.feedback(event,'fact','2 + 2 = 4',permission='record',key='arithmetic')
    record=candidate.snapshot(r.store,r.session,event)
    assert record['fact_correction']=={'kind':'USER_FACT_CORRECTION','learning_permission':'record',
                                       'source_count':1,'truth_authority':False}
    assert record['quality_rating']['score']==8
    assert candidate.still_current(r.store,r.session,event,record['fingerprint_sha256'])
    # A later correction can change both content and its explicit permission.
    r.memory.feedback(event,'fact','The result is 4',permission='learn',key='arithmetic')
    revised=candidate.snapshot(r.store,r.session,event)
    assert revised['fact_correction']['learning_permission']=='learn'
    assert revised['quality_rating']['score']==8
    assert not candidate.still_current(r.store,r.session,event,record['fingerprint_sha256'])
    assert candidate.still_current(r.store,r.session,event,revised['fingerprint_sha256'])
    assert 'The result is 4' not in json.dumps(revised)
    assert '2 + 2 = 5' not in json.dumps(revised)


def test_deleted_correction_or_input_invalidates_snapshot(turn):
    r,event=turn
    mid=r.memory.feedback(event,'fact','2 + 2 = 4',permission='learn',key='arithmetic')
    observed=candidate.snapshot(r.store,r.session,event)
    source=r.store.one('SELECT source_id FROM memories WHERE id=?',(mid,))['source_id']
    with r.store.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(source,))
    assert not candidate.still_current(r.store,r.session,event,observed['fingerprint_sha256'])
    with pytest.raises(ValueError):candidate.snapshot(r.store,r.session,event)
    with r.store.tx() as c:c.execute('UPDATE sources SET deleted=0 WHERE id=?',(source,))
    assert candidate.still_current(r.store,r.session,event,observed['fingerprint_sha256'])
    source=r.store.one('SELECT source_id FROM events WHERE id=?',(event,))['source_id']
    with r.store.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(source,))
    assert not candidate.still_current(r.store,r.session,event,observed['fingerprint_sha256'])


def test_foreign_session_or_changed_action_is_rejected(turn):
    r,event=turn
    observed=candidate.snapshot(r.store,r.session,event)
    with pytest.raises(ValueError):candidate.snapshot(r.store,r.store.new_session(),event)
    action=observed['t8_action_id']
    with r.store.tx() as c:c.execute('UPDATE actions SET outcome=? WHERE id=?',('{}',action))
    assert not candidate.still_current(r.store,r.session,event,observed['fingerprint_sha256'])
    with pytest.raises(ValueError):candidate.snapshot(r.store,r.session,event)


def test_unbound_feedback_row_fails_closed(turn):
    r,event=turn
    mid=r.memory.feedback(event,'fact','2 + 2 = 4',permission='learn',key='arithmetic')
    with r.store.tx() as c:c.execute('DELETE FROM memories WHERE id=?',(mid,))
    with pytest.raises(ValueError,match='lineage incomplete'):
        candidate.snapshot(r.store,r.session,event)


def test_even_validly_changed_decision_packet_invalidates_old_receipt(turn):
    r,event=turn
    r.memory.feedback(event,'fact','2 + 2 = 4',permission='learn',key='arithmetic')
    before=candidate.snapshot(r.store,r.session,event)
    packet=r.store.one("SELECT id,payload FROM packets WHERE event_id=? AND kind='HumanDecision'",(event,))
    value=json.loads(packet['payload']);value['review_marker']='changed'
    with r.store.tx() as c:c.execute('UPDATE packets SET payload=? WHERE id=?',(json.dumps(value),packet['id']))
    after=candidate.snapshot(r.store,r.session,event)
    assert after['fact_correction']==before['fact_correction']
    assert not candidate.still_current(r.store,r.session,event,before['fingerprint_sha256'])
    assert candidate.still_current(r.store,r.session,event,after['fingerprint_sha256'])


def test_changed_dependency_is_rejected(tmp_path):
    source=Path(candidate.__file__).parent
    for name in candidate.SOURCE_HASHES:
        shutil.copy2(source/name,tmp_path/name)
    candidate.verify_sources(tmp_path)
    path=tmp_path/'world_model.py';path.write_bytes(path.read_bytes()+b'\n# changed\n')
    with pytest.raises(ValueError,match='source changed'):candidate.verify_sources(tmp_path)


def test_duplicate_json_keys_cannot_disguise_an_authoritative_field(turn):
    r,event=turn
    r.memory.feedback(event,'fact','2 + 2 = 4',permission='learn',key='arithmetic')
    before=candidate.snapshot(r.store,r.session,event)
    packet=r.store.one("SELECT id,payload FROM packets WHERE event_id=? AND kind='HumanDecision'",(event,))
    # A last-key-wins reader still sees the legitimate kind='fact'.
    ambiguous='{"kind":"style",'+packet['payload'][1:]
    assert json.loads(ambiguous)['kind']=='fact'
    with r.store.tx() as c:c.execute('UPDATE packets SET payload=? WHERE id=?',(ambiguous,packet['id']))
    assert not candidate.still_current(r.store,r.session,event,before['fingerprint_sha256'])
    with pytest.raises(ValueError):candidate.snapshot(r.store,r.session,event)


def test_later_selection_packet_cannot_rebind_a_prior_action(turn):
    r,event=turn
    observed=candidate.snapshot(r.store,r.session,event)
    message=r.store.one("SELECT id,metadata FROM messages WHERE event_id=? AND role='assistant'",(event,))
    meta=json.loads(message['metadata']);packet=r.store.one('SELECT * FROM packets WHERE id=?',(meta['action_selection'],))
    action=r.store.one('SELECT created FROM actions WHERE id=?',(observed['t8_action_id'],))
    payload=json.loads(packet['payload']);payload['packet_id']='late-test-selection'
    meta['action_selection']='late-test-selection'
    with r.store.tx() as c:
        c.execute('INSERT INTO packets VALUES (?,?,?,?,?,?)',('late-test-selection',packet['kind'],event,
                  packet['generation_id'],json.dumps(payload),action['created']+1.))
        c.execute('UPDATE messages SET metadata=? WHERE id=?',(json.dumps(meta),message['id']))
    assert not candidate.still_current(r.store,r.session,event,observed['fingerprint_sha256'])
    with pytest.raises(ValueError,match='action route changed'):
        candidate.snapshot(r.store,r.session,event)


def test_conflicting_terminal_message_cannot_be_hidden_by_final(turn):
    r,event=turn
    observed=candidate.snapshot(r.store,r.session,event)
    with r.store.tx() as c:
        c.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) "
                  "VALUES (?,?,?,?,?,?,?)",(r.session,event,'assistant','other','ERROR','{}',time.time()))
    assert not candidate.still_current(r.store,r.session,event,observed['fingerprint_sha256'])
    with pytest.raises(ValueError,match='unique terminal'):
        candidate.snapshot(r.store,r.session,event)
