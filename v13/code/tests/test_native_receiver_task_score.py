import hashlib
import struct

import pytest

from v13.native_receiver_utility import (
    CONDITIONS,
    NativeReceiverUtilityError,
    build_native_receiver_task_score_receipt,
)
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




def hybrid_state_roundtrip_for(base, overrides=None):
    native = base["native"]
    receiver = base["receiver"]
    state = {
        "schema": "v14.native-hybrid-state-roundtrip/1",
        "status": "READ_ONLY_ROUNDTRIP",
        "state_api": "LLAMA_STATE_SEQ_GET_SIZE_GET_DATA_SET_DATA",
        "state_scope": "FULL_HYBRID_SEQUENCE",
        "state_components": ["ATTENTION_KV", "RECURRENT_SHORTCONV"],
        "source_sequence_id": 0,
        "destination_sequence_id": 0,
        "source_model_sha256": receiver["model_sha256"],
        "destination_model_sha256": receiver["model_sha256"],
        "source_model_revision": receiver["model_revision"],
        "destination_model_revision": receiver["model_revision"],
        "source_tokenizer_revision": receiver["tokenizer_revision"],
        "destination_tokenizer_revision": receiver["tokenizer_revision"],
        "source_llama_cpp_revision": native["llama_cpp_revision"],
        "destination_llama_cpp_revision": native["llama_cpp_revision"],
        "source_binary_sha256": native["binary_sha256"],
        "destination_binary_sha256": native["binary_sha256"],
        "source_context_sha256": base["context_sha256"],
        "destination_context_sha256": base["context_sha256"],
        "source_input_sha256": base["input_sha256"],
        "continuation_token_ids_sha256": base["target_token_ids_sha256"],
        "source_context_params_sha256": sha("native-context-params-r1"),
        "destination_context_params_sha256": sha("native-context-params-r1"),
        "state_bytes": 4096,
        "get_size_bytes": 4096,
        "get_data_bytes": 4096,
        "set_data_bytes": 4096,
        "state_sha256": sha("hybrid-state-" + base["task_group_id"]),
        "capture_duration_us": 100,
        "restore_duration_us": 120,
        "baseline_logits_sha256": sha("baseline-" + base["task_group_id"]),
        "restored_logits_sha256": sha("restored-" + base["task_group_id"]),
        "continuation_token_count": base["target_token_count"],
        "top1_match_count": base["target_token_count"],
        "max_abs_logit_diff": 0.0,
        "rms_logit_diff": 0.0,
        "roundtrip_passed": True,
        "truncated_restore_rejected": True,
        "attention_kv_included": True,
        "recurrent_shortconv_included": True,
        "raw_state_exported": False,
        "state_persisted": False,
        "state_buffer_zeroized": True,
        "installed_runtime_touched": False,
        "production_route": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }
    state.update(overrides or {})
    return state


def attach_hybrid_state_roundtrip(base, overrides=None):
    native = dict(base["native"])
    native["hybrid_state_roundtrip"] = hybrid_state_roundtrip_for(base, overrides)
    return build_native_receiver_task_score_receipt(
        condition=base["condition"],
        task_group_id=base["task_group_id"],
        task_family=base["task_family"],
        session_id=base["session_id"],
        source_ref=base["source_ref"],
        message_source_ref=base["message_source_ref"],
        receiver=base["receiver"],
        target_token_ids_sha256=base["target_token_ids_sha256"],
        target_token_count=base["target_token_count"],
        context_sha256=base["context_sha256"],
        input_sha256=base["input_sha256"],
        native_receipt=native,
        adapter_sha256=base["adapter_sha256"],
    )

def make_receipt(task_index, session_id, task_family, condition, source_ref_override=None,
                 input_sha_override=None, kv_digest_override=None, kv_geometry_override=None):
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
            "layer_id": (kv_geometry_override or {}).get("layer_id", 0),
            "attention_layer_count": (kv_geometry_override or {}).get("attention_layer_count", 12),
            "active_cell_count": 1,
            "position_ids": [0],
            "position_sha256": position_sha,
            "k_shape": (kv_geometry_override or {}).get("k_shape", [64, 8, 128, 1]),
            "v_shape": (kv_geometry_override or {}).get("v_shape", [128, 8, 64, 1]),
            "k_type": (kv_geometry_override or {}).get("k_type", "f16"),
            "v_type": (kv_geometry_override or {}).get("v_type", "f16"),
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
                   source_ref_override=None, input_overrides=None, kv_overrides=None,
                   kv_geometry_override=None, include_hybrid_state_roundtrip=False,
                   hybrid_state_roundtrip_override=None):
    result = None
    input_overrides = input_overrides or {}
    kv_overrides = kv_overrides or {}
    for condition in CONDITIONS:
        receipt = make_receipt(
            task_index, session_id, task_family, condition,
            source_ref_override=source_ref_override,
            input_sha_override=input_overrides.get(condition),
            kv_digest_override=kv_overrides.get(condition),
            kv_geometry_override=kv_geometry_override,
        )
        if include_hybrid_state_roundtrip and condition == "NO_MESSAGE":
            receipt = attach_hybrid_state_roundtrip(receipt, hybrid_state_roundtrip_override)
        result = record_task_score_receipt(runtime, receipt)
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
    assert effect["distinct_from_no_message_task_groups_by_condition"]["NO_MESSAGE"] == 0
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


@pytest.mark.parametrize("geometry_override", [
    {"layer_id": 1},
    {"attention_layer_count": 13},
    {"k_shape": [32, 8, 128, 1]},
    {"k_type": "f32"},
])
def test_kv_snapshot_geometry_must_remain_stable_across_task_groups(geometry_override):
    runtime = type("Runtime", (), {"session": "session-A"})()
    baseline = {condition: "baseline-" + condition for condition in CONDITIONS}
    changed = {condition: "changed-" + condition for condition in CONDITIONS}
    complete_group(runtime, task_index=0, kv_overrides=baseline)

    with pytest.raises(
        NativeReceiverTaskScoreError,
        match="complete task-score cohort failed validation",
    ) as error:
        complete_group(
            runtime,
            task_index=1,
            session_id="session-B",
            task_family="ENTITY_RECALL",
            kv_overrides=changed,
            kv_geometry_override=geometry_override,
        )

    assert "native K/V snapshot geometry changed across task cohort" in str(error.value.__cause__)
    status = task_score_status(runtime)
    assert status["receipt_count"] == 15
    assert status["complete_task_group_count"] == 1
    assert status["incomplete_task_group_count"] == 1


def test_hybrid_state_roundtrip_effect_is_read_only_and_not_part_of_utility_gate():
    runtime = type("Runtime", (), {"session": "session-A"})()
    result = None
    for task_index in range(20):
        session_id = "session-A" if task_index < 10 else "session-B"
        family = "ARITHMETIC" if task_index % 2 == 0 else "ENTITY_RECALL"
        result = complete_group(
            runtime, task_index, session_id, family,
            include_hybrid_state_roundtrip=True,
        )
    effect = result["hybrid_state_roundtrip_effect"]
    assert result["status"] == "FIXTURE_ONLY"
    assert result["candidate_beats_all_controls"] is False
    assert effect["status"] == "SAME_MODEL_ROUNDTRIP_PASS"
    assert effect["task_group_count"] == 20
    assert effect["state_bytes_min"] == effect["state_bytes_max"] == 4096
    assert effect["top1_match_rate"] == 1.0
    assert effect["truncated_restore_rejected_count"] == 20
    assert effect["same_model_only"] is True
    assert effect["cross_model_transfer_proven"] is False
    assert effect["trained_latent_coupling_proven"] is False
    assert effect["influence_on_utility_gate"] is False
    assert effect["production_route"] is False
    assert effect["training_authority"] == effect["native_receiver_authority"] == 0
    assert effect["persisted"] is False


def test_hybrid_state_roundtrip_failure_is_reported_without_passing_task_utility():
    runtime = type("Runtime", (), {"session": "session-A"})()
    result = complete_group(
        runtime, include_hybrid_state_roundtrip=True,
        hybrid_state_roundtrip_override={
            "top1_match_count": 1,
            "max_abs_logit_diff": 0.01,
            "rms_logit_diff": 0.002,
            "roundtrip_passed": False,
        },
    )
    effect = result["hybrid_state_roundtrip_effect"]
    assert result["status"] == "FIXTURE_ONLY"
    assert result["candidate_beats_all_controls"] is False
    assert effect["status"] == "SAME_MODEL_ROUNDTRIP_FAIL"
    assert effect["all_roundtrips_passed"] is False
    assert effect["top1_match_rate"] == 0.5
    assert effect["influence_on_utility_gate"] is False


def test_hybrid_state_roundtrip_partial_cohort_coverage_fails_closed():
    runtime = type("Runtime", (), {"session": "session-A"})()
    complete_group(runtime, task_index=0, include_hybrid_state_roundtrip=True)
    with pytest.raises(
        NativeReceiverTaskScoreError,
        match="complete task-score cohort failed validation",
    ) as error:
        complete_group(
            runtime, task_index=1, session_id="session-B",
            task_family="ENTITY_RECALL",
        )
    assert "hybrid-state roundtrip coverage changed across task cohort" in str(error.value.__cause__)
    status = task_score_status(runtime)
    assert status["complete_task_group_count"] == 1
    assert status["incomplete_task_group_count"] == 1


def test_hybrid_state_roundtrip_is_only_allowed_on_no_message_condition():
    base = make_receipt(0, "session-A", "ARITHMETIC", "EXACT_MESSAGE")
    with pytest.raises(NativeReceiverUtilityError, match="only allowed on NO_MESSAGE"):
        attach_hybrid_state_roundtrip(base)


@pytest.mark.parametrize("overrides,match", [
    ({"destination_model_sha256": "e" * 64}, "model SHA"),
    ({"destination_context_params_sha256": "e" * 64}, "context parameters SHA"),
    ({"set_data_bytes": 4095}, "pass flag"),
    ({"truncated_restore_rejected": False}, "truncated restore negative control"),
    ({"raw_state_blob": "must-not-be-present"}, "fields mismatch"),
])
def test_hybrid_state_roundtrip_rejects_wrong_binding_or_raw_payload(overrides, match):
    base = make_receipt(0, "session-A", "ARITHMETIC", "NO_MESSAGE")
    with pytest.raises(NativeReceiverUtilityError, match=match):
        attach_hybrid_state_roundtrip(base, overrides)


def test_hybrid_state_roundtrip_absence_is_explicitly_unavailable():
    runtime = type("Runtime", (), {"session": "session-A"})()
    result = complete_group(runtime)
    assert result["hybrid_state_roundtrip_effect"]["status"] == "UNAVAILABLE"
    assert result["hybrid_state_roundtrip_effect"]["cross_model_transfer_proven"] is False
    assert result["hybrid_state_roundtrip_effect"]["influence_on_utility_gate"] is False
