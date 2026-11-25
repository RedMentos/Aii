import json

from v13 import brain_panel


def _runner(role, prompt_tokens, prompt_n, cache_n, generated):
    return {
        "role": role,
        "status": "FINAL",
        "prompt_tokens": prompt_tokens,
        "generated_tokens": generated,
        "ttft_s": 1.25,
        "duration_s": 3.5,
        "sampled_peak_pss_bytes": 123456,
        "actual_model": role.lower() + ".gguf",
        "prompt_admission": {
            "native_prompt_tokens": prompt_tokens,
            "native_tokenizer": "LLAMA_SERVER_TOKENIZE",
        },
        "timings": {
            "prompt_n": prompt_n,
            "cache_n": cache_n,
            "predicted_n": generated,
            "prompt_ms": 900.0,
            "prompt_per_second": 44.4,
        },
        # Must never escape the read-only summary.
        "resource_samples": [{"private": "PRIVATE_NATIVE_SAMPLE_SENTINEL"}],
    }


def _fixture():
    b1 = _runner("B1_DETAIL", 90, 80, 10, 15)
    b2 = _runner("B2_GIST", 40, 40, 0, 8)
    c3 = _runner("C3_LANGUAGE", 64, 58, 6, 12)
    c3["native_offer_prompt_receipt"] = {
        "status": "RENDERED_WITH_QUOTES",
        "offers": [
            {"role": "B1_DETAIL", "packet_id": "offer-b1", "rendered_quote_count": 1},
            {"role": "B2_GIST", "packet_id": "offer-b2", "rendered_quote_count": 2},
        ],
        "native_completion_http_200": True,
        "native_template_submitted": True,
        "native_prompt_sha256": "a" * 64,
        "native_token_ids_sha256": "b" * 64,
        "native_prompt_tokens": 64,
        "native_tokenizer": "LLAMA_SERVER_TOKENIZE",
        "native_prefill_observed": True,
        "native_prompt_prefill_verified": False,
        "native_stream_completed": True,
        "native_generation_completed": True,
        "native_attention_or_semantic_use_proven": False,
    }
    message = {
        "event_id": "event-1",
        "status": "FINAL",
        "metadata": json.dumps({
            "runner": c3,
            "model_revision": "c3-r1",
        }),
    }
    c4 = {
        "role": "C3_LANGUAGE",
        "status": "PASS",
        "count": 2,
        "selected_offer_ids": ["offer-b1", "offer-b2"],
    }
    attempts = [
        {"metrics": json.dumps({"role": "B1_DETAIL", "status": "FINAL", "runner": b1})},
        {"metrics": json.dumps({"role": "B2_GIST", "status": "FINAL", "runner": b2})},
    ]
    packets = [
        {"payload": json.dumps({
            "packet_id": "offer-b1", "role": "B1_DETAIL",
            "model_revision": "b1-r1", "evidence_refs": [{"source_id": "source-1"}],
            "native_metrics": b1, "offer": {"summary": "PRIVATE_BODY_SUMMARY_SENTINEL"},
        })},
        {"payload": json.dumps({
            "packet_id": "offer-b2", "role": "B2_GIST",
            "model_revision": "b2-r1", "evidence_refs": [{"source_id": "source-1"}, {"source_id": "source-2"}],
            "native_metrics": b2, "offer": {"summary": "PRIVATE_BODY_SUMMARY_SENTINEL"},
        })},
    ]
    return message, c4, attempts, packets


class _Store:
    def __init__(self, message, c4, attempts, packets):
        self.message = message
        self.c4 = c4
        self.attempts = attempts
        self.packets = packets

    def one(self, query, args=()):
        if "FROM messages" in query:
            return self.message
        if "c4_offer_context_ready" in query:
            return {"metrics": json.dumps(self.c4)}
        return None

    def rows(self, query, args=()):
        if "body_offer_attempt" in query:
            return self.attempts
        if "OfferPacket" in query:
            return self.packets
        return []


class _Runtime:
    def __init__(self, store):
        self.store = store


def _evidence():
    message, c4, attempts, packets = _fixture()
    store = _Store(message, c4, attempts, packets)
    return brain_panel._latest_native_evidence(_Runtime(store)), store


def test_native_prompt_accounting_and_body_offer_delivery_are_correlated():
    evidence, _ = _evidence()

    assert evidence["offer_flow"]["status"] == (
        "NATIVE_PROMPT_ACCOUNTING_VERIFIED_AND_GENERATION_COMPLETED_MATCHED_C4"
    )
    accounting = evidence["offer_flow"]["native_prompt_accounting"]
    assert accounting["status"] == "MATCHED"
    assert accounting["tokenized_prompt_tokens"] == 64
    assert accounting["native_processed_prompt_tokens"] == 58
    assert accounting["native_cached_prompt_tokens"] == 6
    assert accounting["native_accounted_prompt_tokens"] == 64
    assert accounting["native_predicted_tokens"] == 12
    assert accounting["generation_token_count_match"] is True
    assert accounting["semantic_attention_proven"] is False

    body = evidence["body_offer_flow"]
    assert body["attempt_count"] == 2
    assert body["offer_packet_count"] == 2
    assert body["c4_selected_packets_persisted"] is True
    assert body["c3_rendered_packets_persisted"] is True
    assert {item["role"] for item in body["offers"]} == {"B1_DETAIL", "B2_GIST"}
    assert all(item["selected_by_c4"] for item in body["offers"])
    assert all(item["rendered_in_c3_template"] for item in body["offers"])
    assert all(item["native"]["prompt_accounting"]["verified"] for item in body["offers"])
    assert body["semantic_use_proven"] is False


def test_mismatched_native_prompt_counts_do_not_become_verified():
    evidence, store = _evidence()
    metadata = json.loads(store.message["metadata"])
    metadata["runner"]["timings"]["prompt_n"] = 57
    store.message["metadata"] = json.dumps(metadata)

    evidence = brain_panel._latest_native_evidence(_Runtime(store))
    accounting = evidence["offer_flow"]["native_prompt_accounting"]
    assert accounting["status"] == "MISMATCH"
    assert accounting["verified"] is False
    assert accounting["native_accounted_prompt_tokens"] == 63
    assert evidence["offer_flow"]["status"] == "NATIVE_PROMPT_ACCOUNTING_MISMATCH_MATCHED_C4"


def test_missing_cache_counter_and_synthetic_receipts_fail_closed():
    evidence, store = _evidence()
    metadata = json.loads(store.message["metadata"])
    metadata["runner"]["timings"].pop("cache_n")
    store.message["metadata"] = json.dumps(metadata)
    evidence = brain_panel._latest_native_evidence(_Runtime(store))
    assert evidence["offer_flow"]["native_prompt_accounting"]["status"] == "TIMING_FIELDS_UNAVAILABLE"

    evidence, store = _evidence()
    metadata = json.loads(store.message["metadata"])
    metadata["runner"]["synthetic"] = True
    store.message["metadata"] = json.dumps(metadata)
    evidence = brain_panel._latest_native_evidence(_Runtime(store))
    accounting = evidence["offer_flow"]["native_prompt_accounting"]
    assert accounting["status"] == "SYNTHETIC_NOT_NATIVE"
    assert accounting["tokenized_prompt_tokens"] is None

def test_native_output_token_count_mismatch_is_separate_from_prompt_accounting():
    _, store = _evidence()
    metadata = json.loads(store.message["metadata"])
    metadata["runner"]["timings"]["predicted_n"] = 11
    store.message["metadata"] = json.dumps(metadata)

    evidence = brain_panel._latest_native_evidence(_Runtime(store))
    accounting = evidence["offer_flow"]["native_prompt_accounting"]
    assert accounting["verified"] is True
    assert accounting["native_predicted_tokens"] == 11
    assert accounting["runner_generated_tokens"] == 12
    assert accounting["generation_token_count_match"] is False



def test_attempt_deadline_cannot_inherit_a_stale_final_runner_receipt():
    evidence, store = _evidence()
    stale_final = _runner("B2_GIST", 40, 40, 0, 8)
    store.attempts.append({
        "metrics": json.dumps({
            "role": "B2_GIST", "status": "DEADLINE", "runner": stale_final,
        })
    })
    evidence = brain_panel._latest_native_evidence(_Runtime(store))
    attempt = evidence["body_offer_flow"]["attempts"][-1]
    assert attempt["attempt_status"] == "DEADLINE"
    assert attempt["native"]["prompt_accounting"]["status"] == "GENERATION_NOT_COMPLETED"
    assert attempt["native"]["prompt_accounting"]["verified"] is False


def test_brain_panel_never_returns_private_offer_or_runner_text():
    evidence, _ = _evidence()
    serialized = json.dumps(evidence)
    assert "PRIVATE_NATIVE_SAMPLE_SENTINEL" not in serialized
    assert "PRIVATE_BODY_SUMMARY_SENTINEL" not in serialized
    assert "source-1" not in serialized

def test_operator_brain_status_exposes_delivery_evidence_without_claiming_learning():
    _, store = _evidence()
    panel = brain_panel.operator_command(_Runtime(store), ["status"])

    assert panel["kind"] == "READ_ONLY_RUNTIME_STATUS"
    assert panel["native_model_training_proven"] is False
    assert panel["latest_turn"]["offer_flow"]["native_prompt_accounting"]["verified"] is True
    assert panel["latest_turn"]["body_offer_flow"]["c4_selected_packets_persisted"] is True
    assert panel["latest_turn"]["body_offer_flow"]["semantic_use_proven"] is False

