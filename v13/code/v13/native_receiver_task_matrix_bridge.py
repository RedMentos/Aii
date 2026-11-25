"""Source-bound bridge from an approved condition matrix to native target scoring.

This joins the Perception matrix producer to the pinned native receiver probe and
Core's ephemeral task-score collector. It is diagnostic only: no persistence,
generated-answer correctness, weight update, production route or B3 authority.
"""
from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Mapping
from pathlib import Path

from .native_latent_receiver import PINNED_LLAMA_REVISION, POSITION_MODE, probe_matrix
from .native_receiver_condition_matrix import (
    SCHEMA as MATRIX_SCHEMA,
    REQUIRED_APPROVAL_KIND,
    NativeReceiverConditionMatrix,
)
from .native_receiver_task_score import record_task_score_receipts
from .native_receiver_utility import CONDITIONS, SCORE_METHOD, build_native_receiver_task_score_receipt

BRIDGE_SCHEMA = "v14.native-receiver-task-matrix-bridge/1"
NATIVE_MATRIX_SCHEMA = "v14.native-receiver-task-matrix/1"
_ENVIRONMENTS = frozenset({"SYNTHETIC", "LOCAL_LINUX", "TERMUX_ANDROID", "REDMI"})


class NativeReceiverTaskMatrixBridgeError(ValueError):
    pass


def _is_sha256(value):
    return (
        type(value) is str
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _target_sha256(token_ids):
    try:
        payload = struct.pack("<" + "i" * len(token_ids), *token_ids)
    except (OverflowError, struct.error) as exc:
        raise NativeReceiverTaskMatrixBridgeError("target token IDs cannot be encoded as int32") from exc
    return hashlib.sha256(payload).hexdigest()


def _vectors_sha256(vectors):
    flat = []
    for row in vectors:
        for value in row:
            if type(value) not in (int, float) or not math.isfinite(float(value)):
                raise NativeReceiverTaskMatrixBridgeError("condition vectors contain non-finite values")
            flat.append(float(value))
    try:
        payload = struct.pack("<" + "f" * len(flat), *flat)
    except (OverflowError, struct.error) as exc:
        raise NativeReceiverTaskMatrixBridgeError("condition vectors cannot be encoded as float32") from exc
    return hashlib.sha256(payload).hexdigest()


def _validate_source(source_validator, receipt, phase):
    try:
        valid = source_validator(receipt, phase)
    except Exception as exc:
        raise NativeReceiverTaskMatrixBridgeError(
            "source/event/generation validator failed during " + phase
        ) from exc
    if valid is not True:
        raise NativeReceiverTaskMatrixBridgeError(
            "source/event/generation binding is no longer current during " + phase
        )


def _validate_matrix_inputs(receipt, inputs, target_sha, target_count):
    if not isinstance(inputs, list) or len(inputs) != len(CONDITIONS):
        raise NativeReceiverTaskMatrixBridgeError("approved matrix did not yield all eight conditions")
    if tuple(item.get("condition") for item in inputs if isinstance(item, Mapping)) != CONDITIONS:
        raise NativeReceiverTaskMatrixBridgeError("approved matrix condition order is invalid")

    sender = inputs[1].get("sender")
    receiver = inputs[1].get("receiver")
    if not isinstance(sender, Mapping) or not isinstance(receiver, Mapping):
        raise NativeReceiverTaskMatrixBridgeError("matrix sender/receiver bindings are missing")
    if dict(receiver) != dict(receipt["receiver"]):
        raise NativeReceiverTaskMatrixBridgeError("matrix receiver differs from its approval receipt")

    expected_dim = None
    for condition, item in zip(CONDITIONS, inputs):
        if not isinstance(item, Mapping):
            raise NativeReceiverTaskMatrixBridgeError("condition input is malformed")
        for key, expected in (
            ("task_group_id", receipt["task_group_id"]),
            ("task_family", receipt["task_family"]),
            ("session_id", receipt["session_id"]),
            ("source_ref", receipt["source_ref"]),
            ("context_sha256", receipt["context_sha256"]),
            ("target_token_ids_sha256", target_sha),
            ("target_token_count", target_count),
            ("receiver", receipt["receiver"]),
            ("sender", sender),
            ("position_mode", POSITION_MODE),
        ):
            if item.get(key) != expected:
                raise NativeReceiverTaskMatrixBridgeError(
                    condition + " condition is not bound to the approved task/organ"
                )
        if (item.get("persisted") is not False
                or item.get("production_route") is not False
                or item.get("semantic_use_proven") is not False
                or item.get("training_authority") != 0
                or item.get("native_receiver_authority") != 0):
            raise NativeReceiverTaskMatrixBridgeError("condition input carries forbidden authority")
        if not _is_sha256(item.get("input_sha256")):
            raise NativeReceiverTaskMatrixBridgeError("condition input digest is invalid")

        vectors = item.get("vectors")
        positions = item.get("position_ids")
        rows = item.get("input_rows")
        dim = item.get("input_dim")
        if condition == "NO_MESSAGE":
            if vectors != [] or positions != [] or rows != 0:
                raise NativeReceiverTaskMatrixBridgeError(
                    "NO_MESSAGE must contain zero injected rows and zero positions"
                )
            if item["input_sha256"] != hashlib.sha256(b"").hexdigest():
                raise NativeReceiverTaskMatrixBridgeError("NO_MESSAGE digest must bind the empty input")
            if type(dim) is not int or dim < 1:
                raise NativeReceiverTaskMatrixBridgeError("NO_MESSAGE receiver dimension is invalid")
            expected_dim = dim
            continue

        if (not isinstance(vectors, list) or not vectors or type(rows) is not int
                or rows != len(vectors) or type(dim) is not int or dim < 1
                or positions != list(range(rows))):
            raise NativeReceiverTaskMatrixBridgeError(condition + " vector geometry is invalid")
        if any(not isinstance(row, list) or len(row) != dim for row in vectors):
            raise NativeReceiverTaskMatrixBridgeError(condition + " vector dimensions are inconsistent")
        if _vectors_sha256(vectors) != item["input_sha256"]:
            raise NativeReceiverTaskMatrixBridgeError(condition + " vector digest changed after approval")
        if expected_dim is None:
            expected_dim = dim
        elif dim != expected_dim:
            raise NativeReceiverTaskMatrixBridgeError("condition input dimensions differ")
    return dict(sender), dict(receiver), expected_dim


def score_and_record_native_receiver_condition_matrix(
    runtime,
    matrix,
    *,
    approval,
    approval_validator,
    source_validator,
    target_token_ids,
    home,
    model_path,
    deadline,
    target_environment,
    threads=1,
    binary_path=None,
    cancel_event=None,
    device_execution_receipt_sha256=None,
    device_runtime_build_id=None,
):
    """Consume one approved matrix, score all conditions, and atomically record eight receipts.

    approval_validator must bind a real one-shot Runtime approval to the matrix
    digest. source_validator(receipt, phase) must re-check the current source
    bytes, event/generation and relevant Runtime lease both before and after
    native execution. A digest by itself is not approval.
    """
    condition_inputs = []
    native_result = None
    try:
        if not isinstance(matrix, NativeReceiverConditionMatrix):
            raise NativeReceiverTaskMatrixBridgeError("a live NativeReceiverConditionMatrix is required")
        if not callable(approval_validator) or not callable(source_validator):
            raise NativeReceiverTaskMatrixBridgeError("one-shot approval and source validators are required")
        if target_environment not in _ENVIRONMENTS:
            raise NativeReceiverTaskMatrixBridgeError("an explicit native execution environment is required")
        if type(threads) is not int or not 1 <= threads <= 2:
            raise NativeReceiverTaskMatrixBridgeError("native task-matrix threads must be 1 or 2")
        if type(deadline) not in (int, float) or not math.isfinite(float(deadline)):
            raise NativeReceiverTaskMatrixBridgeError("a finite monotonic deadline is required")
        if not isinstance(home, (str, Path)) or not str(home):
            raise NativeReceiverTaskMatrixBridgeError("native runtime home is required")
        if not isinstance(model_path, (str, Path)) or not str(model_path):
            raise NativeReceiverTaskMatrixBridgeError("installed receiver model path is required")
        if not isinstance(target_token_ids, (list, tuple)) or not 1 <= len(target_token_ids) <= 512:
            raise NativeReceiverTaskMatrixBridgeError("target token IDs must contain 1..512 int32 values")
        if any(type(value) is not int or value < 0 or value > 2147483647 for value in target_token_ids):
            raise NativeReceiverTaskMatrixBridgeError("target token IDs must be non-negative int32 values")

        receipt = matrix.receipt
        if not isinstance(receipt, Mapping) or receipt.get("schema") != MATRIX_SCHEMA:
            raise NativeReceiverTaskMatrixBridgeError("condition matrix schema mismatch")
        conditions = receipt.get("conditions")
        if (receipt.get("status") != "MATRIX_READY_NOT_SCORED"
                or receipt.get("condition_count") != len(CONDITIONS)
                or not isinstance(conditions, list)
                or tuple(item.get("condition") for item in conditions if isinstance(item, Mapping)) != CONDITIONS):
            raise NativeReceiverTaskMatrixBridgeError("condition matrix is incomplete or already scored")
        if (receipt.get("required_approval_kind") != REQUIRED_APPROVAL_KIND
                or receipt.get("approval_binding_kind") != "UNSIGNED_DIGEST_ONLY"
                or receipt.get("approval_granted") is not False):
            raise NativeReceiverTaskMatrixBridgeError("condition matrix approval contract is invalid")
        if (receipt.get("persisted") is not False
                or receipt.get("production_route") is not False
                or receipt.get("semantic_use_proven") is not False
                or receipt.get("training_authority") != 0
                or receipt.get("native_receiver_authority") != 0):
            raise NativeReceiverTaskMatrixBridgeError("condition matrix carries forbidden authority")
        if (not _is_sha256(receipt.get("matrix_sha256"))
                or not _is_sha256(receipt.get("approval_binding_sha256"))
                or not _is_sha256(receipt.get("context_sha256"))):
            raise NativeReceiverTaskMatrixBridgeError("condition matrix digest binding is invalid")

        session_id = receipt.get("session_id")
        if type(session_id) is not str or not session_id or getattr(runtime, "session", None) != session_id:
            raise NativeReceiverTaskMatrixBridgeError("task-score session differs from the active Runtime")
        token_ids = list(target_token_ids)
        target_sha = _target_sha256(token_ids)
        if (receipt.get("target_token_ids_sha256") != target_sha
                or receipt.get("target_token_count") != len(token_ids)):
            raise NativeReceiverTaskMatrixBridgeError("target token IDs differ from the approved task")

        source_ref = receipt.get("source_ref")
        if (not isinstance(source_ref, Mapping)
                or type(source_ref.get("source_id")) is not str
                or not source_ref.get("source_id")
                or not _is_sha256(source_ref.get("sha256"))):
            raise NativeReceiverTaskMatrixBridgeError("task source reference is malformed")
        generation_id = receipt.get("task_generation_id")
        if type(generation_id) is not str or not generation_id:
            raise NativeReceiverTaskMatrixBridgeError("task generation binding is missing")

        _validate_source(source_validator, receipt, "before")
        try:
            condition_inputs = list(
                matrix.iter_inputs(approval=approval, approval_validator=approval_validator)
            )
        except Exception as exc:
            raise NativeReceiverTaskMatrixBridgeError("matrix one-shot approval/input validation failed") from exc

        sender, receiver, input_dim = _validate_matrix_inputs(
            receipt, condition_inputs, target_sha, len(token_ids)
        )
        for label, binding in (("sender", sender), ("receiver", receiver)):
            if (type(binding.get("role")) is not str or type(binding.get("tap_id")) is not str
                    or type(binding.get("model_revision")) is not str
                    or not _is_sha256(binding.get("model_sha256"))
                    or type(binding.get("tokenizer_revision")) is not str):
                raise NativeReceiverTaskMatrixBridgeError(label + " manifest binding is incomplete")

        native_result = probe_matrix(
            home=home,
            model_path=model_path,
            expected_model_sha256=receiver["model_sha256"],
            sender_role=sender["role"],
            receiver_role=receiver["role"],
            sender_tap_id=sender["tap_id"],
            sender_model_revision=sender["model_revision"],
            sender_model_sha256=sender["model_sha256"],
            tokenizer_revision=sender["tokenizer_revision"],
            receiver_model_revision=receiver["model_revision"],
            source_id=source_ref["source_id"],
            generation_id=generation_id,
            condition_inputs=condition_inputs,
            target_token_ids=token_ids,
            position_mode=POSITION_MODE,
            deadline=deadline,
            threads=threads,
            binary_path=binary_path,
            cancel_event=cancel_event,
            target_environment=target_environment,
            device_execution_receipt_sha256=device_execution_receipt_sha256,
            device_runtime_build_id=device_runtime_build_id,
        )

        _validate_source(source_validator, receipt, "after")
        if getattr(runtime, "session", None) != session_id:
            raise NativeReceiverTaskMatrixBridgeError("Runtime session changed during native task-matrix scoring")
        if (not isinstance(native_result, Mapping)
                or native_result.get("schema") != NATIVE_MATRIX_SCHEMA
                or native_result.get("status") != "SCORED"
                or native_result.get("runner_revision") != PINNED_LLAMA_REVISION
                or native_result.get("sender_role") != sender["role"]
                or native_result.get("receiver_role") != receiver["role"]
                or native_result.get("sender_tap_id") != sender["tap_id"]
                or native_result.get("sender_model_revision") != sender["model_revision"]
                or native_result.get("sender_model_sha256") != sender["model_sha256"]
                or native_result.get("tokenizer_revision") != sender["tokenizer_revision"]
                or native_result.get("receiver_model_revision") != receiver["model_revision"]
                or native_result.get("receiver_model_sha256") != receiver["model_sha256"]
                or native_result.get("input_dim") != input_dim
                or type(native_result.get("output_dim")) is not int
                or native_result.get("output_dim") < 1
                or native_result.get("target_token_count") != len(token_ids)
                or native_result.get("target_token_ids_sha256") != target_sha
                or native_result.get("native_input_consumed") is not True
                or native_result.get("production_route") is not False
                or native_result.get("semantic_use_proven") is not False
                or native_result.get("training_authority") != 0
                or native_result.get("native_receiver_authority") != 0):
            raise NativeReceiverTaskMatrixBridgeError("native task-matrix result is missing or misbound")
        duration = native_result.get("duration_s")
        if type(duration) not in (int, float) or not math.isfinite(float(duration)) or duration < 0:
            raise NativeReceiverTaskMatrixBridgeError("native task-matrix duration is invalid")

        condition_scores = native_result.get("condition_scores")
        if not isinstance(condition_scores, Mapping) or set(condition_scores) != set(CONDITIONS):
            raise NativeReceiverTaskMatrixBridgeError("native result does not contain all eight condition scores")
        expected_kind, expected_env = (
            ("SYNTHETIC_FIXTURE", "SYNTHETIC")
            if target_environment == "SYNTHETIC"
            else ("NATIVE_LLAMA_CPP_GGUF", target_environment)
        )
        binary_sha = None
        llama_version = native_result.get("llama_version")
        if type(llama_version) is not str or not llama_version:
            raise NativeReceiverTaskMatrixBridgeError("native llama.cpp version is missing")
        score_receipts = []
        for condition, item in zip(CONDITIONS, condition_inputs):
            native_score = condition_scores[condition]
            if (not isinstance(native_score, Mapping)
                    or native_score.get("execution_kind") != expected_kind
                    or native_score.get("environment") != expected_env
                    or native_score.get("llama_cpp_revision") != PINNED_LLAMA_REVISION
                    or native_score.get("receiver_model_sha256") != receiver["model_sha256"]
                    or native_score.get("input_sha256") != item["input_sha256"]
                    or native_score.get("target_token_ids_sha256") != target_sha
                    or native_score.get("target_token_count") != len(token_ids)
                    or native_score.get("score_method") != SCORE_METHOD
                    or native_score.get("decode_status") != 0
                    or native_score.get("native_input_consumed") is not True
                    or native_score.get("llama_version") != llama_version
                    or not _is_sha256(native_score.get("binary_sha256"))):
                raise NativeReceiverTaskMatrixBridgeError(
                    "native target-score receipt is not bound to condition " + condition
                )
            if binary_sha is None:
                binary_sha = native_score["binary_sha256"]
            elif binary_sha != native_score["binary_sha256"]:
                raise NativeReceiverTaskMatrixBridgeError("native binary revision changed across conditions")

            score_receipts.append(build_native_receiver_task_score_receipt(
                condition=condition,
                task_group_id=receipt["task_group_id"],
                task_family=receipt["task_family"],
                session_id=session_id,
                source_ref=receipt["source_ref"],
                message_source_ref=item.get("message_source_ref"),
                receiver=receiver,
                target_token_ids_sha256=target_sha,
                target_token_count=len(token_ids),
                context_sha256=receipt["context_sha256"],
                input_sha256=item["input_sha256"],
                native_receipt=dict(native_score),
                adapter_sha256=item.get("adapter_sha256"),
            ))

        cohort = record_task_score_receipts(runtime, score_receipts)
        return {
            "schema": BRIDGE_SCHEMA,
            "status": "TASK_GROUP_SCORED",
            "cohort_status": cohort.get("status"),
            "evidence_class": cohort.get("evidence_class"),
            "task_group_id": receipt["task_group_id"],
            "task_group_count": cohort.get("task_group_count", 0),
            "complete_task_group_count": cohort.get("complete_task_group_count", 0),
            "incomplete_task_group_count": cohort.get("incomplete_task_group_count", 0),
            "condition_count": len(score_receipts),
            "matrix_sha256": receipt["matrix_sha256"],
            "approval_binding_sha256": receipt["approval_binding_sha256"],
            "execution_kind": expected_kind,
            "environment": expected_env,
            "duration_s": float(duration),
            "score_method": SCORE_METHOD,
            "enough_holdout": cohort.get("enough_holdout", False),
            "candidate_beats_all_controls": cohort.get("candidate_beats_all_controls", False),
            "semantic_use_proven": False,
            "generated_answer_correctness_proven": False,
            "production_route": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
            "persisted": False,
        }
    except NativeReceiverTaskMatrixBridgeError:
        raise
    except Exception as exc:
        raise NativeReceiverTaskMatrixBridgeError("native receiver task-matrix bridge failed") from exc
    finally:
        condition_inputs.clear()
        native_result = None
        if isinstance(matrix, NativeReceiverConditionMatrix):
            matrix.close()
