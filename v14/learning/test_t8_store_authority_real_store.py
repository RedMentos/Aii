"""Real SQLite Store integration for the V14 T8 source authority.

Uses the actual V13 Runtime/Store/ActionSelection/CorollaryCopy/ActionOutcome path.
No model inference or learning permission is enabled by this test.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V13_CODE = ROOT / "v13" / "code"
if str(V13_CODE) not in sys.path:
    sys.path.insert(0, str(V13_CODE))

from v13.runtime import Runtime
from v13.contracts import packet
from v13 import world_model as WM
from t8_store_authority import verify_committed_transitions
from t8_temporal_bridge import TemporalT8Bridge


def test_real_store_source_and_action_outcome_binding(tmp_path):
    runtime = Runtime(Path(tmp_path))
    try:
        runtime.sleep.cycle.set_policy("enabled", "off")
        assert runtime.cfg["learning_mode"] == "RECORD_ONLY"
        created = []
        for i in range(8):
            route = WM.ACTIONS[i % len(WM.ACTIONS)]
            event = runtime.store.event(runtime.session, "Synthetic source-bound route observation " + str(i))
            runtime.store.add_packet("ActionSelection", packet(
                "ActionSelection", "C5_ACTION_GATE", event["event_id"], event["brain_generation_id"],
                [event["source_ref"]],
                selected={"action_id": "TEXT_REPORT", "action_type": "TEXT_REPORT", "score": 0.0,
                          "permission_class": "local_text_only", "focal_support": 0.0},
                candidates=[], suppressed=[], permission_class="local_text_only", route_hint=route))
            forecast = {"input_chars": 100 + 5 * i, "resource_state": "NORMAL"}
            action_id = runtime.store.start_action(event["event_id"], event["brain_generation_id"], forecast=forecast)
            actual = {"action_duration_s": 1.0 + i / 100, "characters": 80 + 2 * i}
            runtime.store.finish_action(action_id, "FINAL", actual)
            created.append((event, action_id, actual))

        verified, rejected = verify_committed_transitions(runtime.store, limit=32)
        assert len(verified) == 8
        assert rejected == 0
        assert {r.action_id for r in verified} == {x[1] for x in created}
        for receipt in verified:
            assert receipt.status == "FINAL"
            assert receipt.source_ref["source_id"]
            assert len(receipt.source_ref["sha256"]) == 64
            assert receipt.actual["action_duration_s"] >= 1.0
            assert "Synthetic source-bound" not in repr(receipt.public_provenance())

        # Exercise the real Store-issued receipt through the V14 temporal ledger.
        # The optimizer gate remains closed: this records an outcome, not a weight update.
        bridge = TemporalT8Bridge(Path(tmp_path) / "temporal-bridge", learning_enabled=False)
        prediction = {"expected_outcome": "FINAL", "probability": .8,
                      "duration_s": 1.0, "tolerance_s": .25}
        pending = bridge.consume(verified[0], prediction, optimizer_permission=False)
        assert pending["outcome"] == "OBSERVED"
        assert pending["pending_optimizer"] is True
        assert bridge.receiver.seen == []
        replayed = bridge.consume(verified[0], prediction, optimizer_permission=False)
        assert replayed["outcome"] == "OBSERVED"
        assert bridge.receiver.seen == []

        # Negative control: a second ActionOutcome for the same action must not
        # be silently selected as truth; the authority rejects that action.
        event, action_id, actual = created[-1]
        runtime.store.add_packet("ActionOutcome", packet(
            "ActionOutcome", "C6_TEXT", event["event_id"], event["brain_generation_id"],
            [event["source_ref"]], action_id=action_id, status="FINAL", actual=actual))
        verified_after_duplicate, rejected_after_duplicate = verify_committed_transitions(runtime.store, limit=32)
        assert len(verified_after_duplicate) == 7
        assert rejected_after_duplicate == 1
        assert runtime.cfg["learning_mode"] == "RECORD_ONLY"
    finally:
        runtime.close()
