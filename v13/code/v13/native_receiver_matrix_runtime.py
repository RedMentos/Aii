"""Core-owned Runtime consumer for the Perception eight-condition native receiver matrix.

The matrix is staged in memory only. A separate local-TTY one-shot approval binds
its exact digest, source/event/generation set and installed sender/receiver bytes.
The native run is serial, diagnostic-only and LOCAL_LINUX until a verified Android
device-receipt path is integrated.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import secrets
import stat
import struct
import time
from collections.abc import Mapping
from pathlib import Path

from . import native_probe_approval as approval
from .common import dumps
from .models import platform_tag
from .native_receiver_utility import CONDITIONS, TASK_FAMILIES

KEY = "v14.native_receiver_matrix_approval"
SCHEMA = "v14.native-receiver-matrix-runtime-approval/1"
TTL_SECONDS = 120
MAX_TARGET_TOKENS = 512
_ALLOWED_SENDER = frozenset({"B1_DETAIL", "B2_GIST"})
_ALLOWED_RECEIVER = frozenset({"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"})


class NativeReceiverMatrixRuntimeError(ValueError):
    """The approved Runtime-to-native matrix contract failed closed."""


def _sha(value, name):
    if (type(value) is not str or len(value) != 64
            or any(ch not in "0123456789abcdef" for ch in value)):
        raise NativeReceiverMatrixRuntimeError(name + " must be lowercase SHA-256")
    return value


def _source_key(value, name):
    if not isinstance(value, Mapping):
        raise NativeReceiverMatrixRuntimeError(name + " source binding is missing")
    source_id = value.get("source_id")
    digest = _sha(value.get("sha256"), name + ".sha256")
    if type(source_id) is not str or not source_id or len(source_id) > 256:
        raise NativeReceiverMatrixRuntimeError(name + " source ID is invalid")
    return source_id, digest


def _target_ids(values, receipt):
    if (not isinstance(values, (list, tuple)) or not 1 <= len(values) <= MAX_TARGET_TOKENS
            or any(type(value) is not int or value < 0 or value > 2147483647 for value in values)):
        raise NativeReceiverMatrixRuntimeError("target token IDs must be 1..512 non-negative int32 values")
    try:
        digest = hashlib.sha256(struct.pack("<" + "i" * len(values), *values)).hexdigest()
    except (OverflowError, struct.error) as exc:
        raise NativeReceiverMatrixRuntimeError("target token IDs cannot be encoded as int32") from exc
    if (receipt.get("target_token_count") != len(values)
            or receipt.get("target_token_ids_sha256") != digest):
        raise NativeReceiverMatrixRuntimeError("target token IDs differ from the matrix's exact C3 target binding")
    return tuple(values)


def _matrix_receipt(matrix):
    if (matrix is None or not callable(getattr(matrix, "iter_inputs", None))
            or getattr(matrix, "_consumed", False) is not False
            or not callable(getattr(matrix, "close", None))
            or not callable(getattr(matrix, "_build_one", None))):
        raise NativeReceiverMatrixRuntimeError("an open one-shot NativeReceiverConditionMatrix is required")
    receipt = matrix.receipt
    if not isinstance(receipt, Mapping):
        raise NativeReceiverMatrixRuntimeError("matrix receipt is not an object")
    receipt = dict(receipt)
    if (receipt.get("schema") != "v14.native-receiver-condition-matrix/1"
            or receipt.get("status") != "MATRIX_READY_NOT_SCORED"
            or receipt.get("required_approval_kind") != "NATIVE_RECEIVER_MATRIX"
            or receipt.get("approval_binding_kind") != "UNSIGNED_DIGEST_ONLY"
            or receipt.get("approval_granted") is not False
            or receipt.get("condition_count") != len(CONDITIONS)
            or not isinstance(receipt.get("conditions"), list)
            or tuple(item.get("condition") for item in receipt["conditions"]
                     if isinstance(item, Mapping)) != CONDITIONS):
        raise NativeReceiverMatrixRuntimeError("matrix is not a complete unsigned eight-condition candidate")
    if (receipt.get("persisted") is not False
            or receipt.get("production_route") is not False
            or receipt.get("semantic_use_proven") is not False
            or receipt.get("training_authority") != 0
            or receipt.get("native_receiver_authority") != 0):
        raise NativeReceiverMatrixRuntimeError("matrix carries forbidden persistence, production or learning authority")
    _sha(receipt.get("matrix_sha256"), "matrix_sha256")
    _sha(receipt.get("approval_binding_sha256"), "approval_binding_sha256")
    _sha(receipt.get("context_sha256"), "context_sha256")
    _sha(receipt.get("adapter_sha256"), "adapter_sha256")
    _sha(receipt.get("target_token_ids_sha256"), "target_token_ids_sha256")
    if type(receipt.get("target_token_count")) is not int or not 1 <= receipt["target_token_count"] <= MAX_TARGET_TOKENS:
        raise NativeReceiverMatrixRuntimeError("matrix target token count is invalid")
    for field in ("task_group_id", "session_id", "task_event_id", "task_generation_id"):
        if type(receipt.get(field)) is not str or not receipt[field] or len(receipt[field]) > 256:
            raise NativeReceiverMatrixRuntimeError("matrix " + field + " is invalid")
    if receipt.get("task_family") not in TASK_FAMILIES:
        raise NativeReceiverMatrixRuntimeError("matrix task family is unsupported")
    _source_key(receipt.get("source_ref"), "task")
    receiver = receipt.get("receiver")
    if not isinstance(receiver, Mapping):
        raise NativeReceiverMatrixRuntimeError("matrix receiver binding is missing")
    if (receiver.get("role") not in _ALLOWED_RECEIVER
            or any(type(receiver.get(key)) is not str or not receiver[key]
                   for key in ("tap_id", "model_revision", "tokenizer_revision"))
            or _sha(receiver.get("model_sha256"), "receiver.model_sha256") != receiver.get("model_sha256")):
        raise NativeReceiverMatrixRuntimeError("matrix receiver model/tap binding is invalid")
    bindings = receipt.get("source_bindings")
    if not isinstance(bindings, list) or len(bindings) != 3:
        raise NativeReceiverMatrixRuntimeError("matrix must bind exactly three disjoint source records")
    keys = [_source_key(item, "matrix source") for item in bindings]
    if len(set(keys)) != 3 or len({key[0] for key in keys}) != 3 or len({key[1] for key in keys}) != 3:
        raise NativeReceiverMatrixRuntimeError("matrix source bindings are not disjoint")
    return receipt


def _pair_bindings(pair_record, receipt):
    if not isinstance(pair_record, Mapping):
        raise NativeReceiverMatrixRuntimeError("the main source-paired sender/receiver record is required")
    from . import native_tokenwise_pairing
    try:
        record = native_tokenwise_pairing._validate_native_pair_record(pair_record)
    except Exception as exc:
        raise NativeReceiverMatrixRuntimeError("main tokenwise pair record failed its source/manifest checks") from exc
    if (record.get("status") != "PAIRED_DIAGNOSTIC"
            or record.get("persisted") is not False
            or record.get("production_route") is not False
            or record.get("semantic_use_proven") is not False
            or record.get("training_authority") != 0
            or record.get("native_receiver_authority") != 0):
        raise NativeReceiverMatrixRuntimeError("main pair record carries forbidden authority")
    if (record.get("session_id") != receipt["session_id"]
            or record.get("event_id") != receipt["task_event_id"]
            or record.get("brain_generation_id") != receipt["task_generation_id"]
            or _source_key(record.get("source_ref"), "pair record") != _source_key(receipt["source_ref"], "matrix task")):
        raise NativeReceiverMatrixRuntimeError("main pair record differs from the matrix task source/event/generation")
    sender_raw, receiver_raw = record.get("sender"), record.get("receiver")
    if not isinstance(sender_raw, Mapping) or not isinstance(receiver_raw, Mapping):
        raise NativeReceiverMatrixRuntimeError("main pair record lacks sender/receiver bindings")

    def clean_binding(value, label):
        clean = {}
        for key in ("role", "tap_id", "model_revision", "tokenizer_revision"):
            item = value.get(key)
            if type(item) is not str or not item or len(item) > 256:
                raise NativeReceiverMatrixRuntimeError(label + "." + key + " is invalid")
            clean[key] = item
        clean["model_sha256"] = _sha(value.get("model_sha256"), label + ".model_sha256")
        return clean

    sender = clean_binding(sender_raw, "sender")
    receiver = clean_binding(receiver_raw, "receiver")
    if (sender.get("role") not in _ALLOWED_SENDER
            or receiver.get("role") not in _ALLOWED_RECEIVER
            or sender.get("role") == receiver.get("role")):
        raise NativeReceiverMatrixRuntimeError("main pair record has invalid organ roles")
    if receiver != dict(receipt["receiver"]):
        raise NativeReceiverMatrixRuntimeError("main pair receiver differs from the matrix receiver")
    return record, sender, receiver


def _model_bindings(runtime, sender, receiver):
    result = {}
    for role, expected in ((sender["role"], sender), (receiver["role"], receiver)):
        actual = approval._model_binding(runtime, role)
        if (actual.get("revision") != expected.get("model_revision")
                or actual.get("sha256") != expected.get("model_sha256")):
            raise PermissionError("installed " + role + " model differs from the source-paired matrix binding")
        result[role] = actual
    return result


def _event_bindings(receipt):
    by_condition = {item["condition"]: item for item in receipt["conditions"]}
    bindings = [
        (receipt["task_event_id"], receipt["task_generation_id"], receipt["source_ref"], "task"),
    ]
    for condition in ("OOD", "ENTITY_SUBSTITUTION"):
        item = by_condition.get(condition)
        if not isinstance(item, Mapping):
            raise NativeReceiverMatrixRuntimeError(condition + " source/event binding is missing")
        bindings.append((
            item.get("message_event_id"),
            item.get("message_generation_id"),
            item.get("message_source_ref"),
            condition.lower(),
        ))
    normalized = []
    for event_id, generation_id, source_ref, label in bindings:
        if (type(event_id) is not str or not event_id or type(generation_id) is not str
                or not generation_id):
            raise NativeReceiverMatrixRuntimeError(label + " event/generation binding is invalid")
        normalized.append((event_id, generation_id, _source_key(source_ref, label), label))
    if len({item[0] for item in normalized}) != 3:
        raise NativeReceiverMatrixRuntimeError("task, OOD and entity controls must use three distinct events")
    if len({item[2][0] for item in normalized}) != 3 or len({item[2][1] for item in normalized}) != 3:
        raise NativeReceiverMatrixRuntimeError("task, OOD and entity controls must use three distinct sources")
    expected = set(normalized_item[2] for normalized_item in normalized)
    recorded = set(_source_key(item, "matrix source") for item in receipt["source_bindings"])
    if expected != recorded:
        raise NativeReceiverMatrixRuntimeError("matrix source list differs from its condition event bindings")
    return normalized


def _validate_event_source(runtime, session_id, event_id, generation_id, expected_source, label):
    row = runtime.store.one(
        "SELECT packet,session_id FROM events WHERE id=?",
        (event_id,),
    )
    if not row or row["session_id"] != session_id:
        raise PermissionError(label + " event is missing or crossed the active matrix session")
    try:
        event = json.loads(row["packet"])
    except (TypeError, ValueError) as exc:
        raise PermissionError(label + " event packet is malformed") from exc
    if (not isinstance(event, dict)
            or event.get("event_id") != event_id
            or event.get("brain_generation_id") != generation_id
            or event.get("authority") != "AUTHORITATIVE"
            or event.get("kind") != "USER_TEXT"):
        raise PermissionError(label + " event authority or generation changed")
    source_ref = event.get("source_ref")
    if (not isinstance(source_ref, dict)
            or source_ref.get("modality") != "text"
            or _source_key(source_ref, label) != expected_source):
        raise PermissionError(label + " event no longer points to the approved source")
    text = runtime.store.read_source(source_ref)
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != expected_source[1]:
        raise PermissionError(label + " source bytes changed or were revoked")
    return True


def _validate_matrix_sources(runtime, receipt, *, require_current=True):
    if runtime.session != receipt.get("session_id"):
        raise PermissionError("native receiver matrix crossed the active Runtime session")
    if require_current:
        event, source_ref = approval._current_event(runtime)
        if (event.get("event_id") != receipt.get("task_event_id")
                or event.get("brain_generation_id") != receipt.get("task_generation_id")
                or _source_key(source_ref, "current task") != _source_key(receipt.get("source_ref"), "matrix task")):
            raise PermissionError("matrix task is no longer the latest completed authoritative user source")
    for event_id, generation_id, source_key, label in _event_bindings(receipt):
        _validate_event_source(
            runtime, receipt["session_id"], event_id, generation_id, source_key, label
        )
    return True


def stage_native_receiver_matrix(runtime, matrix, target_token_ids, pair_record):
    """Stage a Perception-built matrix in memory; this grants no native authority."""
    runtime.require_idle()
    if getattr(runtime, "_native_receiver_condition_matrix", None) is not None:
        raise PermissionError("clear the already-staged native receiver matrix before staging another")
    pending, pending_version = runtime.store.state(KEY, None)
    if (isinstance(pending, dict) and pending.get("schema") == SCHEMA
            and pending.get("status") == "PENDING"):
        liveness = _approval_liveness(runtime, pending)
        if liveness == "PENDING":
            raise PermissionError("revoke the live pending native receiver matrix approval before staging another")
        _invalidate_stale_approval(runtime, pending, pending_version, liveness)
    receipt = _matrix_receipt(matrix)
    ids = _target_ids(target_token_ids, receipt)
    record, sender, receiver = _pair_bindings(pair_record, receipt)
    _validate_matrix_sources(runtime, receipt, require_current=True)
    runtime._native_receiver_condition_matrix = matrix
    runtime._native_receiver_matrix_target_token_ids = ids
    runtime._native_receiver_matrix_pair_record = record
    runtime._native_receiver_matrix_staged_at = time.time()
    return {
        "schema": SCHEMA,
        "status": "STAGED_NOT_APPROVED",
        "task_group_id": receipt["task_group_id"],
        "task_family": receipt["task_family"],
        "session_id": receipt["session_id"],
        "task_event_id": receipt["task_event_id"],
        "matrix_sha256": receipt["matrix_sha256"],
        "approval_binding_sha256": receipt["approval_binding_sha256"],
        "condition_count": receipt["condition_count"],
        "source_count": len(receipt["source_bindings"]),
        "sender_role": sender["role"],
        "receiver_role": receiver["role"],
        "persisted": False,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }


def build_and_stage_native_receiver_matrix(
    runtime, *, task, pair_record, baseline_packet, candidate_packet, ood_control, entity_control
):
    """Perception-facing adapter: build the matrix, then stage it for Core's Runtime consumer."""
    from .native_receiver_condition_matrix import build_native_receiver_condition_matrix
    matrix = build_native_receiver_condition_matrix(
        task=task,
        pair_record=pair_record,
        baseline_packet=baseline_packet,
        candidate_packet=candidate_packet,
        ood_control=ood_control,
        entity_control=entity_control,
    )
    return stage_native_receiver_matrix(
        runtime, matrix, task.get("target_token_ids"), pair_record
    )


def _staged(runtime):
    matrix = getattr(runtime, "_native_receiver_condition_matrix", None)
    pair_record = getattr(runtime, "_native_receiver_matrix_pair_record", None)
    target_ids = getattr(runtime, "_native_receiver_matrix_target_token_ids", None)
    if matrix is None:
        raise PermissionError("no Perception-built native receiver condition matrix is staged")
    receipt = _matrix_receipt(matrix)
    ids = _target_ids(target_ids, receipt)
    record, sender, receiver = _pair_bindings(pair_record, receipt)
    return matrix, receipt, ids, record, sender, receiver


def _model_snapshot_matches(runtime, record):
    _matrix, receipt, _ids, _pair, sender, receiver = _staged(runtime)
    models = _model_bindings(runtime, sender, receiver)
    if record is not None and models != record.get("models"):
        raise PermissionError("installed sender/receiver model identity changed after matrix approval")
    return models, sender, receiver


def _valid_expiry(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _valid_approval_window(record, *, now=None):
    if not isinstance(record, dict):
        return False
    issued_at = record.get("issued_at")
    expires_at = record.get("expires_at")
    if not _valid_expiry(issued_at) or not _valid_expiry(expires_at):
        return False
    current_time = time.time() if now is None else now
    issued = float(issued_at)
    expires = float(expires_at)
    lifetime = expires - issued
    if lifetime <= 0 or lifetime > TTL_SECONDS + 2:
        return False
    if issued > current_time + 2:
        return False
    if current_time < expires and current_time - issued > TTL_SECONDS + 2:
        return False
    return True


def _model_route_is_current(runtime, record, sender, receiver):
    """Cheaply detect model-route drift; native execution still rehashes the full GGUF."""
    models = record.get("models")
    if not isinstance(models, dict):
        return False
    for role, expected in ((sender["role"], sender), (receiver["role"], receiver)):
        binding = models.get(role)
        if not isinstance(binding, dict):
            return False
        if (binding.get("revision") != expected.get("model_revision")
                or binding.get("sha256") != expected.get("model_sha256")):
            return False
        if runtime.models.revision(role) != binding.get("revision"):
            return False
        selected_path = Path(runtime.models.path_for(role))
        if selected_path.is_symlink():
            return False
        resolved = selected_path.resolve(strict=True)
        if str(resolved) != binding.get("canonical_path"):
            return False
        selected_stat = os.stat(selected_path, follow_symlinks=False)
        if not stat.S_ISREG(selected_stat.st_mode):
            return False
        identity = [
            selected_stat.st_dev, selected_stat.st_ino, selected_stat.st_size,
            selected_stat.st_mtime_ns, selected_stat.st_ctime_ns,
        ]
        if identity != binding.get("file_identity"):
            return False
    return True


def _approval_liveness(runtime, record, *, now=None):
    """Classify a persisted one-shot approval without changing Store state."""
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        return "NONE"
    if record.get("status") != "PENDING":
        return record.get("status") if type(record.get("status")) is str else "INVALID_RECORD"

    current_time = time.time() if now is None else now
    expires_at = record.get("expires_at")
    if not _valid_approval_window(record, now=current_time):
        return "INVALID_EXPIRY"
    if current_time >= expires_at:
        return "EXPIRED"

    runtime_nonce = getattr(runtime, "_native_probe_approval_runtime_nonce", None)
    if type(runtime_nonce) is not str or runtime_nonce != record.get("runtime_nonce"):
        return "STALE_RUNTIME"

    try:
        _matrix, receipt, _target_ids, _pair, sender, receiver = _staged(runtime)
    except Exception:
        return "STALE_MATRIX"
    try:
        if not _model_route_is_current(runtime, record, sender, receiver):
            return "STALE_MODEL"
    except Exception:
        return "STALE_MODEL"
    for field in (
        "matrix_sha256", "approval_binding_sha256", "session_id",
        "task_event_id", "task_generation_id", "task_group_id",
    ):
        if record.get(field) != receipt.get(field):
            return "STALE_MATRIX"
    if (record.get("source_bindings") != list(receipt.get("source_bindings", []))
            or record.get("sender_role") != sender.get("role")
            or record.get("receiver_role") != receiver.get("role")):
        return "STALE_MATRIX"
    try:
        _validate_matrix_sources(runtime, receipt, require_current=True)
    except Exception:
        return "STALE_SOURCE"
    return "PENDING"


def _invalidate_stale_approval(runtime, record, version, reason):
    if reason not in {"EXPIRED", "INVALID_EXPIRY", "STALE_RUNTIME", "STALE_MATRIX", "STALE_MODEL", "STALE_SOURCE"}:
        reason = "STALE_APPROVAL"
    updated = dict(record)
    updated.update({
        "status": reason,
        "invalidated_at": time.time(),
        "invalidated_reason": reason,
    })
    runtime.store.set_state(KEY, updated, expected=version)
    return updated


def _approval_record(runtime):
    record, version = runtime.store.state(KEY, None)
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise PermissionError("native receiver matrix has no local one-shot approval")
    return record, version


def _arm(runtime):
    approval._require_local_tty()
    runtime.require_idle()
    matrix, receipt, _ids, _pair, sender, receiver = _staged(runtime)
    _validate_matrix_sources(runtime, receipt, require_current=True)
    models = _model_bindings(runtime, sender, receiver)
    other, _ = runtime.store.state(approval.KEY, None)
    if isinstance(other, dict) and other.get("status") == "PENDING":
        expires = other.get("expires_at")
        if type(expires) in (int, float) and time.time() < expires:
            raise PermissionError("revoke the separate native probe approval before arming a matrix")
    current, version = runtime.store.state(KEY, None)
    if isinstance(current, dict) and current.get("schema") == SCHEMA and current.get("status") == "PENDING":
        liveness = _approval_liveness(runtime, current)
        if liveness == "PENDING":
            raise PermissionError("a live native receiver matrix approval is already pending; revoke it first")
        _invalidate_stale_approval(runtime, current, version, liveness)
        current, version = runtime.store.state(KEY, None)
    nonce = secrets.token_hex(16)
    record = {
        "schema": SCHEMA,
        "status": "PENDING",
        "nonce": nonce,
        "runtime_nonce": approval._runtime_nonce(runtime),
        "issued_at": time.time(),
        "expires_at": int(time.time()) + TTL_SECONDS,
        "session_id": receipt["session_id"],
        "task_event_id": receipt["task_event_id"],
        "task_generation_id": receipt["task_generation_id"],
        "task_group_id": receipt["task_group_id"],
        "matrix_sha256": receipt["matrix_sha256"],
        "approval_binding_sha256": receipt["approval_binding_sha256"],
        "source_bindings": list(receipt["source_bindings"]),
        "sender_role": sender["role"],
        "receiver_role": receiver["role"],
        "models": models,
    }
    runtime.store.set_state(KEY, record, expected=version)
    return {
        "schema": SCHEMA,
        "status": "ARMED_ONE_SHOT",
        "approval_id": nonce,
        "expires_at": record["expires_at"],
        "matrix_sha256": receipt["matrix_sha256"],
        "approval_binding_sha256": receipt["approval_binding_sha256"],
        "condition_count": receipt["condition_count"],
        "execution_authority": "NONE_UNTIL_MATRIX_RUN",
    }


def _consume_approval(runtime, nonce, expected_binding_sha256, receipt, lease_token):
    approval._require_runtime_probe_lease(runtime, lease_token)
    record, version = _approval_record(runtime)
    now = time.time()
    liveness = _approval_liveness(runtime, record, now=now)
    if liveness != "PENDING":
        raise PermissionError(
            "one-shot NATIVE_RECEIVER_MATRIX approval is not live: " + liveness
        )
    if (record.get("nonce") != nonce
            or record.get("runtime_nonce") != approval._runtime_nonce(runtime)
            or record.get("matrix_sha256") != receipt.get("matrix_sha256")
            or record.get("approval_binding_sha256") != expected_binding_sha256
            or expected_binding_sha256 != receipt.get("approval_binding_sha256")
            or record.get("session_id") != receipt.get("session_id")
            or record.get("task_event_id") != receipt.get("task_event_id")
            or record.get("task_generation_id") != receipt.get("task_generation_id")):
        raise PermissionError("one-shot NATIVE_RECEIVER_MATRIX approval does not bind this exact live matrix")
    updated = dict(record)
    updated.update({"status": "CONSUMED", "consumed_at": now})
    runtime.store.set_state(KEY, updated, expected=version)
    return True


def _revoke(runtime, status="REVOKED"):
    record, version = runtime.store.state(KEY, None)
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        return {"schema": SCHEMA, "status": "NO_APPROVAL"}
    if record.get("status") == "PENDING":
        updated = dict(record)
        updated.update({"status": status, "revoked_at": time.time()})
        runtime.store.set_state(KEY, updated, expected=version)
        return {"schema": SCHEMA, "status": status}
    return {"schema": SCHEMA, "status": record.get("status", "NO_APPROVAL")}


def _run(runtime):
    approval._require_local_tty()
    runtime.require_idle()
    matrix, receipt, target_ids, _pair, sender, receiver = _staged(runtime)
    record, _version = _approval_record(runtime)
    now = time.time()
    liveness = _approval_liveness(runtime, record, now=now)
    if (liveness != "PENDING"
            or record.get("runtime_nonce") != approval._runtime_nonce(runtime)
            or record.get("matrix_sha256") != receipt["matrix_sha256"]
            or record.get("approval_binding_sha256") != receipt["approval_binding_sha256"]
            or record.get("session_id") != receipt["session_id"]
            or record.get("task_event_id") != receipt["task_event_id"]
            or record.get("task_generation_id") != receipt["task_generation_id"]):
        raise PermissionError(
            "fresh matching :callosum matrix-arm --confirm approval is required"
            + (": " + liveness if liveness != "PENDING" else "")
        )
    try:
        _validate_matrix_sources(runtime, receipt, require_current=True)
    except BaseException as exc:
        state, version = runtime.store.state(KEY, None)
        if isinstance(state, dict) and state.get("schema") == SCHEMA and state.get("status") == "PENDING":
            state = dict(state)
            state.update({"status": "FAILED_REVOKED", "failure_kind": type(exc).__name__})
            runtime.store.set_state(KEY, state, expected=version)
        try:
            matrix.close()
        except Exception:
            pass
        runtime._native_receiver_condition_matrix = None
        runtime._native_receiver_matrix_target_token_ids = None
        runtime._native_receiver_matrix_pair_record = None
        runtime._native_receiver_matrix_staged_at = None
        raise
    environment = platform_tag()
    if not environment.startswith("linux"):
        raise PermissionError(
            "native matrix execution on Android requires a verified private device-execution receipt; "
            "TERMUX_ANDROID/REDMI remain UNVERIFIED"
        )

    try:
        from .native_receiver_task_matrix_bridge import score_and_record_native_receiver_condition_matrix
    except ImportError as exc:
        raise PermissionError(
            "Perception native matrix bridge is not integrated yet; no model was loaded and approval remains staged"
        ) from exc

    bridge_started = False
    try:
        with approval.runtime_probe_lease(runtime) as lease_token:
            approval._require_runtime_probe_lease(runtime, lease_token)
            models, sender, receiver = _model_snapshot_matches(runtime, record)
            resource = approval._resource_preflight(runtime, models[receiver["role"]])

            def approval_validator(token, expected_binding_sha256):
                if token != record["nonce"]:
                    raise PermissionError("matrix approval nonce differs")
                return _consume_approval(
                    runtime, token, expected_binding_sha256, receipt, lease_token
                )

            def source_validator(current_receipt, phase):
                if current_receipt != receipt:
                    raise PermissionError("matrix receipt changed during native execution")
                approval._require_runtime_probe_lease(runtime, lease_token)
                _validate_matrix_sources(runtime, current_receipt, require_current=True)
                current_models = _model_bindings(runtime, sender, receiver)
                if current_models != record.get("models"):
                    raise PermissionError("installed sender/receiver model identity changed during native execution")
                return True

            bridge_started = True
            result = score_and_record_native_receiver_condition_matrix(
                runtime,
                matrix,
                approval=record["nonce"],
                approval_validator=approval_validator,
                source_validator=source_validator,
                target_token_ids=list(target_ids),
                home=runtime.home,
                model_path=models[receiver["role"]]["canonical_path"],
                deadline=time.monotonic() + 120.0,
                target_environment="LOCAL_LINUX",
                threads=1,
                binary_path=Path(runtime.home) / "bin" / "native_latent_receiver",
                cancel_event=runtime.cancel_event,
            )
        state, version = runtime.store.state(KEY, None)
        if isinstance(state, dict) and state.get("status") == "CONSUMED":
            state = dict(state)
            state.update({"status": "COMPLETED", "completed_at": time.time()})
            runtime.store.set_state(KEY, state, expected=version)
        return result
    except BaseException as exc:
        state, version = runtime.store.state(KEY, None)
        if isinstance(state, dict) and state.get("schema") == SCHEMA and state.get("status") in {"PENDING", "CONSUMED"}:
            state = dict(state)
            state.update({
                "status": "FAILED_AFTER_CONSUMPTION" if state.get("status") == "CONSUMED" else "FAILED_REVOKED",
                "failure_kind": type(exc).__name__,
            })
            runtime.store.set_state(KEY, state, expected=version)
        raise
    finally:
        if bridge_started:
            try:
                matrix.close()
            except Exception:
                pass
            runtime._native_receiver_condition_matrix = None
            runtime._native_receiver_matrix_target_token_ids = None
            runtime._native_receiver_matrix_pair_record = None
            runtime._native_receiver_matrix_staged_at = None


def _status(runtime):
    matrix = getattr(runtime, "_native_receiver_condition_matrix", None)
    staged = None
    if matrix is not None:
        try:
            receipt = _matrix_receipt(matrix)
            staged = {
                "task_group_id": receipt["task_group_id"],
                "task_family": receipt["task_family"],
                "session_id": receipt["session_id"],
                "task_event_id": receipt["task_event_id"],
                "matrix_sha256": receipt["matrix_sha256"],
                "condition_count": receipt["condition_count"],
                "source_count": len(receipt["source_bindings"]),
                "receiver_role": receipt["receiver"]["role"],
                "status": "STAGED_NOT_APPROVED",
            }
        except Exception:
            staged = {"status": "INVALID_STAGED_MATRIX"}
    approval_record, _ = runtime.store.state(KEY, None)
    approval_status = (
        approval_record.get("status")
        if isinstance(approval_record, dict) and approval_record.get("schema") == SCHEMA
        else "NONE"
    )
    expires_at = (
        approval_record.get("expires_at")
        if isinstance(approval_record, dict) and approval_record.get("schema") == SCHEMA
                and _valid_approval_window(approval_record)
        else None
    )
    approval_liveness = _approval_liveness(runtime, approval_record)
    return {
        "schema": SCHEMA,
        "status": "READY" if staged else "NO_MATRIX_STAGED",
        "staged": staged,
        "approval_status": approval_status,
        "approval_liveness": approval_liveness,
        "approval_expires_at": expires_at,
        "android_status": "REDMI_UNVERIFIED",
        "native_execution_environment": "LOCAL_LINUX_ONLY_UNTIL_DEVICE_RECEIPT_INTEGRATION",
        "persisted_vectors": False,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }


def _clear(runtime):
    approval._require_local_tty()
    runtime.require_idle()
    record, version = runtime.store.state(KEY, None)
    if (isinstance(record, dict) and record.get("schema") == SCHEMA
            and record.get("status") == "PENDING"):
        liveness = _approval_liveness(runtime, record)
        if liveness == "PENDING":
            raise PermissionError("revoke the live pending matrix approval before clearing the staged matrix")
        _invalidate_stale_approval(runtime, record, version, liveness)
    matrix = getattr(runtime, "_native_receiver_condition_matrix", None)
    if matrix is not None:
        close = getattr(matrix, "close", None)
        if callable(close):
            close()
    runtime._native_receiver_condition_matrix = None
    runtime._native_receiver_matrix_target_token_ids = None
    runtime._native_receiver_matrix_pair_record = None
    runtime._native_receiver_matrix_staged_at = None
    return {"schema": SCHEMA, "status": "CLEARED", "matrix_was_staged": matrix is not None}


def operator_command(runtime, args):
    """Local-TTY commands for the staged native receiver matrix consumer."""
    if args == ["matrix-status"]:
        return dumps(_status(runtime))
    if args == ["matrix-arm", "--confirm"]:
        return dumps(_arm(runtime))
    if args == ["matrix-run", "--confirm"]:
        return dumps(_run(runtime))
    if args == ["matrix-revoke", "--confirm"]:
        approval._require_local_tty()
        runtime.require_idle()
        return dumps(_revoke(runtime))
    if args == ["matrix-clear", "--confirm"]:
        return dumps(_clear(runtime))
    raise ValueError(
        ":callosum matrix-status|matrix-arm --confirm|matrix-run --confirm|"
        "matrix-revoke --confirm|matrix-clear --confirm"
    )
