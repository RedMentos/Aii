"""Same-turn B1/B2 -> C4 -> C3 consumer proof with C3 recovery evidence.

Native model outputs are deterministic synthetic stubs. The test exercises the
real Runtime, SQLite Store, Cognition, FocalLoop, source validation and C3
prompt assembly; it does not claim native GGUF or Redmi execution.
"""
import json
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from v13.native_turn_budget import recent_proof, zero_token_prefill_failure
from v13.brain_panel import status as brain_status
from v13.native_offer_prompt_receipt import inspect as inspect_native_offer_prompt
from v13.operator import Operator
from v13.runtime import Runtime


QUESTION = (
    "Compare the exact rent detail with the broader plan. "
    "The rent is 120 euros. The plan preserves a long-term reserve."
)
B1_SUMMARY = "Detail finding: monthly rent is fixed at 120 euros."
B2_SUMMARY = "Gist finding: the long-term reserve remains protected."


def wait_for_answer(runtime, timeout=15):
    until = time.monotonic() + timeout
    while not runtime.idle() and time.monotonic() < until:
        time.sleep(0.005)
    assert runtime.idle(), "synthetic Runtime turn did not settle"
    return runtime.last_answer()


def packet_rows(runtime, event_id, kind):
    rows = runtime.store.rows(
        "SELECT payload FROM packets WHERE event_id=? AND kind=? ORDER BY rowid",
        (event_id, kind),
    )
    return [json.loads(row["payload"]) for row in rows]


class SyntheticRunner:
    def __init__(self, role, seen):
        self.role = role
        self.seen = seen
        self.last_metrics = {
            "role": role,
            "status": "FINAL",
            "generated_tokens": 8,
            "prompt_tokens": 32,
            "last_phase": "stream",
            "duration_s": 0.01,
            "synthetic": True,
        }

    def generate(self, messages, cancel, deadline, *args, **kwargs):
        if self.role == "C3_LANGUAGE":
            self.seen[self.role] = [dict(message) for message in messages]
            rendered_prompt = "\n".join(
                message.get("content", "") for message in messages
            )
            witness = inspect_native_offer_prompt(
                messages, rendered_prompt, "Internal hypotheses: "
            )
            self.last_metrics["native_offer_prompt_receipt"] = {
                **witness,
                "native_completion_http_200": False,
                "native_template_submitted": False,
                "synthetic_template_submitted": witness.get("status") == "RENDERED_WITH_QUOTES",
                "native_attention_or_semantic_use_proven": False,
                "synthetic": True,
            }
            yield (
                "The rent is fixed at 120 euros, and the long-term reserve "
                "remains protected."
            )
            return

        if self.role == "B1_DETAIL":
            payload = {
                "summary": B1_SUMMARY,
                "quotes": ["The rent is 120 euros."],
                "uncertainty": "low",
                "needs_reentry": False,
            }
        elif self.role == "B2_GIST":
            payload = {
                "summary": B2_SUMMARY,
                "quotes": ["The plan preserves a long-term reserve."],
                "uncertainty": "low",
                "needs_reentry": False,
            }
        else:
            raise AssertionError("unexpected native role: " + self.role)

        self.seen[self.role] = [dict(message) for message in messages]
        yield json.dumps(payload, ensure_ascii=False)


def test_two_recent_c3_prefill_failures_still_reach_same_turn_c4_and_c3(tmp_path):
    runtime = Runtime(Path(tmp_path) / "private-home")
    seen = {}
    try:
        runtime.sleep.cycle.set_policy("enabled", "off")
        runtime.cfg.update(
            deadline_seconds=30,
            observer_seconds=5,
            observer_mode="background",
            observer_schedule="A_THEN_B_SEQUENTIAL",
            observer_sample_rate=1.0,
            b2_quote_select="off",
            offer_quote_context_chars=0,
            b2_state_slots=0,
        )
        Operator(runtime).run(":effort max")
        runtime._route = Mock(
            return_value=("both", {"source": "SYNTHETIC_CORE_E2E"})
        )

        # Seed only bounded, content-free assistant failure metadata. The
        # current turn's DRAFT assistant row is not eligible recovery evidence.
        failure_metadata = {
            "runner": {
                "role": "C3_LANGUAGE",
                "generated_tokens": 0,
                "last_phase": "prefill",
                "duration_s": 29.1,
            }
        }
        for _ in range(2):
            runtime.store.message(
                runtime.session,
                None,
                "assistant",
                status="DEADLINE",
                metadata=failure_metadata,
            )
        proof = recent_proof(runtime.store)
        assert sum(zero_token_prefill_failure(row) for row in proof) == 2

        runners = {
            role: SyntheticRunner(role, seen)
            for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
        }
        runtime.pool.get = Mock(side_effect=lambda role: runners[role])

        event_id = runtime.submit(QUESTION)
        answer = wait_for_answer(runtime)
        assert answer["event_id"] == event_id
        assert answer["status"] == "FINAL"
        assert "120 euros" in answer["text"]
        assert "reserve" in answer["text"].lower()

        # Native-generation boundaries are not enough: both persisted body
        # offers must be members of the actual same-turn C4 coalition.
        offers = packet_rows(runtime, event_id, "OfferPacket")
        receipts = runtime.store.rows(
            "SELECT metrics FROM telemetry "
            "WHERE event_id=? AND kind='c4_offer_context_ready' ORDER BY id",
            (event_id,),
        )
        assert len(receipts) == 1
        receipt = json.loads(receipts[0]["metrics"])
        selected_ids = set(receipt["selected_offer_ids"])
        body_offers = {
            offer["role"]: offer
            for offer in offers
            if offer["packet_id"] in selected_ids
            and offer["role"] in {"B1_DETAIL", "B2_GIST"}
        }
        assert set(body_offers) == {"B1_DETAIL", "B2_GIST"}

        focal_items = packet_rows(runtime, event_id, "FocalItem")
        active_body_items = [
            item for item in focal_items
            if item.get("source_kind") in {"B1_DETAIL", "B2_GIST"}
            and item.get("origin_event_id") == event_id
        ]
        assert {item["source_kind"] for item in active_body_items} == {
            "B1_DETAIL", "B2_GIST"
        }

        cycles = packet_rows(runtime, event_id, "FocalCycle")
        coalition_ids = {
            item_id
            for cycle in cycles
            for item_id in cycle.get("coalition", [])
        }
        assert {item["item_id"] for item in active_body_items} <= coalition_ids

        # The summaries are deliberately not substrings of the user source.
        # Their presence in the C3 system prompt therefore proves that the
        # selected body hypotheses crossed the real C4 -> C3 context path.
        c3_messages = seen["C3_LANGUAGE"]
        c3_system = "\n".join(
            message.get("content", "")
            for message in c3_messages
            if message.get("role") == "system"
        )
        assert B1_SUMMARY in c3_system
        assert B2_SUMMARY in c3_system

        # :brain status reports the exact synthetic offer IDs that crossed
        # the C4 receipt and were rendered into the C3 template, without
        # exposing prompt text or claiming native execution/semantic use.
        latest = brain_status(runtime)["latest_turn"]
        assert latest["turn_status"] == "FINAL"
        assert latest["runner_role"] == "C3_LANGUAGE"
        assert latest["evidence_environment"] == "SYNTHETIC"
        assert latest["prompt_tokens"] == 32
        assert latest["generated_tokens"] == 8
        assert latest["offer_flow"]["status"] == "SYNTHETIC_TEMPLATE_SUBMITTED_MATCHED_C4"
        assert latest["offer_flow"]["native_template_submitted"] is False
        assert latest["offer_flow"]["template_submitted"] is True
        assert latest["offer_flow"]["native_completion_http_200"] is False
        assert latest["offer_flow"]["c4_native_offer_ids_match"] is True
        assert {item["role"] for item in latest["offer_flow"]["offers"]} == {
            "B1_DETAIL", "B2_GIST"
        }
        assert latest["offer_flow"]["semantic_use_proven"] is False

        assert receipt["role"] == "C3_LANGUAGE"
        assert receipt["status"] == "PASS"
        assert receipt["count"] == 2
        assert set(receipt["selected_offer_ids"]) == {
            body_offers["B1_DETAIL"]["packet_id"],
            body_offers["B2_GIST"]["packet_id"],
        }

        deferred = runtime.store.rows(
            "SELECT metrics FROM telemetry "
            "WHERE event_id=? AND kind='native_body_deferred_for_c3'",
            (event_id,),
        )
        assert deferred == []

        # Negative control: a modified selected offer must fail the persisted
        # OfferPacket binding and must not create another C4 -> C3 receipt.
        event_row = runtime.store.one(
            "SELECT packet FROM events WHERE id=?", (event_id,)
        )
        event = json.loads(event_row["packet"])
        selected_offer = dict(body_offers["B1_DETAIL"])
        selected_offer["offer"] = dict(
            selected_offer["offer"], summary="tampered after C4 selection"
        )
        query_row = runtime.store.one(
            "SELECT payload FROM packets "
            "WHERE event_id=? AND kind='QueryPacket' "
            "AND json_extract(payload,'$.target_role')='B1_DETAIL' "
            "ORDER BY rowid LIMIT 1",
            (event_id,),
        )
        version = json.loads(query_row["payload"])["based_on_state_version"]
        with pytest.raises(ValueError, match="Consumer offer binding changed or expired"):
            runtime.cognition.analyst_context([selected_offer], event, version)
        after_negative = runtime.store.rows(
            "SELECT metrics FROM telemetry "
            "WHERE event_id=? AND kind='c4_offer_context_ready'",
            (event_id,),
        )
        assert len(after_negative) == 1
        assert runtime.store.integrity(True) == []
    finally:
        runtime.close()


class _EvidenceStore:
    def __init__(self, message, telemetry=None):
        self.message = message
        self.telemetry = telemetry

    def one(self, sql, args=()):
        if "FROM messages" in sql:
            return self.message
        if "FROM telemetry" in sql:
            return self.telemetry
        raise AssertionError("unexpected evidence query")


def test_brain_status_refuses_mismatched_c4_and_native_offer_ids():
    from types import SimpleNamespace

    metadata = {
        "runner": {
            "role": "C3_LANGUAGE",
            "synthetic": True,
            "native_offer_prompt_receipt": {
                "status": "RENDERED_WITH_QUOTES",
                "synthetic": True,
                "synthetic_template_submitted": True,
                "offers": [
                    {"role": "B1_DETAIL", "packet_id": "offer-1", "rendered_quote_count": 1},
                    {"role": "B2_GIST", "packet_id": "offer-2", "rendered_quote_count": 1},
                ],
            },
        }
    }
    message = {"event_id": "event-1", "status": "FINAL", "metadata": json.dumps(metadata)}
    telemetry = {"metrics": json.dumps({
        "status": "PASS", "count": 2, "selected_offer_ids": ["offer-1", "tampered"]
    })}
    runtime = SimpleNamespace(
        cfg={}, current=None, store=_EvidenceStore(message, telemetry)
    )
    flow = brain_status(runtime)["latest_turn"]["offer_flow"]
    assert flow["status"] == "SYNTHETIC_TEMPLATE_SUBMITTED_C4_ID_MISMATCH"
    assert flow["c4_native_offer_ids_match"] is False
    assert flow["semantic_use_proven"] is False


def test_brain_status_marks_missing_native_offer_receipt():
    from types import SimpleNamespace

    message = {
        "event_id": "event-2", "status": "DEADLINE",
        "metadata": json.dumps({"runner": {
            "role": "C3_LANGUAGE", "prompt_tokens": 0, "generated_tokens": 0
        }}),
    }
    runtime = SimpleNamespace(cfg={}, current=None, store=_EvidenceStore(message))
    latest = brain_status(runtime)["latest_turn"]
    assert latest["offer_flow"]["status"] == "OFFER_RECEIPT_UNAVAILABLE"
    assert latest["offer_flow"]["semantic_use_proven"] is False
