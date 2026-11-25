"""Ephemeral collector for source-bound native receiver target-score receipts.

This is a diagnostic cohort buffer only. It never persists target text, token IDs,
vectors or receipts, and never grants production, training or B3 authority.
"""
from __future__ import annotations

from collections import defaultdict

from .native_receiver_utility import (
    CONDITIONS,
    NativeReceiverUtilityError,
    _check_receipt,
    build_native_receiver_task_score_receipt,
    evaluate_native_receiver_task_utility,
)

MAX_TASK_SCORE_RECEIPTS = 160


class NativeReceiverTaskScoreError(ValueError):
    pass


def _receipt_buffer(runtime):
    value = getattr(runtime, "_native_receiver_task_score_receipts", None)
    if value is None:
        value = []
        try:
            setattr(runtime, "_native_receiver_task_score_receipts", value)
        except (AttributeError, TypeError) as exc:
            raise NativeReceiverTaskScoreError("Runtime cannot hold an ephemeral task-score cohort") from exc
    if not isinstance(value, list):
        raise NativeReceiverTaskScoreError("Runtime task-score buffer is malformed")
    return value


def task_score_status(runtime):
    """Return counts only; never expose token scores or source content."""
    receipts = _receipt_buffer(runtime)
    groups = defaultdict(set)
    for item in receipts:
        checked = _check_receipt(item)
        groups[checked["task_group_id"]].add(checked["condition"])
    complete = sum(conditions == set(CONDITIONS) for conditions in groups.values())
    incomplete = len(groups) - complete
    return {
        "status": "COLLECTING" if incomplete else ("EMPTY" if not groups else "COHORT_READY"),
        "receipt_count": len(receipts),
        "task_group_count": len(groups),
        "complete_task_group_count": complete,
        "incomplete_task_group_count": incomplete,
        "required_conditions_per_task": len(CONDITIONS),
        "maximum_receipts": MAX_TASK_SCORE_RECEIPTS,
        "persisted": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }


def record_task_score_receipt(runtime, receipt):
    """Add one verified ephemeral receipt; evaluate only complete condition groups."""
    try:
        checked = _check_receipt(receipt)
    except NativeReceiverUtilityError as exc:
        raise NativeReceiverTaskScoreError("task-score receipt rejected") from exc
    receipts = _receipt_buffer(runtime)
    if len(receipts) >= MAX_TASK_SCORE_RECEIPTS:
        raise NativeReceiverTaskScoreError("ephemeral task-score cohort is full; export no data and reset explicitly")
    key = (checked["task_group_id"], checked["condition"])
    if any((item.get("task_group_id"), item.get("condition")) == key for item in receipts):
        raise NativeReceiverTaskScoreError("duplicate task group/condition receipt")
    receipts.append(checked)
    status = task_score_status(runtime)
    if status["incomplete_task_group_count"]:
        return status
    try:
        return evaluate_native_receiver_task_utility(receipts)
    except NativeReceiverUtilityError as exc:
        raise NativeReceiverTaskScoreError("complete task-score cohort failed validation") from exc


def build_and_record_task_score_receipt(runtime, *, condition, task_group_id, task_family,
        session_id, source_ref, message_source_ref, receiver, target_token_ids_sha256,
        target_token_count, context_sha256, input_sha256, native_receipt, adapter_sha256=None):
    """Build a hash/source-bound receipt and add it to the in-memory cohort."""
    if session_id != getattr(runtime, "session", None):
        raise NativeReceiverTaskScoreError("task-score session differs from the active Runtime session")
    receipt = build_native_receiver_task_score_receipt(
        condition=condition,
        task_group_id=task_group_id,
        task_family=task_family,
        session_id=session_id,
        source_ref=source_ref,
        message_source_ref=message_source_ref,
        receiver=receiver,
        target_token_ids_sha256=target_token_ids_sha256,
        target_token_count=target_token_count,
        context_sha256=context_sha256,
        input_sha256=input_sha256,
        native_receipt=native_receipt,
        adapter_sha256=adapter_sha256,
    )
    return receipt, record_task_score_receipt(runtime, receipt)


def evaluate_task_score_cohort(runtime):
    """Evaluate a complete cohort; incomplete groups remain COLLECTING."""
    receipts = _receipt_buffer(runtime)
    status = task_score_status(runtime)
    if not receipts:
        return status
    if status["incomplete_task_group_count"]:
        return status
    try:
        return evaluate_native_receiver_task_utility(receipts)
    except NativeReceiverUtilityError as exc:
        raise NativeReceiverTaskScoreError("task-score cohort failed validation") from exc


def clear_task_score_cohort(runtime):
    """Explicitly discard ephemeral score receipts; no disk or Store writes."""
    receipts = _receipt_buffer(runtime)
    count = len(receipts)
    receipts.clear()
    return {"status": "CLEARED", "discarded_receipt_count": count, "persisted": False,
            "training_authority": 0, "native_receiver_authority": 0}
