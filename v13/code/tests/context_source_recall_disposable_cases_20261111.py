"""Actual staged Runtime context consumption plus bounded source-read regressions."""
import copy
import json
import sqlite3
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from v13 import archive, archive_stream_range_candidate as stream, context_os
from v13 import context_source_recall_candidate as recall
from v13.history import native_history
from v13.operator import Operator
from v13.runtime import Runtime
from v13.source_read_budget_candidate import ReadBudgetExceeded


def configure(r, sent):
    r.sleep.cycle.set_policy('enabled', 'off')
    r.cfg.update(history_turns=1, context_tokens=8192, answer_tokens=128)
    r._route = Mock(return_value=('simple', {'source': 'SYNTHETIC_CONTEXT_TEST'}))
    def runner(role, *args, **kwargs):
        def generate(messages, *args, **kwargs):
            if role == 'C3_LANGUAGE':
                sent.append(copy.deepcopy(messages))
            yield 'Synthetic response.'
        return SimpleNamespace(role=role, last_metrics={}, generate=generate)
    r.pool.get = Mock(side_effect=runner)
    r.learner.output_delta = Mock(return_value=None)
    context_os.controller(r).set_digest(False)


def turn(r, text, expected='FINAL'):
    eid = r.submit(text)
    end = time.monotonic() + 10
    while not r.idle() and time.monotonic() < end:
        time.sleep(.003)
    assert r.idle()
    assert r.last_answer()['status'] == expected, r.last_answer()
    return eid


def seed(r):
    text = 'The Cedar vault code is 4471. ' + 'Earlier detail Ω😀. ' * 90
    eid = turn(r, text)
    ref = json.loads(r.store.one('SELECT packet FROM events WHERE id=?', (eid,))['packet'])['source_ref']
    assert archive.archive_blob(r.store, ref['sha256'], clock=lambda: time.time() + 40 * 86400) == 'ARCHIVED'
    turn(r, 'A short discussion of weather.')
    turn(r, 'A separate discussion of gardening.')
    assert not (r.home / 'data/blobs' / ref['sha256']).exists(), 'history copies recreated the archived raw blob'
    return eid, ref, text


def enable(r):
    op = Operator(r)
    op.run(':ctxos active')
    op.run(':ctxos recall on')


@pytest.fixture
def live(tmp_path):
    r = Runtime(tmp_path)
    sent = []
    configure(r, sent)
    try:
        yield r, sent
    finally:
        r.close()


def test_archived_older_source_reaches_model_with_bounded_context_and_restart(tmp_path):
    r = Runtime(tmp_path)
    sent = []
    configure(r, sent)
    try:
        old, ref, original = seed(r)
        turn(r, 'What is the Cedar vault code?')
        assert '4471' not in json.dumps(sent[-1])
        Operator(r).run(':ctxos recall on')  # Still SHADOW: no delivery yet.
        turn(r, 'Please recall the Cedar vault code.')
        assert '4471' not in json.dumps(sent[-1])
        Operator(r).run(':ctxos active')
        current = turn(r, 'What is the Cedar vault code?')
        payload = json.dumps(sent[-1], ensure_ascii=False)
        assert '4471' in payload and recall.HEADER in ''.join(m['content'] for m in sent[-1])
        assert original not in payload  # Source restored as a bounded excerpt.
        metadata = json.loads(r.last_answer()['metadata'])
        assert metadata['source_recall']['status'] == 'RESTORED'
        refs = [item for item in metadata['context_source_refs'] if item['source_id'] == ref['source_id']]
        assert refs and any(item['char_end'] - item['char_start'] <= recall.SPAN_CHARS for item in refs)
        plan = json.loads(r.store.one("SELECT payload FROM packets WHERE event_id=? AND kind='ContextPlan' ORDER BY created DESC LIMIT 1", (current,))['payload'])
        assert plan['budget']['planned_chars'] <= plan['budget']['chars']
        assert any(item['item_id'] == 'SOURCE_LINKS' for item in plan['items'])
        assert any(item['source_id'] == ref['source_id'] for item in plan['provenance'])
        r.close()
        r = Runtime(tmp_path)
        configure(r, sent)
        assert recall.enabled(r.store, r.session)
        assert context_os.controller(r)._load()[0]['mode'] == 'ACTIVE'
        turn(r, 'What is the Cedar vault code?')
        assert '4471' in json.dumps(sent[-1])
        with r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?', (ref['source_id'],))
        turn(r, 'What is the Cedar vault code?')
        assert '4471' not in json.dumps(sent[-1])
        rows, _ = native_history(r.store, r.session, 'later-event', 32)
        assert old not in {row['event_id'] for row in rows}
    finally:
        r.close()


def test_only_current_session_is_searched_and_enabled(live):
    r, sent = live
    _, _, _ = seed(r)
    session = r.session
    r.session = r.store.new_session()
    turn(r, 'The Cedar vault code is 9999.')
    assert recall.enabled(r.store, r.session) is False
    r.session = session
    enable(r)
    turn(r, 'What is the Cedar vault code?')
    assert '4471' in json.dumps(sent[-1]) and '9999' not in json.dumps(sent[-1])


def test_revocation_between_context_and_model_call_stops_delivery(live):
    r, sent = live
    _, ref, _ = seed(r)
    enable(r)
    count = len(sent)
    def revoke(*args, **kwargs):
        with r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?', (ref['source_id'],))
        return None
    r.learner.output_delta = Mock(side_effect=revoke)
    turn(r, 'What is the Cedar vault code?', expected='ERROR')
    assert len(sent) == count


def test_off_switch_resources_and_context_room_prevent_retrieval(live):
    r, sent = live
    seed(r)
    with pytest.raises(PermissionError):
        recall.set_enabled(r.store, r.session, True)
    enable(r)
    Operator(r).run(':ctxos recall off')
    turn(r, 'What is the Cedar vault code?')
    assert '4471' not in json.dumps(sent[-1])
    enable(r)
    r.guard.state = 'PRESSURE'
    event = r.store.event(r.session, 'Cedar vault code?')
    result = recall.prepare(r, event['event_id'], 'Cedar vault code?', '', [], [])
    assert result['items'] == [] and result['status'] == 'PAUSED_OR_RESOURCES'
    r.guard.state = 'NORMAL'
    r.cfg.update(context_tokens=512, answer_tokens=128)
    result = recall.prepare(r, event['event_id'], 'Cedar vault code?', 'X' * 2000, [], [])
    assert result['items'] == [] and result['status'] == 'NO_CONTEXT_ROOM'


def test_cancellation_after_read_does_not_return_partial_context(live, monkeypatch):
    r, _ = live
    seed(r)
    enable(r)
    event = r.store.event(r.session, 'Cedar vault code?')
    original = recall.read_span
    def cancel_after_read(*args, **kwargs):
        value = original(*args, **kwargs)
        r.cancel_event.set()
        return value
    monkeypatch.setattr(recall, 'read_span', cancel_after_read)
    result = recall.prepare(r, event['event_id'], 'Cedar vault code?', '', [], [])
    assert result['items'] == result['source_refs'] == []
    assert result['status'] == 'CANCELLED_OR_DEADLINE'
    r.cancel_event.clear()


def test_expired_retrieval_budget_returns_no_layer(live):
    r, _ = live
    seed(r)
    enable(r)
    event = r.store.event(r.session, 'Cedar vault code?')
    result = recall.prepare(r, event['event_id'], 'Cedar vault code?', '', [], [], deadline=time.monotonic() - 1)
    assert result['items'] == [] and result['status'] == 'CANCELLED_OR_DEADLINE'


def test_stream_cancel_after_first_io_never_releases_partial_text(live, monkeypatch):
    r, _ = live
    text = 'Bounded unicode source Ω😀 ' * 10000
    ref = r.store.source(text, 'USER')
    cancelled = threading.Event()
    original = stream.os.read
    def read_then_cancel(*args):
        result = original(*args)
        cancelled.set()
        return result
    monkeypatch.setattr(stream.os, 'read', read_then_cancel)
    with pytest.raises(ReadBudgetExceeded, match='cancelled'):
        stream.read_span(r.store, dict(ref, char_end=24), should_continue=lambda: not cancelled.is_set(),
                         deadline=time.monotonic() + 1)


def test_mutex_wait_and_sqlite_wait_fit_budget_and_restore_timeout(live):
    r, _ = live
    ref = r.store.source('bounded source', 'USER')
    entered = threading.Event()
    release = threading.Event()
    def hold():
        with r.store.mutex:
            entered.set()
            release.wait(3)
    thread = threading.Thread(target=hold)
    thread.start()
    try:
        assert entered.wait(1)
        start = time.monotonic()
        with pytest.raises(ReadBudgetExceeded, match='deadline'):
            stream.read_span(r.store, ref, deadline=start + .05)
        assert time.monotonic() - start < 1.
    finally:
        release.set()
        thread.join(3)
    prior = r.store.db.execute('PRAGMA busy_timeout').fetchone()[0]
    other = sqlite3.connect(r.home / 'data/db/brain.sqlite3', isolation_level=None)
    try:
        other.execute('BEGIN IMMEDIATE')
        start = time.monotonic()
        with pytest.raises(sqlite3.OperationalError, match='locked'):
            stream.read_span(r.store, ref, deadline=start + .1)
        assert time.monotonic() - start < 1.
    finally:
        other.execute('ROLLBACK')
        other.close()
    assert r.store.db.execute('PRAGMA busy_timeout').fetchone()[0] == prior


def test_bounded_reader_refuses_nested_transaction_without_disturbing_caller(live):
    r, _ = live
    ref = r.store.source('bounded source', 'USER')
    with r.store.tx() as db:
        with pytest.raises(ValueError, match='existing transaction'):
            stream.read_span(r.store, ref, deadline=time.monotonic() + 1)
        assert db.in_transaction and db.execute('SELECT 1').fetchone()[0] == 1
    assert r.store.read_source(ref) == 'bounded source'


def test_repeated_text_reference_keeps_archive_and_hot_kind_requires_plain(live):
    r, _ = live
    text = 'An archived textual reference Ω😀. ' * 100
    ref = r.store.source(text, 'USER')
    path = r.home / 'data/blobs' / ref['sha256']
    assert archive.archive_blob(r.store, ref['sha256'], clock=lambda: time.time() + 40 * 86400) == 'ARCHIVED'
    second = r.store.source(text, 'C3_OUTPUT_HISTORY_CONTEXT')
    assert second['source_id'] != ref['source_id'] and r.store.read_source(second) == text
    assert not path.exists()
    r.store.source(text, 'HUMAN_DECISION')
    assert path.read_bytes() == text.encode()


def test_corrupt_shared_archive_does_not_create_new_source_or_plain_copy(live):
    r, _ = live
    text = 'An archived textual reference Ω😀. ' * 100
    ref = r.store.source(text, 'USER')
    path = r.home / 'data/blobs' / ref['sha256']
    assert archive.archive_blob(r.store, ref['sha256'], clock=lambda: time.time() + 40 * 86400) == 'ARCHIVED'
    compressed = path.with_name(path.name + '.z')
    corrupted = compressed.read_bytes() + b'trailing'
    compressed.write_bytes(corrupted)
    count = r.store.one('SELECT COUNT(*) AS n FROM sources')['n']
    with pytest.raises(ValueError, match='trailing'):
        r.store.source(text, 'C3_OUTPUT_HISTORY_CONTEXT')
    assert r.store.one('SELECT COUNT(*) AS n FROM sources')['n'] == count
    assert not path.exists() and compressed.read_bytes() == corrupted


def test_event_session_change_before_model_call_is_rejected(live):
    r, sent = live
    old, _, _ = seed(r)
    other = r.store.new_session()
    enable(r)
    count = len(sent)
    def move_event(*args, **kwargs):
        with r.store.tx() as db:
            db.execute('UPDATE events SET session_id=? WHERE id=?', (other, old))
        return None
    r.learner.output_delta = Mock(side_effect=move_event)
    turn(r, 'What is the Cedar vault code?', expected='ERROR')
    assert len(sent) == count


def test_recalled_source_is_retained_in_later_world_learning_lineage(live):
    r, sent = live
    _, ref, _ = seed(r)
    enable(r)
    turn(r, 'What is the Cedar vault code?')
    assert '4471' in json.dumps(sent[-1])
    Operator(r).run(':learning shadow')
    result = r.online_world_update(limit=1, authority='EXPLICIT_HUMAN')
    assert result['learned'] == 1 and r._online_world.model.seen == 1
    with r.store.tx() as db:
        db.execute('UPDATE sources SET deleted=1 WHERE id=?', (ref['source_id'],))
    with pytest.raises(ValueError, match='source changed or revoked'):
        r._online_world.predict([0., 0., 0., 1.], 'simple')
    assert r._online_world._unusable


@pytest.mark.parametrize('field', ['packet', 'metadata'])
def test_oversized_source_envelope_is_not_delivered_to_model(live, field):
    r, sent = live
    old, ref, _ = seed(r)
    enable(r)
    with r.store.tx() as db:
        if field == 'packet':
            value = json.loads(db.execute('SELECT packet FROM events WHERE id=?', (old,)).fetchone()[0])
            value['_oversized_test'] = 'x' * recall.MAX_ENVELOPE_CHARS
            db.execute('UPDATE events SET packet=? WHERE id=?', (json.dumps(value), old))
        else:
            value = json.loads(db.execute("SELECT metadata FROM messages WHERE event_id=? AND role='user'", (old,)).fetchone()[0])
            value['_oversized_test'] = 'x' * recall.MAX_ENVELOPE_CHARS
            db.execute("UPDATE messages SET metadata=? WHERE event_id=? AND role='user'", (json.dumps(value), old))
    turn(r, 'What is the Cedar vault code?')
    assert '4471' not in json.dumps(sent[-1])
    assert json.loads(r.last_answer()['metadata'])['source_recall']['count'] == 0
    assert r.store.one('SELECT deleted FROM sources WHERE id=?', (ref['source_id'],))['deleted'] == 0
