"""Real SQLite/source/archive/G13 checks in the composed compaction tree.

Synthetic decode only. No model training, downloads, deletion or VACUUM.
"""
import copy
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from v13 import archive, context_os, guards, inputs, world_model
from v13 import user_message_compaction_candidate as compact
from v13.agi import hub
from v13.agi.weights import NullTrainer
from v13.body_jepa import BodyJepaTrainer
from v13.history import native_history
from v13.lora_trainer import LoraTrainer
from v13.online_world import OnlineWorld
from v13.operator import Operator
from v13.runtime import Runtime
from v13.source_read_budget_candidate import Budget


def forbidden(*args, **kwargs):
    pytest.fail('message compaction called a trainer')


@pytest.fixture(autouse=True)
def no_training(monkeypatch):
    for trainer in (NullTrainer, BodyJepaTrainer, LoraTrainer):
        monkeypatch.setattr(trainer, 'fit', forbidden)


def configure(runtime, sent):
    runtime.sleep.cycle.set_policy('enabled', 'off')
    runtime.sleep.cycle.set_policy('tick_seconds', '1')
    runtime.cfg.update(history_turns=1, context_tokens=8192, answer_tokens=128)
    runtime._route = Mock(return_value=('simple', {'source': 'SYNTHETIC_COMPACTION_TEST'}))
    def runner(role, *args, **kwargs):
        def generate(messages, *args, **kwargs):
            if role == 'C3_LANGUAGE':
                sent.append(copy.deepcopy(messages))
            yield 'Synthetic compacted-history response.'
        return SimpleNamespace(role=role, last_metrics={}, generate=generate)
    runtime.pool.get = Mock(side_effect=runner)
    runtime.learner.output_delta = Mock(return_value=None)
    context_os.controller(runtime).set_digest(False)


def turn(runtime, text):
    eid = runtime.submit(text)
    until = time.monotonic() + 10
    while not runtime.idle() and time.monotonic() < until:
        time.sleep(.003)
    assert runtime.idle() and runtime.last_answer()['status'] == 'FINAL'
    return eid


@pytest.fixture
def live(tmp_path):
    runtime = Runtime(tmp_path / 'home')
    sent = [];configure(runtime, sent)
    try:
        yield runtime, sent
    finally:
        runtime.close()


def seed(runtime):
    text = 'The Cedar vault code is 4471. ' + 'Ω😀 ' * 600
    event_id = turn(runtime, text)
    event = runtime.store.one('SELECT packet FROM events WHERE id=?', (event_id,))
    ref = json.loads(event['packet'])['source_ref']
    message = runtime.store.one("SELECT * FROM messages WHERE event_id=? AND role='user'", (event_id,))
    old = time.time() - 40 * 86400
    with runtime.store.tx() as db:
        db.execute('UPDATE sources SET created=? WHERE hash=?', (old, ref['sha256']))
        db.execute('UPDATE messages SET created=? WHERE id=?', (old, message['id']))
    assert archive.archive_blob(runtime.store, ref['sha256']) == 'ARCHIVED'
    for i in range(4):
        turn(runtime, 'Recent independent synthetic turn number ' + str(i))
    assert not (runtime.home / 'data/blobs' / ref['sha256']).exists()
    return event_id, message['id'], ref, text


def enable(runtime):
    # Prevent automatic SYSTEM work from racing the explicit test request.
    compact.configure(runtime, {'min_idle_s':86400, 'keep_turns':2}, compact.HUMAN)
    compact.set_enabled(runtime, True, compact.HUMAN)


def request(runtime):
    event_id = json.loads(Operator(runtime).run(':archive compact step'))['scheduled']
    assert event_id is not None
    until = time.monotonic() + 10
    while time.monotonic() < until:
        result = compact.status(runtime)['last_result']
        if result and result['event_id'] == event_id and runtime.idle():
            return result
        time.sleep(.01)
    raise AssertionError('compaction G13 job did not finish: ' + repr(runtime.sleep.scheduler.report()))


def test_default_off_and_forged_direct_job_cannot_modify_user_rows(live):
    runtime, _ = live
    assert not compact.status(runtime)['enabled']
    assert compact.maybe_post(runtime) is None
    with pytest.raises(PermissionError):
        compact.set_enabled(runtime, True)
    with pytest.raises(PermissionError):
        compact.step(runtime, {'id':'forged','action':compact.ACTION,'origin':'USER'})
    assert runtime.store.one("SELECT name FROM sqlite_master WHERE name=?", (compact.TABLE,)) is None


def test_real_worker_compacts_only_user_then_history_recall_restart_and_t8_stay_exact(live):
    runtime, sent = live
    event, mid, ref, text = seed(runtime)
    before = runtime.store.rows('SELECT * FROM messages ORDER BY id')
    pairs_before = guards.store_pairs(runtime.store, runtime.session)
    assert any(query == text for query, _ in pairs_before)
    fingerprint = runtime.memory.experience(event, runtime.session)['fingerprint_sha256']
    enable(runtime)
    result = request(runtime)
    assert result['status'] == 'COMPACTED' and result['message_id'] == mid
    assert result['logical_text_bytes_removed'] == len(text.encode())
    after = runtime.store.rows('SELECT * FROM messages ORDER BY id')
    assert len(before) == len(after)
    for original, current in zip(before, after):
        assert current == (dict(original, text='') if original['id'] == mid else original)
    assert compact.user_event(runtime.store, event)['text'] == text
    assert next(row for row in runtime.store.history(runtime.session, 32) if row['id'] == mid)['text'] == text
    rows, _ = native_history(runtime.store, runtime.session, '', 32, after_id=0)
    assert next(row for row in rows if row['id'] == mid)['text'] == text
    assert runtime.memory.experience(event, runtime.session)['fingerprint_sha256'] == fingerprint
    assert guards.store_pairs(runtime.store, runtime.session) == pairs_before
    verifier = object.__new__(OnlineWorld);verifier.runtime = runtime
    action_ids = {row['id'] for row in runtime.store.rows('SELECT id FROM actions WHERE event_id=?', (event,))}
    transitions = [row for row in world_model.transitions(runtime.store, 64) if row['action_id'] in action_ids]
    assert transitions and all(verifier._source_current(row) for row in transitions)
    Operator(runtime).run(':ctxos active');Operator(runtime).run(':ctxos recall on')
    turn(runtime, 'What is the Cedar vault code?')
    assert '4471' in json.dumps(sent[-1])
    assert runtime.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == ''
    home = runtime.home;runtime.close()
    restored = Runtime(home)
    try:
        configure(restored, sent)
        assert compact.status(restored)['enabled']
        assert compact.status(restored)['reserved_today'] == 1
        assert compact.user_event(restored.store, event)['text'] == text
        assert restored.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == ''
        assert restored.store.read_source(ref) == text
    finally:
        restored.close()


def test_body_and_c3_admission_keep_real_source_provenance_after_compaction(live):
    from v13 import body_jepa_runtime_candidate as body
    runtime, _ = live
    event, mid, ref, text = seed(runtime)
    enable(runtime);assert request(runtime)['compacted']
    runtime.memory.feedback(event, 'fact', 'A synthetic approved correction.', permission='learn')
    Operator(runtime).run(':learning shadow')
    weights = hub(runtime).weights
    c3 = [item for item in weights.candidates(require_replay_pass=False) if item['event_id'] == event]
    assert len(c3) == 1 and c3[0]['prompt'] == text and c3[0]['source_dependencies'] == [ref]
    body_weights = SimpleNamespace(s=runtime.store, cfg=runtime.cfg, box=weights.box,
                                   _replay_passed=weights._replay_passed)
    rows = [item for item in body.candidates(body_weights, False) if item['event_id'] == event]
    assert len(rows) == 1 and rows[0]['prompt'] == text and rows[0]['source_dependencies'] == [ref]
    assert runtime.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == ''


def test_source_revocation_prevents_hydration_recall_and_clears_derived_prefix(live):
    runtime, sent = live
    event, mid, ref, _ = seed(runtime)
    enable(runtime);assert request(runtime)['compacted']
    with runtime.store.tx() as db:
        db.execute('UPDATE sources SET deleted=1 WHERE id=?', (ref['source_id'],))
    assert compact.user_event(runtime.store, event) is None
    assert runtime.store.one('SELECT prefix FROM compacted_user_messages_v1 WHERE message_id=?', (mid,))['prefix'] is None
    rows, _ = native_history(runtime.store, runtime.session, '', 32, after_id=0)
    assert event not in {row['event_id'] for row in rows}
    Operator(runtime).run(':ctxos active');Operator(runtime).run(':ctxos recall on')
    turn(runtime, 'What is the Cedar vault code?')
    assert '4471' not in json.dumps(sent[-1])


def test_corrupt_archive_never_removes_original_sql_text(live):
    runtime, _ = live
    _, mid, ref, text = seed(runtime)
    path = runtime.home / 'data/blobs' / (ref['sha256'] + '.z')
    path.write_bytes(path.read_bytes() + b'trailing')
    enable(runtime);result = request(runtime)
    assert not result['compacted']
    assert runtime.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == text
    assert runtime.store.one('SELECT 1 FROM compacted_user_messages_v1 WHERE message_id=?', (mid,)) is None


def test_injected_sql_publish_failure_rolls_back_text_and_receipt(live):
    runtime, _ = live
    _, mid, _, text = seed(runtime)
    enable(runtime)
    with runtime.store.tx() as db:
        db.execute("CREATE TRIGGER synthetic_compaction_failure BEFORE UPDATE OF text ON messages WHEN NEW.text='' BEGIN SELECT RAISE(ABORT,'SYNTHETIC_COMPACTION_ABORT'); END")
    # Existing G13 records the failed job; its reservation remains charged.
    event_id = json.loads(Operator(runtime).run(':archive compact step'))['scheduled']
    until = time.monotonic() + 10
    while time.monotonic() < until:
        if runtime.idle() and compact.status(runtime)['reserved_today'] == 1:
            break
        time.sleep(.01)
    assert event_id is not None
    assert compact.status(runtime)['reserved_today'] == 1
    assert runtime.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == text
    assert runtime.store.one('SELECT 1 FROM compacted_user_messages_v1 WHERE message_id=?', (mid,)) is None


def test_daily_attempt_budget_survives_restart(live):
    runtime, sent = live
    _, mid, _, _ = seed(runtime)
    compact.configure(runtime, {'daily_attempts':1}, compact.HUMAN)
    enable(runtime);assert request(runtime)['compacted']
    assert request(runtime)['status'] == 'SKIPPED_DAILY_BUDGET'
    home = runtime.home;runtime.close()
    restored = Runtime(home)
    try:
        configure(restored, sent)
        assert compact.status(restored)['reserved_today'] == 1
        assert request(restored)['status'] == 'SKIPPED_DAILY_BUDGET'
        assert restored.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == ''
    finally:
        restored.close()


def test_training_pause_prevents_compaction_without_charging(live):
    runtime, _ = live
    _, mid, _, text = seed(runtime)
    enable(runtime)
    inputs.set_pause(runtime.store, 'training', True)
    result = request(runtime)
    assert result['status'] == 'SKIPPED_PAUSED_OR_CANCELLED'
    assert compact.status(runtime)['reserved_today'] == 0
    assert runtime.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == text


def test_compaction_rejects_an_outer_transaction_before_any_mutation(live):
    runtime, _ = live
    _, mid, _, text = seed(runtime)
    enable(runtime)
    state = compact.box(runtime).load()[0]
    with runtime.store.tx():
        with pytest.raises(ValueError):
            compact._compact(runtime, state, Budget(time.monotonic()+1.))
        assert runtime.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == text
        assert runtime.store.one('SELECT 1 FROM compacted_user_messages_v1 WHERE message_id=?', (mid,)) is None
    assert runtime.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == text


def test_expired_hydration_budget_returns_unavailable_without_materializing_text(live):
    runtime, _ = live
    _, mid, _, _ = seed(runtime)
    enable(runtime);assert request(runtime)['compacted']
    row = runtime.store.one('SELECT * FROM messages WHERE id=?', (mid,))
    budget = Budget(time.monotonic()+1.)
    budget.deadline = time.monotonic()-1.
    rows = compact.hydrate_rows(runtime.store, [row], budget=budget)
    assert len(rows) == 1 and rows[0]['text'] == '' and rows[0]['text_unavailable']
    assert runtime.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == ''


def test_error_after_commit_never_claims_known_nonpublication(live, monkeypatch):
    runtime, _ = live
    event, mid, _, text = seed(runtime)
    enable(runtime)
    original = compact._compact
    def committed_then_error(*args):
        result = original(*args)
        assert result['compacted']
        raise OSError('synthetic exception after actual commit')
    monkeypatch.setattr(compact, '_compact', committed_then_error)
    result = request(runtime)
    assert result['status'] == 'UNKNOWN_IO_OUTCOME' and result['compacted'] is None
    assert runtime.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == ''
    assert compact.user_event(runtime.store, event)['text'] == text
