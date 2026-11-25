import json
import time
from pathlib import Path
from types import SimpleNamespace

from v13 import brain_panel
from v13.contracts import packet
from v13.store import Store


def _id(prefix, char):
    return prefix + "_" + char * 32


class FakeStore:
    def __init__(self, message, c4_metrics=None, body_rows=()):
        self.message = message
        self.c4_metrics = c4_metrics
        self.body_rows = list(body_rows)
        self.event_id = message.get("event_id")
        self.event_generation_id = "gen_" + "1" * 32
        self.packet_rows = {}
        self.source_refs = {}
        for row in self.body_rows:
            if row.get("kind") != "body_offer_delivered":
                continue
            metrics = json.loads(row["metrics"])
            packet_id = metrics["packet_id"]
            source_ref = {
                "source_id": "src_" + packet_id.split("_", 1)[1],
                "sha256": "c" * 64,
                "char_start": 0,
                "char_end": 1,
                "modality": "text",
            }
            payload = {
                "packet_id": packet_id,
                "event_id": self.event_id,
                "brain_generation_id": self.event_generation_id,
                "producer_component": metrics["role"],
                "role": metrics["role"],
                "query_packet_id": metrics["query_packet_id"],
                "evidence_refs": [source_ref],
                "provenance": [source_ref],
            }
            self.packet_rows[packet_id] = {
                "kind": "OfferPacket",
                "event_id": self.event_id,
                "generation_id": self.event_generation_id,
                "payload": json.dumps(payload),
            }
            self.source_refs[source_ref["source_id"]] = source_ref

    def one(self, sql, args=()):
        if "FROM messages" in sql:
            return self.message
        if "FROM events" in sql:
            return ({"generation_id": self.event_generation_id}
                    if args and args[0] == self.event_id else None)
        if "FROM packets" in sql:
            return self.packet_rows.get(args[0]) if args else None
        if "c4_offer_context_ready" in sql:
            return {"metrics": json.dumps(self.c4_metrics)} if self.c4_metrics is not None else None
        raise AssertionError("unexpected Store.one query")

    def read_source(self, ref):
        registered = self.source_refs.get(ref.get("source_id"))
        if registered != ref:
            raise ValueError("source ref is missing, deleted or changed")
        return "x"

    def rows(self, sql, args=()):
        if "body_offer_attempt" not in sql or "body_offer_delivered" not in sql:
            raise AssertionError("unexpected Store.rows query")
        return self.body_rows


def _runtime(*, status="FINAL", receipt=None, c4=None, body_rows=(), runner_extra=None):
    event_id = _id("evt", "e")
    runner = {
        "role": "C3_LANGUAGE",
        "prompt_tokens": 173,
        "generated_tokens": 12,
        "ttft_s": 0.7,
        "duration_s": 2.1,
        "sampled_peak_pss_bytes": 1234567,
    }
    runner.update(runner_extra or {})
    if receipt is not None:
        runner["native_offer_prompt_receipt"] = receipt
    message = {
        "event_id": event_id,
        "status": status,
        "metadata": json.dumps({"runner": runner, "model_revision": "c3-rev-1"}),
    }
    return type("RuntimeStub", (), {
        "store": FakeStore(message, c4, body_rows)
    })()


def _native_receipt(packet_id):
    return {
        "status": "RENDERED_WITH_QUOTES",
        "native_template_submitted": True,
        "native_prompt_sha256": "a" * 64,
        "native_token_ids_sha256": "b" * 64,
        "native_prompt_tokens": 173,
        "native_tokenizer": "LLAMA_SERVER_TOKENIZE",
        "native_prefill_observed": True,
        "native_prompt_prefill_verified": False,
        "native_stream_completed": True,
        "native_generation_completed": True,
        "offers": [{
            "role": "B1_DETAIL",
            "packet_id": packet_id,
            "rendered_quote_count": 1,
        }],
    }


def _body_rows(role, query_id, *, packet_id=None, prompt_tokens=143,
               generated_tokens=21, status="FINAL", synthetic=False):
    attempt = {
        "role": role,
        "query_packet_id": query_id,
        "status": status,
        "runner": {
            "prompt_tokens": prompt_tokens,
            "generated_tokens": generated_tokens,
            "ttft_s": 0.42 if generated_tokens else None,
            "duration_s": 1.8,
            "sampled_peak_pss_bytes": 987654,
            "synthetic": synthetic,
            "private_prompt": "PRIVATE PROMPT MUST NOT BE RETURNED",
        },
    }
    rows = [{"kind": "body_offer_attempt", "metrics": json.dumps(attempt)}]
    if packet_id is not None:
        delivered = {
            "role": role,
            "query_packet_id": query_id,
            "packet_id": packet_id,
            "count": 1,
            "duration_s": 1.9,
            "private_summary": "PRIVATE HYPOTHESIS MUST NOT BE RETURNED",
        }
        rows.append({"kind": "body_offer_delivered", "metrics": json.dumps(delivered)})
    return rows


def test_b1_attempt_is_joined_to_c4_and_native_c3_prefill_without_claiming_semantics():
    query_id, packet_id = _id("pkt", "a"), _id("pkt", "b")
    runtime = _runtime(
        receipt=_native_receipt(packet_id),
        c4={
            "status": "PASS",
            "role": "C3_LANGUAGE",
            "selected_offer_ids": [packet_id],
            "count": 1,
        },
        body_rows=_body_rows("B1_DETAIL", query_id, packet_id=packet_id),
    )

    latest = brain_panel._latest_native_evidence(runtime)
    flow = latest["offer_flow"]
    assert latest["prompt_tokens"] == 173
    assert flow["native_prefill_observed"] is True
    assert flow["native_prompt_prefill_verified"] is False
    assert flow["native_generation_completed"] is True
    assert flow["c4_native_offer_ids_match"] is True

    assert len(flow["body_attempts"]) == 1
    body = flow["body_attempts"][0]
    assert body["role"] == "B1_DETAIL"
    assert body["attempt_status"] == "FINAL"
    assert body["prompt_tokens"] == 143
    assert body["generated_tokens"] == 21
    assert body["ttft_s"] == 0.42
    assert body["sampled_peak_pss_bytes"] == 987654
    assert body["delivered"] is True
    assert body["offer_packet_verified"] is True
    assert body["source_bound"] is True
    assert body["source_count_matches"] is True
    assert body["reported_source_span_count"] == 1
    assert body["verified_source_span_count"] == 1
    assert body["selected_by_c4"] is True
    assert body["included_in_c3_template"] is True
    assert body["native_prefill_observed"] is True
    assert body["native_prefill_verified"] is False
    assert body["native_generation_completed"] is True
    assert body["consumption_state"] == (
        "C4_SELECTED_C3_NATIVE_PREFILL_OBSERVED_AND_GENERATION_COMPLETED"
    )
    assert body["semantic_use_proven"] is False
    assert "PRIVATE PROMPT" not in repr(latest)
    assert "PRIVATE HYPOTHESIS" not in repr(latest)


def test_zero_token_b2_deadline_is_visible_without_inventing_delivery():
    query_id = _id("pkt", "c")
    runtime = _runtime(
        status="DEADLINE",
        body_rows=_body_rows(
            "B2_GIST", query_id, prompt_tokens=608, generated_tokens=0,
            status="DEADLINE",
        ),
    )
    latest = brain_panel._latest_native_evidence(runtime)
    body = latest["offer_flow"]["body_attempts"][0]
    assert body["role"] == "B2_GIST"
    assert body["attempt_status"] == "DEADLINE"
    assert body["prompt_tokens"] == 608
    assert body["generated_tokens"] == 0
    assert body["delivered"] is False
    assert body["selected_by_c4"] is None
    assert body["consumption_state"] == "ATTEMPT_NOT_DELIVERED"


def test_synthetic_path_remains_synthetic_even_with_matching_ids_and_receipts():
    query_id, packet_id = _id("pkt", "d"), _id("pkt", "f")
    receipt = _native_receipt(packet_id)
    receipt.update({
        "synthetic": True,
        "native_template_submitted": False,
        "synthetic_template_submitted": True,
        "synthetic_prompt_prefill_verified": True,
        "synthetic_generation_completed": True,
    })
    runtime = _runtime(
        receipt=receipt,
        c4={
            "status": "PASS",
            "role": "C3_LANGUAGE",
            "selected_offer_ids": [packet_id],
            "count": 1,
        },
        body_rows=_body_rows(
            "B1_DETAIL", query_id, packet_id=packet_id, synthetic=True,
        ),
    )
    latest = brain_panel._latest_native_evidence(runtime)
    body = latest["offer_flow"]["body_attempts"][0]
    assert latest["offer_flow"]["status"] == "SYNTHETIC_PREFILL_AND_GENERATION_VERIFIED_MATCHED_C4"
    assert body["evidence_environment"] == "SYNTHETIC"
    assert body["consumption_state"] == "SYNTHETIC_PREFILL_AND_GENERATION_VERIFIED"
    assert body["native_prefill_observed"] is False
    assert body["native_generation_completed"] is False
    assert "NATIVE" not in body["consumption_state"]


def test_delivered_offer_not_selected_by_c4_is_not_reported_as_consumed():
    query_id, packet_id = _id("pkt", "1"), _id("pkt", "2")
    runtime = _runtime(
        receipt=_native_receipt(packet_id),
        c4={
            "status": "PASS",
            "role": "C3_LANGUAGE",
            "selected_offer_ids": [],
            "count": 0,
        },
        body_rows=_body_rows("B1_DETAIL", query_id, packet_id=packet_id),
    )
    body = brain_panel._latest_native_evidence(runtime)["offer_flow"]["body_attempts"][0]
    assert body["selected_by_c4"] is False
    assert body["consumption_state"] == "DELIVERED_NOT_SELECTED_BY_C4"


def test_missing_c4_receipt_and_malformed_telemetry_fail_closed():
    query_id, packet_id = _id("pkt", "3"), _id("pkt", "4")
    rows = _body_rows("B2_GIST", query_id, packet_id=packet_id)
    rows.append({"kind": "body_offer_attempt", "metrics": "not-json"})
    runtime = _runtime(receipt=_native_receipt(packet_id), c4=None, body_rows=rows)
    body = brain_panel._latest_native_evidence(runtime)["offer_flow"]["body_attempts"][0]
    assert body["consumption_state"] == "C4_RECEIPT_UNAVAILABLE"

    runtime = _runtime(
        receipt=_native_receipt(packet_id),
        c4=None,
        body_rows=[{"kind": "body_offer_attempt", "metrics": "not-json"}],
    )
    assert brain_panel._latest_native_evidence(runtime)["offer_flow"]["body_attempts"] == []


def test_body_telemetry_is_bounded_and_invalid_store_shapes_fail_closed():
    event_id = _id("evt", "e")
    rows = []
    for index in range(17):
        query_id = "pkt_" + format(index, "032x")[-32:]
        rows.append({
            "kind": "body_offer_attempt",
            "metrics": json.dumps({
                "role": "B1_DETAIL" if index % 2 == 0 else "B2_GIST",
                "query_packet_id": query_id,
                "status": "FINAL",
                "runner": {"prompt_tokens": index + 1, "generated_tokens": 1},
            }),
        })
    runtime = _runtime(body_rows=rows)
    attempts = brain_panel._latest_native_evidence(runtime)["offer_flow"]["body_attempts"]
    assert len(attempts) == 16
    assert attempts[0]["telemetry_truncated"] is True
    assert all(item["telemetry_truncated"] is True for item in attempts)
    assert all("private_prompt" not in item for item in attempts)

    class RaisingStore:
        def rows(self, sql, args=()):
            raise RuntimeError("private store failure")

    assert brain_panel._body_offer_evidence(RaisingStore(), event_id) == []
    assert brain_panel._body_offer_evidence(RaisingStore(), None) == []


def test_missing_body_environment_marker_stays_unverified_even_with_native_c3_receipt():
    query_id, packet_id = _id("pkt", "9"), _id("pkt", "a")
    rows = _body_rows("B1_DETAIL", query_id, packet_id=packet_id)
    attempt = json.loads(rows[0]["metrics"])
    # Store.telemetry_metrics currently drops the nested synthetic marker.
    # A missing marker must not be promoted to a native body execution claim.
    attempt["runner"].pop("synthetic", None)
    rows[0]["metrics"] = json.dumps(attempt)
    runtime = _runtime(
        receipt=_native_receipt(packet_id),
        c4={
            "status": "PASS",
            "role": "C3_LANGUAGE",
            "selected_offer_ids": [packet_id],
            "count": 1,
        },
        body_rows=rows,
    )
    body = brain_panel._latest_native_evidence(runtime)["offer_flow"]["body_attempts"][0]
    assert body["evidence_environment"] == "UNVERIFIED"
    assert body["native_prefill_observed"] is True
    assert body["native_generation_completed"] is True
    assert body["consumption_state"] == "BODY_ATTEMPT_ENVIRONMENT_UNVERIFIED"
    assert body["semantic_use_proven"] is False


def test_b1_and_b2_sharing_one_query_packet_keep_both_consumption_records():
    query_id, b1_packet, b2_packet = _id("pkt", "a"), _id("pkt", "b"), _id("pkt", "c")
    receipt = _native_receipt(b1_packet)
    receipt["offers"] = [
        {"role": "B1_DETAIL", "packet_id": b1_packet, "rendered_quote_count": 1},
        {"role": "B2_GIST", "packet_id": b2_packet, "rendered_quote_count": 1},
    ]
    runtime = _runtime(
        receipt=receipt,
        c4={
            "status": "PASS",
            "role": "C3_LANGUAGE",
            "selected_offer_ids": [b1_packet, b2_packet],
            "count": 2,
        },
        body_rows=(
            _body_rows("B1_DETAIL", query_id, packet_id=b1_packet)
            + _body_rows("B2_GIST", query_id, packet_id=b2_packet)
        ),
    )

    latest = brain_panel._latest_native_evidence(runtime)
    flow = latest["offer_flow"]
    assert flow["c4_native_offer_ids_match"] is True
    assert len(flow["body_attempts"]) == 2
    by_role = {item["role"]: item for item in flow["body_attempts"]}
    assert set(by_role) == {"B1_DETAIL", "B2_GIST"}

    for role, packet_id in (
        ("B1_DETAIL", b1_packet),
        ("B2_GIST", b2_packet),
    ):
        body = by_role[role]
        assert body["query_packet_id"] == query_id
        assert body["packet_id"] == packet_id
        assert body["delivered"] is True
        assert body["selected_by_c4"] is True
        assert body["included_in_c3_template"] is True
        assert body["consumption_state"] == (
            "C4_SELECTED_C3_NATIVE_PREFILL_OBSERVED_AND_GENERATION_COMPLETED"
        )
        assert body["semantic_use_proven"] is False

    assert "PRIVATE PROMPT" not in repr(latest)
    assert "PRIVATE HYPOTHESIS" not in repr(latest)


def test_duplicate_or_malformed_c4_and_template_ids_do_not_match():
    query_id, packet_id = _id("pkt", "7"), _id("pkt", "8")
    runtime = _runtime(
        receipt=_native_receipt(packet_id),
        c4={
            "status": "PASS",
            "role": "C3_LANGUAGE",
            "selected_offer_ids": [packet_id, packet_id, "not-an-id"],
            "count": 3,
        },
        body_rows=_body_rows("B1_DETAIL", query_id, packet_id=packet_id),
    )
    latest = brain_panel._latest_native_evidence(runtime)
    assert latest["offer_flow"]["c4_native_offer_ids_match"] is False
    assert latest["offer_flow"]["body_attempts"][0]["consumption_state"] == (
        "DELIVERED_NOT_SELECTED_BY_C4"
    )


def test_native_template_packet_role_mismatch_is_not_reported_as_consumed():
    query_id, packet_id = _id("pkt", "5"), _id("pkt", "6")
    receipt = _native_receipt(packet_id)
    receipt["offers"] = [{
        "role": "B2_GIST",
        "packet_id": packet_id,
        "rendered_quote_count": 1,
    }]
    runtime = _runtime(
        receipt=receipt,
        c4={
            "status": "PASS",
            "role": "C3_LANGUAGE",
            "selected_offer_ids": [packet_id],
            "count": 1,
        },
        body_rows=_body_rows("B1_DETAIL", query_id, packet_id=packet_id),
    )
    body = brain_panel._latest_native_evidence(runtime)["offer_flow"]["body_attempts"][0]
    assert body["selected_by_c4"] is True
    assert body["native_template_role"] == "B2_GIST"
    assert body["template_role_matches"] is False
    assert body["included_in_c3_template"] is False
    assert body["consumption_state"] == "C4_C3_PACKET_ROLE_MISMATCH"
    assert body["semantic_use_proven"] is False


def test_duplicate_native_template_packet_ids_cannot_create_role_binding():
    query_id, packet_id = _id("pkt", "7"), _id("pkt", "8")
    receipt = _native_receipt(packet_id)
    receipt["offers"] = [
        {"role": "B1_DETAIL", "packet_id": packet_id, "rendered_quote_count": 1},
        {"role": "B2_GIST", "packet_id": packet_id, "rendered_quote_count": 1},
    ]
    runtime = _runtime(
        receipt=receipt,
        c4={
            "status": "PASS",
            "role": "C3_LANGUAGE",
            "selected_offer_ids": [packet_id],
            "count": 1,
        },
        body_rows=_body_rows("B1_DETAIL", query_id, packet_id=packet_id),
    )
    latest = brain_panel._latest_native_evidence(runtime)
    body = latest["offer_flow"]["body_attempts"][0]
    assert latest["offer_flow"]["c4_native_offer_ids_match"] is False
    assert body["native_template_role"] is None
    assert body["template_role_matches"] is False
    assert body["included_in_c3_template"] is False
    assert body["consumption_state"] == "C4_C3_PACKET_ROLE_MISMATCH"


def test_missing_persisted_offer_packet_cannot_be_reported_as_consumed():
    query_id, packet_id = _id("pkt", "9"), _id("pkt", "a")
    runtime = _runtime(
        receipt=_native_receipt(packet_id),
        c4={
            "status": "PASS",
            "role": "C3_LANGUAGE",
            "selected_offer_ids": [packet_id],
            "count": 1,
        },
        body_rows=_body_rows("B1_DETAIL", query_id, packet_id=packet_id),
    )
    runtime.store.packet_rows.clear()
    latest = brain_panel._latest_native_evidence(runtime)
    body = latest["offer_flow"]["body_attempts"][0]
    assert body["offer_packet_verified"] is False
    assert body["source_bound"] is False
    assert body["verified_source_span_count"] is None
    assert body["consumption_state"] == "DELIVERED_OFFER_PACKET_UNVERIFIED"
    assert latest["offer_flow"]["status"] == (
        "NATIVE_TEMPLATE_MATCHED_C4_BODY_EVIDENCE_UNVERIFIED"
    )


def test_deleted_offer_source_ref_cannot_be_reported_as_source_bound():
    query_id, packet_id = _id("pkt", "b"), _id("pkt", "c")
    runtime = _runtime(
        receipt=_native_receipt(packet_id),
        c4={
            "status": "PASS",
            "role": "C3_LANGUAGE",
            "selected_offer_ids": [packet_id],
            "count": 1,
        },
        body_rows=_body_rows("B1_DETAIL", query_id, packet_id=packet_id),
    )
    runtime.store.source_refs.clear()
    latest = brain_panel._latest_native_evidence(runtime)
    body = latest["offer_flow"]["body_attempts"][0]
    assert body["offer_packet_verified"] is True
    assert body["source_bound"] is False
    assert body["verified_source_span_count"] == 0
    assert body["source_count_matches"] is False
    assert body["consumption_state"] == "DELIVERED_WITHOUT_VERIFIED_SOURCE_SPANS"


def test_reported_source_count_must_match_persisted_offer_packet():
    query_id, packet_id = _id("pkt", "d"), _id("pkt", "e")
    rows = _body_rows("B1_DETAIL", query_id, packet_id=packet_id)
    delivered = json.loads(rows[1]["metrics"])
    delivered["count"] = 2
    rows[1]["metrics"] = json.dumps(delivered)
    runtime = _runtime(
        receipt=_native_receipt(packet_id),
        c4={
            "status": "PASS",
            "role": "C3_LANGUAGE",
            "selected_offer_ids": [packet_id],
            "count": 1,
        },
        body_rows=rows,
    )
    latest = brain_panel._latest_native_evidence(runtime)
    body = latest["offer_flow"]["body_attempts"][0]
    assert body["source_bound"] is True
    assert body["reported_source_span_count"] == 2
    assert body["verified_source_span_count"] == 1
    assert body["source_count_matches"] is False
    assert body["consumption_state"] == "DELIVERED_SOURCE_SPAN_COUNT_MISMATCH"


def test_real_sqlite_offer_packet_and_source_ref_are_verified(tmp_path):
    home = tmp_path / "v14-test-home"
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    try:
        session = store.new_session("body evidence test")
        event = store.event(session, "Please use the source evidence.")
        source_ref = store.source("A persisted exact source span.", "TEST_EVIDENCE")
        query_id = _id("pkt", "f")
        query = packet(
            "QueryPacket", "C2_CONTROL", event["event_id"],
            event["brain_generation_id"], [source_ref],
            target_role="B1_DETAIL", goal="extract one exact detail",
            source_refs=[source_ref],
        )
        store.add_packet("QueryPacket", query)
        offer = packet(
            "OfferPacket", "B1_DETAIL", event["event_id"],
            event["brain_generation_id"], [source_ref],
            role="B1_DETAIL", based_on_state_version=0,
            deadline_monotonic_ns=time.monotonic_ns() + 10_000_000_000,
            evidence_refs=[source_ref], offer={"summary": "test hypothesis"},
            confidence=0.7, query_packet_id=query["packet_id"],
        )
        store.add_packet("OfferPacket", offer)
        store.log("body_offer_attempt", event["event_id"], {
            "role": "B1_DETAIL", "query_packet_id": query["packet_id"],
            "status": "FINAL", "runner": {"prompt_tokens": 12, "generated_tokens": 2,
            "ttft_s": 0.1, "duration_s": 0.2, "synthetic": False},
        })
        store.log("body_offer_delivered", event["event_id"], {
            "role": "B1_DETAIL", "query_packet_id": query["packet_id"],
            "packet_id": offer["packet_id"], "count": 1, "duration_s": 0.2,
        })
        store.log("c4_offer_context_ready", event["event_id"], {
            "status": "PASS", "role": "C3_LANGUAGE",
            "selected_offer_ids": [offer["packet_id"]], "count": 1,
        })
        receipt = {
            "status": "RENDERED_WITH_QUOTES",
            "native_template_submitted": True,
            "native_prompt_sha256": "a" * 64,
            "native_token_ids_sha256": "b" * 64,
            "native_prompt_tokens": 12,
            "native_prefill_observed": True,
            "native_generation_completed": True,
            "offers": [{"role": "B1_DETAIL", "packet_id": offer["packet_id"],
                        "rendered_quote_count": 1}],
        }
        store.message(session, event["event_id"], "assistant", "answer", "FINAL", {
            "runner": {"role": "C3_LANGUAGE", "synthetic": False,
                       "native_offer_prompt_receipt": receipt},
            "model_revision": "c3-test-rev",
        })
        runtime = SimpleNamespace(store=store)
        latest = brain_panel._latest_native_evidence(runtime)
        body = latest["offer_flow"]["body_attempts"][0]
        assert body["offer_packet_verified"] is True
        assert body["source_bound"] is True
        assert body["source_count_matches"] is True
        assert body["verified_source_span_count"] == 1
        # Store telemetry intentionally drops the runner's synthetic marker.
        # Source/packet verification can pass, but native execution remains unverified.
        assert body["evidence_environment"] == "UNVERIFIED"
        assert body["native_prefill_observed"] is True
        assert body["consumption_state"] == "BODY_ATTEMPT_ENVIRONMENT_UNVERIFIED"

        with store.tx() as conn:
            conn.execute("UPDATE sources SET deleted=1 WHERE id=?", (source_ref["source_id"],))
        latest_after_revoke = brain_panel._latest_native_evidence(runtime)
        revoked = latest_after_revoke["offer_flow"]["body_attempts"][0]
        assert revoked["offer_packet_verified"] is True
        assert revoked["source_bound"] is False
        assert revoked["verified_source_span_count"] == 0
        assert revoked["consumption_state"] == "DELIVERED_WITHOUT_VERIFIED_SOURCE_SPANS"
    finally:
        store.close()
