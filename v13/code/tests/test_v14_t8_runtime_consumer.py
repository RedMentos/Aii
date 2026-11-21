"""Runtime integration tests for the deployable V14 temporal/World shadow consumer."""
import json
import math
import sys
import time
import pytest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v13.runtime import Runtime
from v13.contracts import packet
from v13.v14_learning.runtime_shadow import (
    consume_recent_committed,
    online_world_shadow_prediction,
)
from v13.v14_learning.t8_temporal_bridge import TemporalT8Bridge


def _event_and_selection(runtime, text="source-bound shadow event", route="simple"):
    event = runtime.store.event(runtime.session, text)
    selected = packet(
        "ActionSelection", "C5_ACTION_GATE", event["event_id"], event["brain_generation_id"],
        [event["source_ref"]],
        selected={
            "action_id": "TEXT_REPORT", "action_type": "TEXT_REPORT", "score": 0.0,
            "permission_class": "local_text_only", "focal_support": 0.0,
        },
        candidates=[], suppressed=[], permission_class="local_text_only", route_hint=route,
    )
    runtime.store.add_packet("ActionSelection", selected)
    return event, selected


def _committed_action(runtime, *, status="FINAL", include_predictions=True, duplicate_outcome=False):
    event, selection = _event_and_selection(runtime)
    action_id = runtime.store.start_action(
        event["event_id"], event["brain_generation_id"],
        forecast={
            "input_chars": 96, "resource_state": "NORMAL",
            "profile": {"id": "profile-c3"}, "duration_median_s": 1.0,
        },
    )
    if include_predictions:
        self_prediction = packet(
            "SelfCorollary", "C2_SELF", event["event_id"], event["brain_generation_id"],
            [event["source_ref"]],
            action_id=action_id,
            issued_at=time.time(),
            intended_effect="TEXT_REPORT to user",
            predicted_observations=[{"channel": "action_status", "value": "FINAL"}],
            uncertainty=0.3,
            causal_hypothesis="local text report should finish",
            expected_cost={"duration_s": 1.0},
            permission_snapshot={"permission": "local_text_only", "external_tools": False},
        )
        runtime.store.add_packet("SelfCorollary", self_prediction)
        shadow = {
            "status": "SHADOW_ONLY", "decision_authority": "NONE",
            "calibration_status": "UNCALIBRATED", "model_seen": 12,
            "predicted_duration_s": math.expm1(0.0) + 1.0,
            "success_score_raw": 0.8, "success_score_clipped": 0.8,
            "predicted_output_chars": 72.0, "clipped": False,
        }
        prediction = {
            "role": "C3_LANGUAGE", "route_hint": "simple",
            "action_selection_packet_id": selection["packet_id"],
            "online_world_shadow": shadow,
        }
        runtime.store.add_packet(
            "ActionPrediction",
            packet(
                "ActionPrediction", "F4_FAST_FORWARD", event["event_id"], event["brain_generation_id"],
                [event["source_ref"]], action_type="TEXT_REPORT", profile_id="profile-c3",
                prediction=prediction,
            ),
        )
    actual = {"role": "C3_LANGUAGE", "action_duration_s": 1.2, "characters": 72}
    runtime.store.finish_action(action_id, status, actual)
    if duplicate_outcome:
        runtime.store.add_packet(
            "ActionOutcome",
            packet(
                "ActionOutcome", "C6_TEXT", event["event_id"], event["brain_generation_id"],
                [event["source_ref"]], action_id=action_id, status=status, actual=actual,
            ),
        )
    return event, action_id, actual


def test_online_world_prediction_is_a_non_authoritative_world_shadow(tmp_path):
    runtime = Runtime(Path(tmp_path))
    try:
        event, selection = _event_and_selection(runtime)
        class Predictor:
            seen = 12
            updates = 24
        class Online:
            model = Predictor()
            def predict(self, state, route):
                assert len(state) == 4
                assert route == "simple"
                return [1.0, 0.8, 0.5]
        runtime._online_world = Online()
        shadow = online_world_shadow_prediction(
            runtime, runtime.store, event, "C3_LANGUAGE", 96, empirical_duration_s=1.1
        )
        assert shadow["status"] == "SHADOW_ONLY"
        assert shadow["decision_authority"] == "NONE"
        assert shadow["calibration_status"] == "UNCALIBRATED"
        assert shadow["action_selection_packet_id"] == selection["packet_id"]
        assert shadow["predicted_duration_s"] == pytest.approx(math.expm1(1.0))
        assert shadow["success_score_raw"] == pytest.approx(0.8)
        assert shadow["empirical_duration_median_s"] == pytest.approx(1.1)
    finally:
        runtime.close()


def test_postcommit_consumer_records_temporal_and_world_outcomes_without_weight_updates(tmp_path):
    runtime = Runtime(Path(tmp_path))
    try:
        _event, action_id, _actual = _committed_action(runtime)
        result = consume_recent_committed(runtime.store, runtime.home, limit=16)
        assert result["status"] == "RECORDED"
        assert result["verified"] == 1
        assert result["temporal_recorded"] == 1
        assert result["world_outcomes_created"] == 1
        assert result["weight_updates"] == 0
        assert result["optimizer_permission"] is False
        assert runtime.cfg["learning_mode"] == "RECORD_ONLY"

        bridge = TemporalT8Bridge(Path(tmp_path) / "v14_temporal", learning_enabled=False)
        record = bridge.ledger.get(action_id)
        assert record is not None
        assert record["status"] == "OBSERVED"
        assert bridge.receiver.seen == []

        packets = runtime.store.rows(
            "SELECT id,payload FROM packets WHERE kind='WorldPredictionOutcome' ORDER BY created DESC LIMIT 8"
        )
        assert len(packets) == 1
        outcome = json.loads(packets[0]["payload"])
        assert outcome["action_id"] == action_id
        assert outcome["status"] == "SHADOW_ONLY"
        assert outcome["decision_authority"] == "NONE"
        assert outcome["calibration_status"] == "UNCALIBRATED"
        assert outcome["duration_error_s"] == pytest.approx(0.2)
        assert outcome["success_squared_error_clipped"] == pytest.approx(0.04)

        replay = consume_recent_committed(runtime.store, runtime.home, limit=16)
        assert replay["status"] == "NO_NEW_TRANSITIONS"
        packets_after = runtime.store.rows(
            "SELECT id FROM packets WHERE kind='WorldPredictionOutcome' ORDER BY created DESC LIMIT 8"
        )
        assert len(packets_after) == 1
    finally:
        runtime.close()


def test_duplicate_action_outcome_is_rejected_before_shadow_consumption(tmp_path):
    runtime = Runtime(Path(tmp_path))
    try:
        _event, action_id, _actual = _committed_action(runtime, duplicate_outcome=True)
        result = consume_recent_committed(runtime.store, runtime.home, limit=16)
        assert result["verified"] == 0
        assert result["rejected"] == 1
        assert result["temporal_recorded"] == 0
        assert result["world_outcomes_created"] == 0
        assert TemporalT8Bridge(Path(tmp_path) / "v14_temporal", learning_enabled=False).ledger.get(action_id) is None
        assert runtime.cfg["learning_mode"] == "RECORD_ONLY"
    finally:
        runtime.close()


def test_missing_online_world_and_censored_outcome_do_not_promote_learning(tmp_path):
    runtime = Runtime(Path(tmp_path))
    try:
        event, _selection = _event_and_selection(runtime)
        shadow = online_world_shadow_prediction(runtime, runtime.store, event, "C3_LANGUAGE", 96)
        assert shadow["status"] == "NOT_READY"
        _event, action_id, _actual = _committed_action(runtime, status="CANCELLED", include_predictions=True)
        result = consume_recent_committed(runtime.store, runtime.home, limit=16)
        assert result["temporal_recorded"] == 1
        record = TemporalT8Bridge(Path(tmp_path) / "v14_temporal", learning_enabled=False).ledger.get(action_id)
        assert record is not None
        assert record["status"] == "CANCELLED"
        assert record["prediction_error"] is None
        assert runtime.cfg["learning_mode"] == "RECORD_ONLY"
    finally:
        runtime.close()
