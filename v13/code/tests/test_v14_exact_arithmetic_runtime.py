"""End-to-end local arithmetic path through Runtime, C5, world outcome and C7/C6."""
from __future__ import annotations

import json
import time
from unittest.mock import Mock

from v13.runtime import Runtime
from v13.broker import decide, egress_type
from v13.output_policy import match


def _wait(runtime):
    until = time.monotonic() + 10
    while not runtime.idle() and time.monotonic() < until:
        time.sleep(0.005)
    assert runtime.idle(), "Runtime did not finish the bounded test turn"
    return runtime.last_answer()


def _packet(runtime, event_id, kind):
    row = runtime.store.one(
        "SELECT payload FROM packets WHERE event_id=? AND kind=? ORDER BY rowid DESC LIMIT 1",
        (event_id, kind),
    )
    return json.loads(row["payload"]) if row else None


def test_arithmetic_is_a_distinct_bounded_c5_action_not_a_fixed_rule(tmp_path):
    runtime = Runtime(tmp_path)
    try:
        runtime.sleep.cycle.set_policy("enabled", "off")
        assert match(runtime.store, "2+2") is None

        # Any accidental fall-through into perception, body inference or C3
        # generation fails this test rather than silently masking the fastpath.
        runtime._route = Mock(side_effect=AssertionError("arithmetic entered normal routing"))
        runtime.pool.get = Mock(side_effect=AssertionError("arithmetic loaded a native model"))
        runtime.cognition.percept = Mock(side_effect=AssertionError("arithmetic re-entered text perception"))
        runtime.cognition.offer = Mock(side_effect=AssertionError("arithmetic invoked B1/B2"))
        runtime.memory.recall = Mock(side_effect=AssertionError("arithmetic invoked optional recall"))
        runtime.learner.retrieve = Mock(side_effect=AssertionError("arithmetic invoked semantic retrieval"))

        event_id = runtime.submit("2+2")
        answer = _wait(runtime)
        assert answer["event_id"] == event_id
        assert answer["status"] == "FINAL"
        assert answer["text"] == "4"

        metadata = json.loads(answer["metadata"])
        assert metadata["model_generated"] is False
        assert metadata["output_authority"] == "LOCAL_EXACT_ARITHMETIC"
        assert metadata["direct_source_copy"] is False
        assert metadata["arithmetic_reflex"]["result"] == "4"
        assert metadata["arithmetic_reflex"]["operands"] == [2, 2]
        event_packet = json.loads(runtime.store.one("SELECT packet FROM events WHERE id=?", (event_id,))["packet"])
        assert metadata["arithmetic_reflex"]["source_ref"] == event_packet["source_ref"]

        selection = _packet(runtime, event_id, "ActionSelection")
        assert selection["selected"]["action_id"] == "LOCAL_EXACT_ARITHMETIC"
        assert selection["selected"]["action_type"] == "TEXT_REPORT"
        assert selection["selected"]["permission_class"] == "local_text_only"

        broker = _packet(runtime, event_id, "OutputBrokerDecision")
        assert broker["authority"] == "LOCAL_EXACT_ARITHMETIC"
        assert broker["egress_type"] == "TEXT_REPORT"
        assert broker["rewrites"] == 0

        egress = _packet(runtime, event_id, "EgressCheck")
        assert egress["action_type"] == "TEXT_REPORT"
        assert egress["ok"] is True

        action = runtime.store.one("SELECT status,outcome FROM actions WHERE event_id=?", (event_id,))
        outcome = json.loads(action["outcome"])
        assert action["status"] == "FINAL"
        assert outcome["role"] == "LOCAL_EXACT_ARITHMETIC"
        assert outcome["model_generated"] is False

        assert _packet(runtime, event_id, "PerceptPacket")["modality"] == "text"
        assert _packet(runtime, event_id, "ExperienceRecord")["outcome"] == "FINAL"
        assert _packet(runtime, event_id, "OutputPolicyDecision") is None
        assert runtime.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE event_id=? AND kind IN ('QueryPacket','OfferPacket')",
            (event_id,),
        )["n"] == 0
        assert runtime.store.integrity(True) == []

        runtime._route.assert_not_called()
        runtime.pool.get.assert_not_called()
        runtime.cognition.percept.assert_not_called()
        runtime.cognition.offer.assert_not_called()
        runtime.memory.recall.assert_not_called()
        runtime.learner.retrieve.assert_not_called()
    finally:
        runtime.close()


def test_local_arithmetic_authority_order_and_egress_are_not_exact_copy():
    assert decide(["MODEL_ANSWER", "LOCAL_EXACT_ARITHMETIC"])["selected"] == "LOCAL_EXACT_ARITHMETIC"
    assert decide(["APPROVED_FIXED_RULE", "LOCAL_EXACT_ARITHMETIC"])["selected"] == "APPROVED_FIXED_RULE"
    assert decide(["EXPLICIT_EXACT_COPY", "LOCAL_EXACT_ARITHMETIC"])["selected"] == "EXPLICIT_EXACT_COPY"
    assert egress_type("LOCAL_EXACT_ARITHMETIC") == "TEXT_REPORT"
    assert egress_type("EXPLICIT_EXACT_COPY") == "EXACT_RENDER"
