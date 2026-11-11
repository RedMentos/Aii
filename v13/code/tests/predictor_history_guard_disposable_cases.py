"""Real Runtime/SQLite source-history regressions in the integrated test copy."""
import json
import sqlite3
import threading

import pytest

from integrated_online_world_disposable_cases import synthetic_c3, turn
from v13 import online_world_history_guard_candidate as history
from v13 import online_world_policy, world_model
from v13.online_world import OnlineWorld
from v13.operator import Operator
from v13.runtime import Runtime


def two_committed_turns(r):
    synthetic_c3(r)
    first = turn(r)
    r.session = r.store.new_session()
    second = turn(r)
    assert len(world_model.transitions(r.store, limit=10)) == 2
    Operator(r).run(':learning shadow')
    assert r.online_world_update(limit=64, authority=online_world_policy.HUMAN)['learned'] == 2
    return first, second


def test_old_source_revalidated_for_predict_and_update_after_restart(tmp_path, monkeypatch):
    r = Runtime(tmp_path)
    try:
        old, _ = two_committed_turns(r)
        world = r._online_world
        all_ids = set(world.processed)
        assert len(all_ids) == 2
        # Exercise independent bounded chunks without manufacturing new rows.
        monkeypatch.setattr(history, 'CHUNK', 1)
        calls = []
        check = world._source_current
        def record(row):
            calls.append(row['action_id'])
            return check(row)
        monkeypatch.setattr(world, '_source_current', record)
        assert len(world.predict([0., 0., 0., 1.], 'simple')) == 3
        assert set(calls) == all_ids
        source = r.store.one('SELECT source_id FROM events WHERE id=?', (old,))['source_id']
        with r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?', (source,))
        # Old source is outside this requested latest-one transition window.
        assert world_model.transitions(r.store, limit=1)[0]['action_id'] != next(
            row['id'] for row in r.store.rows('SELECT id FROM actions WHERE event_id=?', (old,))
            if row['id'] in all_ids)
        with pytest.raises(ValueError, match='source changed or revoked'):
            world.predict([0., 0., 0., 1.], 'simple')
        assert world._unusable
        with pytest.raises(RuntimeError, match='review'):
            world.predict([0., 0., 0., 1.], 'simple')
        r.close()
        r = Runtime(tmp_path)
        Operator(r).run(':learning shadow')
        restored = OnlineWorld(r)
        with pytest.raises(ValueError, match='source changed or revoked'):
            restored.predict([0., 0., 0., 1.], 'simple')
        with pytest.raises(ValueError, match='source changed or revoked'):
            r.online_world_update(limit=1, authority=online_world_policy.HUMAN)
        assert r._online_world._unusable
    finally:
        r.close()


def test_old_transition_content_change_quarantines_model(tmp_path):
    r = Runtime(tmp_path)
    try:
        old, _ = two_committed_turns(r)
        world = r._online_world
        row = r.store.one('SELECT id,expected FROM actions WHERE event_id=? AND expected LIKE ?',
                          (old, '%"forecast"%'))
        data = json.loads(row['expected'])
        data['forecast']['input_chars'] += 7
        with r.store.tx() as db:
            db.execute('UPDATE actions SET expected=? WHERE id=?', (json.dumps(data), row['id']))
        with pytest.raises(ValueError, match='source changed or revoked'):
            world.predict([0., 0., 0., 1.], 'simple')
        assert world._unusable
    finally:
        r.close()


def test_source_revocation_cannot_commit_during_checked_prediction(tmp_path, monkeypatch):
    r = Runtime(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    thread = None
    try:
        old, _ = two_committed_turns(r)
        world = r._online_world
        original = world.model.predict
        def slow_prediction(*args):
            entered.set()
            if not release.wait(5):
                raise TimeoutError('test prediction was not released')
            return original(*args)
        monkeypatch.setattr(world.model, 'predict', slow_prediction)
        result = []
        def predict():
            try:
                result.append(world.predict([0., 0., 0., 1.], 'simple'))
            except BaseException as exc:
                result.append(exc)
        thread = threading.Thread(target=predict)
        thread.start()
        assert entered.wait(5)
        # A second SQLite connection cannot begin a revocation while the
        # verified prediction holds the same write fence.
        db = sqlite3.connect(tmp_path / 'data/db/brain.sqlite3', timeout=.2, isolation_level=None)
        try:
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                db.execute('BEGIN IMMEDIATE')
        finally:
            db.close()
        release.set()
        thread.join(5)
        assert not thread.is_alive() and len(result) == 1 and isinstance(result[0], list)
        source = r.store.one('SELECT source_id FROM events WHERE id=?', (old,))['source_id']
        with r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?', (source,))
        with pytest.raises(ValueError, match='source changed or revoked'):
            world.predict([0., 0., 0., 1.], 'simple')
    finally:
        release.set()
        if thread is not None:
            thread.join(5)
        r.close()


def test_source_revocation_cannot_commit_during_new_checked_update(tmp_path, monkeypatch):
    r = Runtime(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    thread = None
    try:
        synthetic_c3(r)
        old = turn(r)
        Operator(r).run(':learning shadow')
        assert r.online_world_update(limit=64, authority=online_world_policy.HUMAN)['learned'] == 1
        r.session = r.store.new_session()
        turn(r)
        world = r._online_world
        original = world.model.observe
        def slow_update(*args):
            entered.set()
            if not release.wait(5):
                raise TimeoutError('test update was not released')
            return original(*args)
        monkeypatch.setattr(world.model, 'observe', slow_update)
        result = []
        def update():
            try:
                result.append(r.online_world_update(limit=64, authority=online_world_policy.HUMAN))
            except BaseException as exc:
                result.append(exc)
        thread = threading.Thread(target=update)
        thread.start()
        assert entered.wait(5)
        db = sqlite3.connect(tmp_path / 'data/db/brain.sqlite3', timeout=.2, isolation_level=None)
        try:
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                db.execute('BEGIN IMMEDIATE')
        finally:
            db.close()
        release.set()
        thread.join(5)
        assert not thread.is_alive() and len(result) == 1 and result[0]['learned'] == 1
        source = r.store.one('SELECT source_id FROM events WHERE id=?', (old,))['source_id']
        with r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?', (source,))
        with pytest.raises(ValueError, match='source changed or revoked'):
            r.online_world_update(limit=1, authority=online_world_policy.HUMAN)
        assert world._unusable
    finally:
        release.set()
        if thread is not None:
            thread.join(5)
        r.close()
