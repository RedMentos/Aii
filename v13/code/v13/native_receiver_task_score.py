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


MIN_TASK_GROUPS = 20
MIN_SESSIONS = 2
MIN_TASK_FAMILIES = 2
MIN_TASKS_PER_SESSION = 5
MIN_TASKS_PER_FAMILY = 4


def _status_for_receipts(receipts):
    groups = defaultdict(set)
    metadata = {}
    for item in receipts:
        checked = _check_receipt(item)
        task_id = checked["task_group_id"]
        groups[task_id].add(checked["condition"])
        metadata[task_id] = (checked["session_id"], checked["task_family"])
    complete = {
        task_id for task_id, conditions in groups.items()
        if conditions == set(CONDITIONS)
    }
    incomplete = len(groups) - len(complete)
    sessions = defaultdict(int)
    families = defaultdict(int)
    for task_id in complete:
        session_id, task_family = metadata[task_id]
        sessions[session_id] += 1
        families[task_family] += 1
    ready = (
        not incomplete
        and len(complete) >= MIN_TASK_GROUPS
        and len(sessions) >= MIN_SESSIONS
        and len(families) >= MIN_TASK_FAMILIES
        and all(count >= MIN_TASKS_PER_SESSION for count in sessions.values())
        and all(count >= MIN_TASKS_PER_FAMILY for count in families.values())
    )
    return {
        "status": "EMPTY" if not groups else ("COHORT_READY" if ready else "COLLECTING"),
        "receipt_count": len(receipts),
        "task_group_count": len(groups),
        "complete_task_group_count": len(complete),
        "incomplete_task_group_count": incomplete,
        "session_count": len(sessions),
        "task_family_count": len(families),
        "minimum_task_groups": MIN_TASK_GROUPS,
        "minimum_sessions": MIN_SESSIONS,
        "minimum_task_families": MIN_TASK_FAMILIES,
        "minimum_tasks_per_session": MIN_TASKS_PER_SESSION,
        "minimum_tasks_per_family": MIN_TASKS_PER_FAMILY,
        "required_conditions_per_task": len(CONDITIONS),
        "maximum_receipts": MAX_TASK_SCORE_RECEIPTS,
        "persisted": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }


def task_score_status(runtime):
    """Return counts only; never expose token scores or source content."""
    return _status_for_receipts(_receipt_buffer(runtime))


def record_task_score_receipts(runtime, receipts):
    """Atomically add a bounded receipt batch; evaluate only a fully qualified cohort."""
    if not isinstance(receipts, (list, tuple)) or not receipts or len(receipts) > len(CONDITIONS):
        raise NativeReceiverTaskScoreError("task-score batch must contain 1..8 receipts")
    try:
        checked = [_check_receipt(item) for item in receipts]
    except NativeReceiverUtilityError as exc:
        raise NativeReceiverTaskScoreError("task-score receipt rejected") from exc
    existing = _receipt_buffer(runtime)
    if len(existing) + len(checked) > MAX_TASK_SCORE_RECEIPTS:
        raise NativeReceiverTaskScoreError("ephemeral task-score cohort is full; export no data and reset explicitly")
    existing_keys = {(item.get("task_group_id"), item.get("condition")) for item in existing}
    batch_keys = [(item["task_group_id"], item["condition"]) for item in checked]
    if len(set(batch_keys)) != len(batch_keys) or any(key in existing_keys for key in batch_keys):
        raise NativeReceiverTaskScoreError("duplicate task group/condition receipt")
    candidate = existing + checked
    status = _status_for_receipts(candidate)
    if status["status"] == "COHORT_READY":
        try:
            result = evaluate_native_receiver_task_utility(candidate)
        except NativeReceiverUtilityError as exc:
            raise NativeReceiverTaskScoreError("complete task-score cohort failed validation") from exc
        existing.extend(checked)
        return result
    existing.extend(checked)
    return status


def record_task_score_receipt(runtime, receipt):
    """Add one verified ephemeral receipt; evaluate only a fully qualified cohort."""
    return record_task_score_receipts(runtime, [receipt])


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
