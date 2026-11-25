import json

from v13 import brain_panel


def _id(prefix, char):
    return prefix + "_" + char * 32


class FakeStore:
    def __init__(self, message, c4_metrics=None, body_rows=()):
        self.message = message
        self.c4_metrics = c4_metrics
        self.body_rows = list(body_rows)

    def one(self, sql, args=()):
        if "FROM messages" in sql:
            return self.message
        if "c4_offer_context_ready" in sql:
            return {"metrics": json.dumps(self.c4_metrics)} if self.c4_metrics is not None else None
        raise AssertionError("unexpected Store.one query")

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
