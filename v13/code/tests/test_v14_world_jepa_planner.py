"""Focused integration tests for the source-bound WorldJEPA planner receiver.

All experiences are synthetic rows through the real V13 SQLite Store. These
tests do not claim native GGUF learning, Redmi behavior, or production routing.
"""
import json

from v13 import contracts, world_model
from v13.store import Store
from v13.world_jepa_store_authority import MAX_ACTION_OUTCOMES_PER_EVENT
from v13.world_jepa_consumer import WorldJEPAStoreConsumer
from v13.world_jepa_planner import consume_world_planner_shadow, read_world_planner_shadow
from v13.world_jepa_receiver_matrix import receiver_matrix


def _make_store(home):
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    session = store.new_session("V14 JEPA integration test")
    return store, session


def _add_transitions(store, session, start, count, status_overrides=None, source_text_factory=None):
    status_overrides = status_overrides or {}
    action_ids = []
    actions = tuple(world_model.ACTIONS)
    for index in range(start, start + count):
        text = (source_text_factory(index) if source_text_factory is not None
                else f"synthetic-user-content-{index:04d}" + ("x" * (index % 29)))
        event = store.event(session, text)
        event_id = event["event_id"]
        generation = event["brain_generation_id"]
        action_index = index % len(actions)
        route = actions[action_index]

        # Selection must be persisted before dispatch: world_model.transitions()
        # admits only the committed selection that existed at action.created.
        selection = contracts.packet(
            "ActionSelection",
            "C2_CONTROL",
            event_id,
            generation,
            [event["source_ref"]],
            selected={
                "action_id": "TEXT_REPORT",
                "action_type": "TEXT_REPORT",
                "score": 0.0,
                "permission_class": "local_text_only",
                "focal_support": 0.0,
            },
            candidates=[],
            suppressed=[],
            permission_class="local_text_only",
            route_hint=route,
            stage="COMMIT",
        )
        store.add_packet("ActionSelection", selection)

        action_id = store.start_action(
            event_id,
            generation,
            forecast={
                "input_chars": len(text),
                "resource_state": "NORMAL",
            },
        )
        # Controlled action-conditioned signal: the committed route changes
        # both observed duration and output size; independent nuisance terms
        # keep the fixture from being a pure action lookup. This is a synthetic
        # positive control, not a claim about real-user outcome distributions.
        duration = 0.15 + action_index * 0.65 + (index % 13) * 0.02
        characters = 9 + action_index * 24 + (index % 23) * 0.75
        status = status_overrides.get(index, "FAILED" if index % 5 == 0 else "FINAL")
        store.finish_action(
            action_id,
            status,
            {"action_duration_s": duration, "characters": characters},
        )
        action_ids.append(action_id)
    return action_ids


def _make_committed_planner_action(store, session, text):
    event = store.event(session, text)
    action_id = store.start_action(
        event["event_id"],
        event["brain_generation_id"],
        forecast={"input_chars": len(text), "resource_state": "NORMAL"},
    )
    actual = {"action_duration_s": 0.5, "characters": 12}
    store.finish_action(action_id, "FINAL", actual)
    return event, action_id, actual


def test_postcommit_world_planner_consumes_numeric_b1_b2_receivers_with_learning_gates_closed(tmp_path):
    home = tmp_path / "brain-planner"
    store, session = _make_store(home)
    try:
        _add_transitions(store, session, 0, 256)
        learner = WorldJEPAStoreConsumer(
            store, home / "world_jepa", learning_enabled=True, seed=13, ensemble=2
        )
        trained = learner.update(limit=256, steps=120, optimizer_permission=True)
        assert trained["status"] == "UPDATED_EXPERIMENTAL_WORLD_JEPA"
        active_before, _ = store.state("v14.world_jepa.store_consumer", None)
        checkpoint_before = active_before["active"]["checkpoint_sha256"]

        text = "current planner receiver source with exact source binding"
        event, _, _ = _make_committed_planner_action(store, session, text)
        shadow = consume_world_planner_shadow(store, event["event_id"], home=home)
        assert shadow["status"] == "SHADOW_PLANNER_READY"
        assert shadow["persisted"] is True
        assert shadow["decision_authority"] == "NONE"
        assert shadow["dispatch"] is False
        assert shadow["native_body_consumed"] is False
        assert shadow["native_body_weights_changed"] is False
        assert shadow["representation"] == "NUMERIC_ROLE_READOUTS_NOT_NATIVE_BODY_LATENT"
        assert len(shadow["ranked_actions"]) == len(world_model.ACTIONS)
        assert all(
            item["status"] == "READY"
            and item["B1_DETAIL"]["status"] == "SHADOW_READOUT_ONLY"
            and item["B2_GIST"]["status"] == "SHADOW_READOUT_ONLY"
            and item["SELF_MODEL"]["status"] == "SHADOW_READOUT_ONLY"
            for item in shadow["candidate_readouts"].values()
        )
        assert shadow["memory_recall"]["status"] == "MEMORY_RECALL_SHADOW"
        assert shadow["memory_recall"]["items"]
        assert all(
            "source_sha256" in item and "outcome_sha256" in item
            for item in shadow["memory_recall"]["items"]
        )
        assert text not in repr(shadow)

        persisted = read_world_planner_shadow(store, event["event_id"])
        assert persisted["status"] == "SHADOW_PLANNER_READY"
        assert persisted["checkpoint_sha256"] == checkpoint_before

        matrix = receiver_matrix(
            store, shadow["state_vector"], ["simple", "detail"], home=home
        )
        assert set(matrix) == {"simple", "detail"}
        assert all(
            set(matrix[action]) == {"B1_DETAIL", "B2_GIST", "SELF_MODEL"}
            for action in matrix
        )

        again = consume_world_planner_shadow(store, event["event_id"], home=home)
        assert again["idempotent"] is True
        active_after, _ = store.state("v14.world_jepa.store_consumer", None)
        assert active_after["active"]["checkpoint_sha256"] == checkpoint_before

        active_for_stale, version = store.state("v14.world_jepa.store_consumer", None)
        tampered_active = dict(active_for_stale)
        tampered_active["active"] = dict(active_for_stale["active"])
        tampered_active["active"]["checkpoint_sha256"] = "0" * 64
        store.set_state(
            "v14.world_jepa.store_consumer", tampered_active, expected=version
        )
        stale = read_world_planner_shadow(store, event["event_id"])
        assert stale["status"] == "STALE_CHECKPOINT"
        current_state, current_version = store.state(
            "v14.world_jepa.store_consumer", None
        )
        store.set_state(
            "v14.world_jepa.store_consumer", active_for_stale,
            expected=current_version,
        )

        event_row = store.one(
            "SELECT packet FROM events WHERE id=?", (event["event_id"],)
        )
        envelope = json.loads(event_row["packet"])
        envelope["source_ref"]["sha256"] = "0" * 64
        with store.tx() as connection:
            connection.execute(
                "UPDATE events SET packet=? WHERE id=?",
                (json.dumps(envelope, sort_keys=True), event["event_id"]),
            )
        revoked = read_world_planner_shadow(store, event["event_id"])
        assert revoked["status"] == "SOURCE_REVOKED_OR_CHANGED"
    finally:
        store.close()


def test_world_planner_receiver_rejects_uncommitted_or_source_mismatched_event(tmp_path):
    home = tmp_path / "brain-planner-negative"
    store, session = _make_store(home)
    try:
        event = store.event(session, "uncommitted action must not enter planner")
        missing = consume_world_planner_shadow(store, event["event_id"], home=home)
        assert missing["status"] == "NO_COMMITTED_OUTCOME"
        assert store.state(
            "v14.world_jepa.planner_shadow:" + event["event_id"], None
        )[0] is None

        text = "source binding negative control"
        second, _, _ = _make_committed_planner_action(store, session, text)
        row = store.one(
            "SELECT packet FROM events WHERE id=?", (second["event_id"],)
        )
        envelope = json.loads(row["packet"])
        envelope["source_ref"]["sha256"] = "0" * 64
        with store.tx() as connection:
            connection.execute(
                "UPDATE events SET packet=? WHERE id=?",
                (json.dumps(envelope, sort_keys=True), second["event_id"]),
            )
        rejected = consume_world_planner_shadow(store, second["event_id"], home=home)
        assert rejected["status"] == "SOURCE_OR_RECEIPT_REJECTED"
        assert store.state(
            "v14.world_jepa.planner_shadow:" + second["event_id"], None
        )[0] is None
    finally:
        store.close()


def test_world_planner_rejects_duplicate_action_outcome_beyond_first_32(tmp_path):
    home = tmp_path / "brain-planner-duplicate-overflow"
    store, session = _make_store(home)
    try:
        event, action_id, actual = _make_committed_planner_action(
            store, session, "planner duplicate receipt source"
        )
        event_id = event["event_id"]
        generation = event["brain_generation_id"]
        original = store.rows(
            "SELECT id FROM packets WHERE kind='ActionOutcome' "
            "AND event_id=? AND generation_id=?",
            (event_id, generation),
        )
        assert len(original) == 1

        duplicate = contracts.packet(
            "ActionOutcome", "C6_TEXT", event_id, generation,
            action_id=action_id, status="FINAL", actual=actual,
        )
        store.add_packet("ActionOutcome", duplicate)
        with store.tx() as connection:
            connection.execute(
                "UPDATE packets SET created=? WHERE id=?",
                (1000.0, original[0]["id"]),
            )
            connection.execute(
                "UPDATE packets SET created=? WHERE id=?",
                (1.0, duplicate["packet_id"]),
            )

        # The old LIMIT 32 query sees the original but misses this older
        # duplicate after 33 newer unrelated outcomes.
        for index in range(33):
            unrelated = contracts.packet(
                "ActionOutcome", "C6_TEXT", event_id, generation,
                action_id=f"unrelated-{index:03d}", status="FINAL",
                actual={"action_duration_s": 0.1, "characters": 1},
            )
            store.add_packet("ActionOutcome", unrelated)
            with store.tx() as connection:
                connection.execute(
                    "UPDATE packets SET created=? WHERE id=?",
                    (100.0 + index, unrelated["packet_id"]),
                )

        old_window = store.rows(
            "SELECT payload FROM packets WHERE kind='ActionOutcome' "
            "AND event_id=? AND generation_id=? ORDER BY created DESC LIMIT 32",
            (event_id, generation),
        )
        assert len(old_window) == 32
        assert sum(
            json.loads(row["payload"]).get("action_id") == action_id
            for row in old_window
        ) == 1

        rejected = consume_world_planner_shadow(store, event_id, home=home)
        assert rejected["status"] == "SOURCE_OR_RECEIPT_REJECTED"
        assert store.state(
            "v14.world_jepa.planner_shadow:" + event_id, None
        )[0] is None
    finally:
        store.close()


def test_world_planner_fails_closed_above_shared_action_outcome_bound(tmp_path):
    home = tmp_path / "brain-planner-overbound"
    store, session = _make_store(home)
    try:
        event, _, _ = _make_committed_planner_action(
            store, session, "planner overbound receipt source"
        )
        event_id = event["event_id"]
        generation = event["brain_generation_id"]
        rows = []
        for index in range(MAX_ACTION_OUTCOMES_PER_EVENT):
            packet = contracts.packet(
                "ActionOutcome", "C6_TEXT", event_id, generation,
                action_id=f"overbound-{index:04d}", status="FINAL",
                actual={"action_duration_s": 0.1, "characters": 1},
            )
            rows.append((
                packet["packet_id"], "ActionOutcome", event_id, generation,
                json.dumps(packet, sort_keys=True, separators=(",", ":")),
                float(index + 100),
            ))
        with store.tx() as connection:
            connection.executemany(
                "INSERT INTO packets VALUES (?,?,?,?,?,?)", rows
            )

        rejected = consume_world_planner_shadow(store, event_id, home=home)
        assert rejected["status"] == "SOURCE_OR_RECEIPT_REJECTED"
        assert store.state(
            "v14.world_jepa.planner_shadow:" + event_id, None
        )[0] is None
    finally:
        store.close()
