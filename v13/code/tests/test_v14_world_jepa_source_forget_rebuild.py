"""Source-forget rollback/replay for the persistent WorldJEPA Store consumer.

These tests use synthetic ActionOutcome fixtures through the real SQLite Store.
They prove checkpoint invalidation and source-verified replay only; they do not
prove native GGUF learning, Android behavior, or resistance to correlated-data
relearning.
"""
from v13 import contracts, world_model
from v13.memory import Memory
from v13.store import Store
from v13.world_jepa_consumer import WorldJEPAStoreConsumer


def _make_store(home):
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session("V14 JEPA source-forget replay")
    return store, session


def _add_transitions(store, session, start, count):
    event_ids = []
    actions = tuple(world_model.ACTIONS)
    for index in range(start, start + count):
        text = f"source-forget-fixture-{index:04d}" + ("x" * (index % 29))
        event = store.event(session, text)
        event_id = event["event_id"]
        generation = event["brain_generation_id"]
        route = actions[index % len(actions)]
        selection = contracts.packet(
            "ActionSelection", "C2_CONTROL", event_id, generation,
            [event["source_ref"]],
            selected={
                "action_id": "TEXT_REPORT", "action_type": "TEXT_REPORT",
                "score": 0.0, "permission_class": "local_text_only",
                "focal_support": 0.0,
            },
            candidates=[], suppressed=[], permission_class="local_text_only",
            route_hint=route, stage="COMMIT",
        )
        store.add_packet("ActionSelection", selection)
        action_id = store.start_action(
            event_id, generation,
            forecast={"input_chars": len(text), "resource_state": "NORMAL"},
        )
        action_index = index % len(actions)
        store.finish_action(
            action_id,
            "FAILED" if index % 5 == 0 else "FINAL",
            {
                "action_duration_s": 0.15 + action_index * 0.65 + (index % 13) * 0.02,
                "characters": 9 + action_index * 24 + (index % 23) * 0.75,
            },
        )
        event_ids.append(event_id)
    return event_ids


def _source_id(store, event_id):
    row = store.one("SELECT source_id FROM events WHERE id=?", (event_id,))
    assert row is not None
    return row["source_id"]


def _forget(store, source_id):
    memory = object.__new__(Memory)
    memory.s = store
    return memory._forget_source(source_id, None)


def _train(consumer, limit, steps):
    result = consumer.update(
        limit=limit, steps=steps, optimizer_permission=True,
        replay_mode="uniform",
    )
    assert result["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA", result
    return result


def test_forget_rolls_back_to_clean_checkpoint_and_replays_remaining_t8(tmp_path):
    home = tmp_path / "clean-previous"
    store, session = _make_store(home)
    try:
        consumer = WorldJEPAStoreConsumer(
            store, home / "world_jepa", learning_enabled=True
        )
        first_events = _add_transitions(store, session, 0, 256)
        first = _train(consumer, 256, 120)
        second_events = _add_transitions(store, session, 256, 32)
        second = _train(consumer, 64, 24)

        state, _ = consumer._read_state()
        active, previous = state["active"], state["previous"]
        forgotten_source = _source_id(store, second_events[-1])
        assert forgotten_source in {
            row["source_id"] for row in active["experience_rows"]
        }
        assert forgotten_source not in {
            row["source_id"] for row in previous["experience_rows"]
        }
        tainted_path = home / "world_jepa" / active["checkpoint"]
        clean_path = home / "world_jepa" / previous["checkpoint"]
        clean_sha = previous["checkpoint_sha256"]
        clean_cursor = previous["scan_cursor"]

        _forget(store, forgotten_source)

        restored, _ = consumer._read_state()
        assert restored["active"]["checkpoint_sha256"] == clean_sha
        assert restored["previous"] is None
        assert restored["scan_cursor"] == clean_cursor
        assert restored["pending_rows"] == []
        assert not tainted_path.exists()
        assert clean_path.is_file()
        source = store.one(
            "SELECT deleted FROM sources WHERE id=?", (forgotten_source,)
        )
        assert source is not None and source["deleted"] == 1

        _add_transitions(store, session, 288, 64)
        replay = consumer.update(
            limit=128, steps=24, optimizer_permission=True,
            replay_mode="uniform",
        )
        assert replay["rejected_receipts"] >= 1
        final, _ = consumer._read_state()
        assert forgotten_source not in {
            row["source_id"] for row in final["active"]["experience_rows"]
        } if final["active"] is not None else True
        assert forgotten_source not in {
            row["source_id"] for row in final["pending_rows"]
        }
        assert final["scan_cursor"] > clean_cursor
        assert second["checkpoint_sha256"] != first["checkpoint_sha256"]
    finally:
        store.close()


def test_forget_invalidates_both_tainted_checkpoints_and_restarts_scan(tmp_path):
    home = tmp_path / "both-tainted"
    store, session = _make_store(home)
    try:
        consumer = WorldJEPAStoreConsumer(
            store, home / "world_jepa", learning_enabled=True
        )
        first_events = _add_transitions(store, session, 0, 256)
        first = _train(consumer, 256, 120)
        _add_transitions(store, session, 256, 32)
        second = _train(consumer, 64, 24)

        state, _ = consumer._read_state()
        active, previous = state["active"], state["previous"]
        forgotten_source = _source_id(store, first_events[0])
        assert forgotten_source in {
            row["source_id"] for row in active["experience_rows"]
        }
        assert forgotten_source in {
            row["source_id"] for row in previous["experience_rows"]
        }
        active_path = home / "world_jepa" / active["checkpoint"]
        previous_path = home / "world_jepa" / previous["checkpoint"]

        _forget(store, forgotten_source)

        reset, _ = consumer._read_state()
        assert reset["active"] is None
        assert reset["previous"] is None
        assert reset["scan_cursor"] == 0
        assert reset["pending_rows"] == []
        assert not active_path.exists()
        assert not previous_path.exists()

        replay = consumer.update(
            limit=512, steps=120, optimizer_permission=True,
            replay_mode="uniform",
        )
        assert replay["rejected_receipts"] >= 1
        after, _ = consumer._read_state()
        rows = (
            after["active"]["experience_rows"]
            if after["active"] is not None else after["pending_rows"]
        )
        assert forgotten_source not in {row["source_id"] for row in rows}
        assert after["scan_cursor"] > 0
        assert second["checkpoint_sha256"] != first["checkpoint_sha256"]
    finally:
        store.close()


def test_forget_of_pending_only_source_does_not_invalidate_clean_state(tmp_path):
    home = tmp_path / "pending-only"
    store, session = _make_store(home)
    try:
        consumer = WorldJEPAStoreConsumer(
            store, home / "world_jepa", learning_enabled=True
        )
        event_ids = _add_transitions(store, session, 0, 1)
        pending = consumer.update(
            limit=16, steps=8, optimizer_permission=True,
            replay_mode="uniform",
        )
        assert pending["status"] == "INSUFFICIENT_SOURCE_DISJOINT_T8_COHORT"
        before, _ = consumer._read_state()
        assert before["active"] is None
        assert len(before["pending_rows"]) == 1
        cursor = before["scan_cursor"]
        forgotten_source = _source_id(store, event_ids[0])

        _forget(store, forgotten_source)

        after, _ = consumer._read_state()
        assert after["active"] is None
        assert after["previous"] is None
        assert after["scan_cursor"] == cursor
        assert after["pending_rows"] == []
        source = store.one(
            "SELECT deleted FROM sources WHERE id=?", (forgotten_source,)
        )
        assert source is not None and source["deleted"] == 1
    finally:
        store.close()
