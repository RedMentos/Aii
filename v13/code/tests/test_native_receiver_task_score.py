import hashlib
import json
from pathlib import Path

import pytest

from v13 import native_probe_approval as approval
from v13.operator import Operator
from v13.runtime import Runtime

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


def make_receipt(task_index, session_id, task_family, condition):
    task_group_id = f"task-{task_index:02d}"
    source_ref = {"source_id": f"source-{task_index:02d}", "sha256": sha(f"source-{task_index}")}
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
    input_sha = sha(f"input-{task_index}-{condition}")
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


def complete_group(runtime, task_index=0, session_id="session-A", task_family="ARITHMETIC"):
    result = None
    for condition in CONDITIONS:
        result = record_task_score_receipt(
            runtime, make_receipt(task_index, session_id, task_family, condition)
        )
    return result


def test_single_complete_task_group_is_not_enough_for_utility():
    runtime = type("Runtime", (), {"session": "session-A"})()
    result = complete_group(runtime)
    assert result["status"] == "FIXTURE_ONLY"
    assert result["task_group_count"] == 1
    assert result["enough_holdout"] is False
    assert result["semantic_use_proven"] is False
    assert result["training_authority"] == result["native_receiver_authority"] == 0
    assert result["persisted"] is False


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


def _operator_runtime(tmp_path):
    runtime = Runtime(Path(tmp_path))
    runtime.sleep.cycle.set_policy("enabled", "off")
    return runtime


def test_task_score_operator_status_is_local_counts_only(tmp_path, monkeypatch):
    runtime = _operator_runtime(tmp_path)
    try:
        monkeypatch.setattr(approval, "_require_local_tty", lambda: None)
        result = json.loads(Operator(runtime).run(":callosum task-score status"))
        assert result["schema"] == "v14.native-receiver-task-score-operator/1"
        assert result["operation"] == "STATUS"
        assert result["cohort"]["status"] == "EMPTY"
        assert result["cohort"]["receipt_count"] == 0
        assert result["cohort"]["persisted"] is False
        assert result["production_route"] is False
        assert result["semantic_use_proven"] is False
        assert result["generated_answer_correctness_proven"] is False
        encoded = json.dumps(result)
        for forbidden in ("token_logprobs", "source_text", "source_id", "target_token_ids_sha256", "context_sha256"):
            assert forbidden not in encoded
    finally:
        runtime.close()


def test_task_score_operator_evaluation_keeps_synthetic_fixture_non_authoritative(tmp_path, monkeypatch):
    runtime = _operator_runtime(tmp_path)
    try:
        monkeypatch.setattr(approval, "_require_local_tty", lambda: None)
        complete_group(runtime, 0, "session-A", "ARITHMETIC")
        result = json.loads(Operator(runtime).run(":callosum task-score evaluate"))
        evaluation = result["evaluation"]
        assert result["schema"] == "v14.native-receiver-task-score-operator/1"
        assert result["operation"] == "EVALUATE"
        assert evaluation["status"] == "FIXTURE_ONLY"
        assert evaluation["evidence_class"] == "SYNTHETIC"
        assert evaluation["semantic_use_proven"] is False
        assert evaluation["generated_answer_correctness_proven"] is False
        assert evaluation["production_route"] is False
        assert evaluation["training_authority"] == 0
        assert evaluation["native_receiver_authority"] == 0
        assert evaluation["persisted"] is False
    finally:
        runtime.close()


def test_task_score_operator_clear_requires_confirmation_and_preserves_pending_probe(tmp_path, monkeypatch):
    runtime = _operator_runtime(tmp_path)
    try:
        monkeypatch.setattr(approval, "_require_local_tty", lambda: None)
        record_task_score_receipt(runtime, make_receipt(0, "session-A", "ARITHMETIC", "NO_MESSAGE"))
        with pytest.raises(ValueError, match="usage"):
            Operator(runtime).run(":callosum task-score clear")
        state, version = runtime.store.state(approval.KEY, None)
        runtime.store.set_state(approval.KEY, {"status": "PENDING"}, expected=version)
        with pytest.raises(PermissionError, match="revoke the pending local probe approval"):
            Operator(runtime).run(":callosum task-score clear --confirm")
        assert task_score_status(runtime)["receipt_count"] == 1
        runtime.store.set_state(approval.KEY, {"status": "REVOKED"}, expected=version + 1)
        result = json.loads(Operator(runtime).run(":callosum task-score clear --confirm"))
        assert result["operation"] == "CLEAR"
        assert result["status"] == "CLEARED"
        assert result["discarded_receipt_count"] == 1
        assert result["persisted"] is False
        assert task_score_status(runtime)["status"] == "EMPTY"
    finally:
        runtime.close()


def test_task_score_operator_rejects_model_origin(tmp_path, monkeypatch):
    runtime = _operator_runtime(tmp_path)
    try:
        monkeypatch.setattr(approval, "_require_local_tty", lambda: None)
        with pytest.raises(PermissionError):
            Operator(runtime).run(":callosum task-score status", origin="MODEL")
    finally:
        runtime.close()
