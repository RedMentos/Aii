import hashlib
import json
from unittest.mock import patch
from pathlib import Path
import pytest
from v13 import world_model
from temporal_outcomes import TemporalOutcomes, Expectation
from temporal_receiver import TemporalReadout
from t8_store_authority import verify_committed_transitions, VerifiedT8Transition
from t8_temporal_bridge import TemporalT8Bridge


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class FakeStore:
    def __init__(self, status="FINAL", actual=None, source_text="a synthetic user request"):
        self.source_text = source_text
        self.source_sha = hashlib.sha256(source_text.encode()).hexdigest()
        self.source_ref = {"source_id": "src-1", "sha256": self.source_sha, "char_start": 0,
                           "char_end": len(source_text), "modality": "text"}
        self.event = {"event_id": "evt-1", "brain_generation_id": "gen-1",
                      "source_ref": self.source_ref, "provenance": [self.source_ref]}
        self.expected = {"forecast": {"input_chars": len(source_text), "resource_state": "NORMAL"}}
        self.actual = actual or {"action_duration_s": 1.0, "characters": 20}
        self.status = status
        self.corollary = {"packet_id": "pkt-copy", "event_id": "evt-1", "brain_generation_id": "gen-1",
                          "action_id": "act-1", "expected": self.expected, "self_caused": True}
        self.outcome = {"packet_id": "pkt-out", "event_id": "evt-1", "brain_generation_id": "gen-1",
                        "action_id": "act-1", "status": status, "actual": self.actual}
        self.action = {"action_id": "act-1", "event_id": "evt-1", "status": status,
                       "expected": canonical(self.expected), "outcome": canonical(self.actual), "created": 100.0,
                       "corollary_id": "pkt-copy", "generation_id": "gen-1", "source_id": "src-1",
                       "event_packet": canonical(self.event), "corollary_kind": "CorollaryCopy",
                       "corollary_payload": canonical(self.corollary)}
        self.outcome_packets = [{"payload": canonical(self.outcome)}]

    def one(self, sql, args=()):
        if "FROM actions a" in sql:
            return dict(self.action)
        raise AssertionError("unexpected one query")

    def rows(self, sql, args=()):
        if "FROM packets" in sql and "ActionOutcome" in sql:
            return list(self.outcome_packets)
        raise AssertionError("unexpected rows query")

    def read_source(self, ref):
        if ref != self.source_ref or hashlib.sha256(self.source_text.encode()).hexdigest() != ref["sha256"]:
            raise ValueError("source hash mismatch")
        return self.source_text[ref["char_start"]:ref["char_end"]]


def transition(status="FINAL"):
    return {"action_id": "act-1", "s": [.2, .1, 0., 1.], "a": "simple",
            "y": [.69314718056, 1.0 if status == "FINAL" else 0.0, .3]}


def verified(store):
    with patch.object(world_model, "transitions", return_value=[transition(store.status)]):
        good, bad = verify_committed_transitions(store, limit=8)
    return good, bad


def test_store_authority_issues_receipt_without_exporting_raw_text():
    store = FakeStore()
    good, bad = verified(store)
    assert len(good) == 1 and bad == 0
    receipt = good[0]
    assert receipt.action_id == "act-1"
    assert receipt.public_provenance()["source_sha256"] == store.source_sha
    assert "synthetic user request" not in repr(receipt.public_provenance())
    assert receipt.training_row()["a"] == "simple"


def test_store_authority_rejects_source_tampering():
    store = FakeStore()
    store.source_ref["sha256"] = "0" * 64
    store.event["source_ref"] = store.source_ref
    store.event["provenance"] = [store.source_ref]
    store.action["event_packet"] = canonical(store.event)
    good, bad = verified(store)
    assert good == [] and bad == 1


def test_store_authority_rejects_mismatched_or_duplicate_action_outcome():
    store = FakeStore()
    altered = dict(store.outcome, actual={"action_duration_s": 2.0, "characters": 20})
    store.outcome_packets = [{"payload": canonical(altered)}]
    good, bad = verified(store)
    assert good == [] and bad == 1
    store = FakeStore()
    store.outcome_packets = [{"payload": canonical(store.outcome)}, {"payload": canonical(store.outcome)}]
    good, bad = verified(store)
    assert good == [] and bad == 1


def test_store_authority_rejects_duplicate_beyond_previous_seventeen_packet_window():
    store = FakeStore()
    packets = []
    for index in range(18):
        action_id = "act-1" if index == 0 else f"act-{index + 1}"
        payload = dict(store.outcome, action_id=action_id, packet_id=f"pkt-{index + 1}")
        packets.append({"payload": canonical(payload)})
    # The old LIMIT 17 saw the first valid packet but missed this older duplicate.
    packets.append({"payload": canonical(dict(store.outcome, packet_id="pkt-old-duplicate"))})
    store.outcome_packets = packets
    good, bad = verified(store)
    assert good == [] and bad == 1


def test_store_authority_rejects_event_history_over_hard_scan_bound():
    store = FakeStore()
    store.outcome_packets = [
        {"payload": canonical(dict(store.outcome, action_id=f"act-{index}", packet_id=f"pkt-{index}"))}
        for index in range(4097)
    ]
    good, bad = verified(store)
    assert good == [] and bad == 1


def test_known_failed_outcome_can_match_not_final_without_censoring(tmp_path):
    store = FakeStore(status="FAILED")
    good, rejected = verified(store)
    assert rejected == 0 and len(good) == 1
    bridge = TemporalT8Bridge(tmp_path / "known-failed")
    result = bridge.consume(good[0], {
        "expected_outcome": "NOT_FINAL", "probability": .8,
        "duration_s": 1.0, "tolerance_s": .25,
    })
    assert result["outcome"] == "OBSERVED"
    assert result["prediction_error"] == pytest.approx(.2)
    assert result["updated"] is False




class SQLiteRowStore(FakeStore):
    def __init__(self):
        import sqlite3
        super().__init__()
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row

    def _row(self, values):
        columns = list(values)
        query = "SELECT " + ", ".join("?" + " AS " + key for key in columns)
        return self.connection.execute(query, tuple(values[key] for key in columns)).fetchone()

    def one(self, sql, args=()):
        if "FROM actions a" in sql:
            return self._row(self.action)
        raise AssertionError("unexpected one query")

    def rows(self, sql, args=()):
        if "FROM packets" in sql and "ActionOutcome" in sql:
            return [self._row(row) for row in self.outcome_packets]
        raise AssertionError("unexpected rows query")


def test_store_authority_supports_real_sqlite_row_results():
    store = SQLiteRowStore()
    good, bad = verified(store)
    assert len(good) == 1 and bad == 0
    assert good[0].action_id == "act-1"
    store.connection.close()

def test_verified_receipt_cannot_be_constructed_without_private_issuer():
    with pytest.raises(TypeError):
        VerifiedT8Transition(object(), {}, None)


def test_temporal_bridge_records_outcome_but_does_not_learn_without_both_gates(tmp_path):
    store = FakeStore()
    good, _ = verified(store)
    bridge = TemporalT8Bridge(tmp_path, learning_enabled=False)
    prediction = {"expected_outcome": "FINAL", "probability": .8, "duration_s": 1.0, "tolerance_s": .25}
    pending = bridge.consume(good[0], prediction, optimizer_permission=False)
    assert pending["outcome"] == "OBSERVED"
    assert pending["prediction_error"] == pytest.approx(.2)
    assert pending["pending_optimizer"] is True
    assert bridge.receiver.seen == []


def test_temporal_bridge_updates_only_with_explicit_lab_and_optimizer_gates(tmp_path):
    store = FakeStore()
    good, _ = verified(store)
    bridge = TemporalT8Bridge(tmp_path, learning_enabled=True)
    prediction = {"expected_outcome": "FINAL", "probability": .8, "duration_s": 1.0, "tolerance_s": .25}
    no_permission = bridge.consume(good[0], prediction, optimizer_permission=False)
    assert no_permission["updated"] is False
    assert bridge.receiver.seen == []
    updated = bridge.consume(good[0], prediction, optimizer_permission=True)
    assert updated["updated"] is True
    assert bridge.receiver.seen == ["act-1"]
    assert updated["parameter_delta"]["WORLD"] > 0
    again = bridge.consume(good[0], prediction, optimizer_permission=True)
    assert again["duplicate"] is True
    assert bridge.receiver.seen == ["act-1"]


@pytest.mark.parametrize("status, expected_result", [
    ("CANCELLED", "CANCELLED"),
    ("ABORTED", "CANCELLED"),
    ("OUTCOME_UNKNOWN", "CENSORED"),
    ("INTERRUPTED", "CENSORED"),
])
@pytest.mark.parametrize("expected_label", ["FINAL", "NOT_FINAL"])
@pytest.mark.parametrize("learning_enabled", [False, True])
def test_cancelled_and_unknown_outcomes_never_create_learning_intent(
        tmp_path, status, expected_result, expected_label, learning_enabled):
    store = FakeStore(status=status)
    good, rejected = verified(store)
    assert rejected == 0 and len(good) == 1
    directory = tmp_path / f"{status}-{expected_label}-{learning_enabled}"
    prediction = {"expected_outcome": expected_label, "probability": .8,
                  "duration_s": 1.0, "tolerance_s": .25}
    bridge = TemporalT8Bridge(directory, learning_enabled=learning_enabled)
    result = bridge.consume(good[0], prediction, optimizer_permission=True)
    assert result["outcome"] == expected_result
    assert result["prediction_error"] is None
    assert result["updated"] is False
    assert bridge.receiver.seen == []
    assert bridge.receiver.weights == {"WORLD": 0.0, "B1": 0.0, "B2": 0.0}

    restarted = TemporalT8Bridge(directory, learning_enabled=learning_enabled)
    replay = restarted.consume(good[0], prediction, optimizer_permission=True)
    assert replay["outcome"] == expected_result
    assert replay["prediction_error"] is None
    assert replay["updated"] is False
    assert restarted.receiver.seen == []


def test_mismatch_and_late_outcome_are_negative_prediction_errors(tmp_path):
    store = FakeStore(status="FAILED")
    good, _ = verified(store)
    bridge = TemporalT8Bridge(tmp_path)
    mismatch = bridge.consume(good[0], {"expected_outcome": "FINAL", "probability": .8, "duration_s": 1.0, "tolerance_s": .25})
    assert mismatch["outcome"] == "MISMATCHED"
    assert mismatch["prediction_error"] == pytest.approx(-.8)
    store = FakeStore(actual={"action_duration_s": 4.0, "characters": 20})
    good, _ = verified(store)
    bridge2 = TemporalT8Bridge(Path(tmp_path) / "late")
    late = bridge2.consume(good[0], {"expected_outcome": "FINAL", "probability": .8, "duration_s": 1.0, "tolerance_s": .25})
    assert late["outcome"] == "DELAYED"
    assert late["prediction_error"] == pytest.approx(-.8)


def test_bridge_rejects_unverified_receipt_and_truthy_permission(tmp_path):
    bridge = TemporalT8Bridge(tmp_path, learning_enabled=True)
    with pytest.raises(PermissionError):
        bridge.consume({"action_id": "x"}, {"expected_outcome": "FINAL", "probability": .5, "duration_s": 1.})
    store = FakeStore()
    good, _ = verified(store)
    with pytest.raises(ValueError):
        bridge.consume(good[0], {"expected_outcome": "FINAL", "probability": .5, "duration_s": 1.}, optimizer_permission="yes")


def _process_expect(path, event_id):
    ledger = TemporalOutcomes(path)
    ledger.expect(Expectation(event_id, "T8:src:hash", "WORLD", "FINAL", 1., 1., 2., .7))


def _process_readout_update(path, event_id):
    readout = TemporalReadout(path, learning_enabled=True)
    intent = {"source": "T8:src:hash", "evidence": "T8:action:hash", "owner": "WORLD",
              "expected_outcome": "FINAL", "observed_outcome": "FINAL", "prediction_error": .5,
              "target": "WORLD_TEMPORAL", "requires_optimizer_permission": True}
    readout.update(intent, event_id, authorized=True)


def test_two_stale_ledger_instances_do_not_lose_either_committed_event(tmp_path):
    path = tmp_path / "shared.json"
    left = TemporalOutcomes(path)
    right = TemporalOutcomes(path)
    left.expect(Expectation("left", "T8:src:1", "WORLD", "FINAL", 1., 1., 2., .7))
    right.expect(Expectation("right", "T8:src:2", "WORLD", "FINAL", 1., 1., 2., .6))
    restored = TemporalOutcomes(path)
    assert set(restored.records) == {"left", "right"}


def test_two_stale_readout_instances_preserve_both_parameter_updates(tmp_path):
    path = tmp_path / "shared-readout.json"
    left = TemporalReadout(path, learning_enabled=True)
    right = TemporalReadout(path, learning_enabled=True)
    intent = {"source": "T8:src:hash", "evidence": "T8:action:hash", "owner": "WORLD",
              "expected_outcome": "FINAL", "observed_outcome": "FINAL", "prediction_error": .5,
              "target": "WORLD_TEMPORAL", "requires_optimizer_permission": True}
    left.update(intent, "left", authorized=True)
    right.update(intent, "right", authorized=True)
    restored = TemporalReadout(path, learning_enabled=True)
    assert set(restored.seen) == {"left", "right"}
    assert restored.weights["WORLD"] == pytest.approx(.1)


def test_multiprocess_ledger_writers_preserve_both_events(tmp_path):
    import multiprocessing
    path = str(tmp_path / "process-ledger.json")
    ctx = multiprocessing.get_context("fork")
    workers = [ctx.Process(target=_process_expect, args=(path, event_id)) for event_id in ("p1", "p2")]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(10)
    assert all(worker.exitcode == 0 for worker in workers)
    assert set(TemporalOutcomes(path).records) == {"p1", "p2"}


def test_multiprocess_readout_writers_preserve_both_updates(tmp_path):
    import multiprocessing
    path = str(tmp_path / "process-readout.json")
    ctx = multiprocessing.get_context("fork")
    workers = [ctx.Process(target=_process_readout_update, args=(path, event_id)) for event_id in ("p1", "p2")]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(10)
    assert all(worker.exitcode == 0 for worker in workers)
    restored = TemporalReadout(path, learning_enabled=True)
    assert set(restored.seen) == {"p1", "p2"}
    assert restored.weights["WORLD"] == pytest.approx(.1)


def test_two_stale_bridge_instances_consume_one_receipt_exactly_once(tmp_path):
    store = FakeStore()
    good, _ = verified(store)
    first = TemporalT8Bridge(tmp_path, learning_enabled=True)
    second = TemporalT8Bridge(tmp_path, learning_enabled=True)
    prediction = {"expected_outcome": "FINAL", "probability": .8, "duration_s": 1.0, "tolerance_s": .25}
    one = first.consume(good[0], prediction, optimizer_permission=True)
    two = second.consume(good[0], prediction, optimizer_permission=True)
    assert one["updated"] is True
    assert two["duplicate"] is True
    restored = TemporalT8Bridge(tmp_path, learning_enabled=True)
    assert restored.receiver.has_seen("act-1")
    assert restored.receiver.weights["WORLD"] == pytest.approx(.02)
