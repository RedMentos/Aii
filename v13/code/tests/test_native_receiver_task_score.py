import hashlib
import struct

import pytest

from v13.native_receiver_utility import CONDITIONS, build_native_receiver_task_score_receipt
from v13.native_receiver_task_score import (
    MAX_TASK_SCORE_RECEIPTS,
    NativeReceiverTaskScoreError,
    clear_task_score_cohort,
    evaluate_task_score_cohort,
    record_task_score_receipt,
    task_score_status,
)

LLAMA_REVISION = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
RECEIVER = {
    "role": "C3_LANGUAGE",
    "model_revision": "c3-pinned-r1",
    "model_sha256": "b" * 64,
    "tokenizer_revision": "c3-tokenizer-r1",
}
ADAPTER_SHA256 = "a" * 64


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_receipt(task_index, session_id, task_family, condition, source_ref_override=None,
                 input_sha_override=None, kv_digest_override=None):
    task_group_id = f"task-{task_index:02d}"
    source_ref = source_ref_override or {"source_id": f"source-{task_index:02d}", "sha256": sha(f"source-{task_index}")}
    if condition == "NO_MESSAGE":
        message_source_ref = None
        adapter_sha256 = None
    elif condition == "EXACT_MESSAGE":
        message_source_ref = source_ref
        adapter_sha256 = None
    elif condition in {"OOD", "ENTITY_SUBSTITUTION"}:
        message_source_ref = {
            "source_id": f"control-{condition.lower()}-{task_index:02d}",
            "sha256": sha(f"{condition}-source-{task_index}"),
        }
        adapter_sha256 = ADAPTER_SHA256
    else:
        message_source_ref = source_ref
        adapter_sha256 = ADAPTER_SHA256
    target_sha = sha(f"target-{task_index}")
    input_sha = input_sha_override or sha(f"input-{task_index}-{condition}")
    native = {
        "schema": "v14.native-receiver-target-score/1",
        "execution_kind": "SYNTHETIC_FIXTURE",
        "environment": "SYNTHETIC",
        "llama_cpp_revision": LLAMA_REVISION,
        "binary_sha256": "c" * 64,
        "receiver_model_sha256": RECEIVER["model_sha256"],
        "input_sha256": input_sha,
        "target_token_ids_sha256": target_sha,
        "target_token_count": 2,
        "score_method": "TEACHER_FORCED_TARGET_LOGPROB_V1",
        "token_logprobs": [-1.0, -1.25],
        "decode_status": 0,
        "native_input_consumed": True,
        "llama_version": "synthetic-fixture",
    }
    if kv_digest_override is not None:
        position_sha = hashlib.sha256(struct.pack("<i", 0)).hexdigest()
        combined_sha = sha("kv-combined-" + kv_digest_override)
        native["kv_snapshot"] = {
            "schema": "v14.native-receiver-kv-snapshot/1",
            "status": "READ_ONLY_SNAPSHOT",
            "cache_kind": "LLAMA_MEMORY_HYBRID_ATTENTION",
            "snapshot_scope": "ONE_ATTENTION_LAYER_ONE_SEQUENCE",
            "sequence_id": 0,
            "layer_id": 0,
            "attention_layer_count": 12,
            "active_cell_count": 1,
            "position_ids": [0],
            "position_sha256": position_sha,
            "k_shape": [64, 8, 128, 1],
            "v_shape": [128, 8, 64, 1],
            "k_type": "f16",
            "v_type": "f16",
            "k_sha256": sha("kv-k-" + kv_digest_override),
            "v_sha256": sha("kv-v-" + kv_digest_override),
            "combined_sha256": combined_sha,
            "stable_read_sha256": combined_sha,
            "bytes_read_per_snapshot": 64,
            "double_read_bytes_read": 128,
            "duration_us": 5,
            "read_only": True,
            "double_read_stable": True,
            "raw_data_exported": False,
            "recurrent_state_included": False,
        }
    return build_native_receiver_task_score_receipt(
        condition=condition,
        task_group_id=task_group_id,
        task_family=task_family,
        session_id=session_id,
        source_ref=source_ref,
        message_source_ref=message_source_ref,
        receiver=RECEIVER,
        target_token_ids_sha256=target_sha,
        target_token_count=2,
        context_sha256=sha(f"context-{task_index}"),
        input_sha256=input_sha,
        native_receipt=native,
        adapter_sha256=adapter_sha256,
    )


def complete_group(runtime, task_index=0, session_id="session-A", task_family="ARITHMETIC",
                   source_ref_override=None, input_overrides=None, kv_overrides=None):
    result = None
    input_overrides = input_overrides or {}
    kv_overrides = kv_overrides or {}
    for condition in CONDITIONS:
        result = record_task_score_receipt(
            runtime,
            make_receipt(
                task_index, session_id, task_family, condition,
                source_ref_override=source_ref_override,
                input_sha_override=input_overrides.get(condition),
                kv_digest_override=kv_overrides.get(condition),
            ),
        )
    return result


def test_single_complete_synthetic_task_group_is_not_enough_for_utility():
    runtime = type("Runtime", (), {"session": "session-A"})()
    result = complete_group(runtime)
    assert result["status"] == "FIXTURE_ONLY"
    assert result["task_group_count"] == 1
    assert result["enough_holdout"] is False
    assert result["holdout_status"] == "INSUFFICIENT_HOLDOUT"
    assert result["minimum_task_groups"] == 20
    assert result["semantic_use_proven"] is False
    assert result["training_authority"] == result["native_receiver_authority"] == 0
    assert result["persisted"] is False
    assert task_score_status(runtime)["status"] == "COHORT_READY"


def test_kv_snapshot_effect_is_read_only_and_separate_from_task_utility():
    runtime = type("Runtime", (), {"session": "session-A"})()
    kv_overrides = {condition: "kv-" + condition for condition in CONDITIONS}
    result = complete_group(runtime, kv_overrides=kv_overrides)
    effect = result["kv_snapshot_effect"]

    assert result["status"] == "FIXTURE_ONLY"
    assert effect["status"] == "READ_ONLY_SAMPLE_ONLY"
    assert effect["snapshot_count"] == 8
    assert effect["candidate_differs_from_no_message_count"] == 1
    assert effect["candidate_differs_from_exact_message_count"] == 1
    assert effect["distinct_from_no_message_by_condition"]["NO_MESSAGE"] is False
    assert effect["same_input_consistency_passed"] is True
    assert effect["semantic_use_proven"] is False
    assert effect["generated_answer_correctness_proven"] is False
    assert effect["production_route"] is False
    assert effect["training_authority"] == effect["native_receiver_authority"] == 0
    assert effect["persisted"] is False


def test_identical_input_digest_requires_identical_kv_snapshot():
    runtime = type("Runtime", (), {"session": "session-A"})()
    shared_input = sha("identical-receiver-input")
    input_overrides = {"EXACT_MESSAGE": shared_input, "LATENT_CANDIDATE": shared_input}
    kv_overrides = {condition: "kv-" + condition for condition in CONDITIONS}

    with pytest.raises(NativeReceiverTaskScoreError, match="complete task-score cohort failed validation") as error:
        complete_group(runtime, input_overrides=input_overrides, kv_overrides=kv_overrides)
    assert "identical receiver input digest" in str(error.value.__cause__)
    assert task_score_status(runtime)["receipt_count"] == 7
    assert task_score_status(runtime)["incomplete_task_group_count"] == 1


def test_identical_input_and_kv_snapshot_is_consistent():
    runtime = type("Runtime", (), {"session": "session-A"})()
    shared_input = sha("identical-receiver-input")
    shared_kv = "same-sampled-kv-state"
    input_overrides = {"EXACT_MESSAGE": shared_input, "LATENT_CANDIDATE": shared_input}
    kv_overrides = {
        "EXACT_MESSAGE": shared_kv,
        "LATENT_CANDIDATE": shared_kv,
        **{condition: "kv-" + condition for condition in CONDITIONS
           if condition not in {"EXACT_MESSAGE", "LATENT_CANDIDATE"}},
    }

    result = complete_group(runtime, input_overrides=input_overrides, kv_overrides=kv_overrides)
    effect = result["kv_snapshot_effect"]
    assert effect["duplicate_input_groups_checked"] == 1
    assert effect["same_input_consistency_passed"] is True
    assert effect["candidate_differs_from_exact_message_count"] == 0


def test_partial_kv_snapshot_coverage_is_rejected():
    runtime = type("Runtime", (), {"session": "session-A"})()
    with pytest.raises(NativeReceiverTaskScoreError, match="complete task-score cohort failed validation") as error:
        complete_group(runtime, kv_overrides={"NO_MESSAGE": "only-one-snapshot"})
    assert "partial native K/V snapshot coverage" in str(error.value.__cause__)
    assert task_score_status(runtime)["receipt_count"] == 7


def test_twenty_task_groups_across_two_sessions_are_fixture_only():
    runtime = type("Runtime", (), {"session": "session-A"})()
    result = None
    for task_index in range(20):
        session_id = "session-A" if task_index < 10 else "session-B"
        family = "ARITHMETIC" if task_index % 2 == 0 else "ENTITY_RECALL"
        result = complete_group(runtime, task_index, session_id, family)
    assert result["status"] == "FIXTURE_ONLY"
    assert result["evidence_class"] == "SYNTHETIC"
    assert result["task_group_count"] == 20
    assert result["session_count"] == 2
    assert result["enough_holdout"] is True
    assert result["balanced_session_family_coverage"] is True
    assert result["tasks_per_session_family"] == {
        "session-A": {"ARITHMETIC": 5, "ENTITY_RECALL": 5},
        "session-B": {"ARITHMETIC": 5, "ENTITY_RECALL": 5},
    }
    assert result["candidate_beats_all_controls"] is False
    assert result["semantic_use_proven"] is False
    assert result["generated_answer_correctness_proven"] is False
    assert result["production_route"] is False
    assert result["training_authority"] == result["native_receiver_authority"] == 0
    assert result["persisted"] is False


def test_incomplete_groups_remain_collecting_and_status_contains_counts_only():
    runtime = type("Runtime", (), {"session": "session-A"})()
    first = record_task_score_receipt(runtime, make_receipt(0, "session-A", "ARITHMETIC", "NO_MESSAGE"))
    assert first["status"] == "COLLECTING"
    status = task_score_status(runtime)
    assert status["receipt_count"] == 1
    assert status["complete_task_group_count"] == 0
    assert status["incomplete_task_group_count"] == 1
    assert "token_logprobs" not in status
    assert "source_text" not in status


def test_duplicate_condition_is_rejected():
    runtime = type("Runtime", (), {"session": "session-A"})()
    receipt = make_receipt(0, "session-A", "ARITHMETIC", "NO_MESSAGE")
    record_task_score_receipt(runtime, receipt)
    with pytest.raises(NativeReceiverTaskScoreError, match="duplicate"):
        record_task_score_receipt(runtime, receipt)


def test_receipt_cap_is_bounded_and_explicit_clear_discards_memory():
    runtime = type("Runtime", (), {"session": "session-A"})()
    for task_index in range(20):
        session_id = "session-A" if task_index < 10 else "session-B"
        family = "ARITHMETIC" if task_index % 2 == 0 else "ENTITY_RECALL"
        complete_group(runtime, task_index, session_id, family)
    assert task_score_status(runtime)["receipt_count"] == MAX_TASK_SCORE_RECEIPTS
    extra = make_receipt(21, "session-C", "OTHER", "NO_MESSAGE")
    with pytest.raises(NativeReceiverTaskScoreError, match="full"):
        record_task_score_receipt(runtime, extra)
    cleared = clear_task_score_cohort(runtime)
    assert cleared["status"] == "CLEARED"
    assert cleared["discarded_receipt_count"] == MAX_TASK_SCORE_RECEIPTS
    assert task_score_status(runtime)["status"] == "EMPTY"
    assert cleared["persisted"] is False


def test_collector_rejects_duplicate_source_content_across_task_groups():
    runtime = type("Runtime", (), {"session": "session-A"})()
    shared_source = make_receipt(0, "session-A", "ARITHMETIC", "NO_MESSAGE")["source_ref"]
    with pytest.raises(NativeReceiverTaskScoreError, match="failed validation"):
        for task_index in range(20):
            session_id = "session-A" if task_index < 10 else "session-B"
            family = "ARITHMETIC" if task_index % 2 == 0 else "ENTITY_RECALL"
            override = shared_source if task_index == 1 else None
            complete_group(
                runtime, task_index, session_id, family,
                source_ref_override=override,
            )


def test_collector_rejects_sparse_session_family_cross_even_when_totals_pass():
    runtime = type("Runtime", (), {"session": "session-A"})()
    result = None
    for task_index in range(20):
        session_id = "session-A" if task_index < 10 else "session-B"
        if session_id == "session-A":
            family = "ENTITY_RECALL" if task_index == 1 else "ARITHMETIC"
        else:
            family = "ARITHMETIC" if task_index == 10 else "ENTITY_RECALL"
        result = complete_group(runtime, task_index, session_id, family)
    assert result["status"] == "FIXTURE_ONLY"
    assert result["tasks_per_session"] == {"session-A": 10, "session-B": 10}
    assert result["tasks_per_family"] == {"ARITHMETIC": 10, "ENTITY_RECALL": 10}
    assert result["tasks_per_session_family"] == {
        "session-A": {"ARITHMETIC": 9, "ENTITY_RECALL": 1},
        "session-B": {"ARITHMETIC": 1, "ENTITY_RECALL": 9},
    }
    assert result["balanced_session_family_coverage"] is False
    assert result["enough_holdout"] is False
