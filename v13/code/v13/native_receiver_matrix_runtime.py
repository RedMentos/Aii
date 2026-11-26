"""Core-owned Runtime consumer for the Perception eight-condition native receiver matrix.

The matrix is staged in memory only. A separate local-TTY one-shot approval binds
its exact digest, source/event/generation set and installed sender/receiver bytes.
The native run is serial, diagnostic-only and LOCAL_LINUX until a verified Android
device-receipt path is integrated.
"""
from __future__ import annotations

import hashlib
import json
import secrets
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
    pending, _ = runtime.store.state(KEY, None)
    if isinstance(pending, dict) and pending.get("status") == "PENDING":
        raise PermissionError("revoke the pending native receiver matrix approval before staging another")
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
    if isinstance(current, dict) and current.get("status") == "PENDING":
        expires = current.get("expires_at")
        if (current.get("runtime_nonce") == approval._runtime_nonce(runtime)
                and type(expires) in (int, float) and time.time() < expires):
            raise PermissionError("a native receiver matrix approval is already pending; revoke it first")
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
    if (record.get("status") != "PENDING"
            or record.get("nonce") != nonce
            or record.get("runtime_nonce") != approval._runtime_nonce(runtime)
            or type(record.get("expires_at")) not in (int, float)
            or now >= record["expires_at"]
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
    if (record.get("status") != "PENDING"
            or record.get("runtime_nonce") != approval._runtime_nonce(runtime)
            or type(record.get("expires_at")) not in (int, float)
            or now >= record["expires_at"]
            or record.get("matrix_sha256") != receipt["matrix_sha256"]
            or record.get("approval_binding_sha256") != receipt["approval_binding_sha256"]
            or record.get("session_id") != receipt["session_id"]
            or record.get("task_event_id") != receipt["task_event_id"]
            or record.get("task_generation_id") != receipt["task_generation_id"]):
        raise PermissionError("fresh matching :callosum matrix-arm --confirm approval is required")
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
        runtime._native_receiver_matrix_target_kind = None
        runtime._native_receiver_matrix_target_event_id = None
        runtime._native_receiver_matrix_task_family_source = None
        runtime._native_receiver_matrix_family_labels = None
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
            runtime._native_receiver_matrix_target_kind = None
            runtime._native_receiver_matrix_target_event_id = None
            runtime._native_receiver_matrix_task_family_source = None
            runtime._native_receiver_matrix_family_labels = None



def _json_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _f32_sha(rows):
    flat = [float(value) for row in rows for value in row]
    return hashlib.sha256(struct.pack("<" + "f" * len(flat), *flat)).hexdigest()


def _matrix_token_ids(response, label, minimum, maximum):
    if not isinstance(response, dict) or not isinstance(response.get("tokens"), list):
        raise NativeReceiverMatrixRuntimeError(label + " tokenizer response is malformed")
    items = response["tokens"]
    if not minimum <= len(items) <= maximum:
        raise NativeReceiverMatrixRuntimeError(label + " token count is outside the diagnostic bound")
    result = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"id", "piece"}:
            raise NativeReceiverMatrixRuntimeError(label + " token item is not canonical")
        token_id, piece = item["id"], item["piece"]
        if type(token_id) is not int or not 0 <= token_id <= 2147483647:
            raise NativeReceiverMatrixRuntimeError(label + " contains an invalid token ID")
        if not (type(piece) is str or (isinstance(piece, list) and piece
                and all(type(value) is int and 0 <= value <= 255 for value in piece))):
            raise NativeReceiverMatrixRuntimeError(label + " contains an invalid token piece")
        result.append(token_id)
    return result


def _matrix_record_by_prefix(records, prefix, label):
    if (type(prefix) is not str or not 8 <= len(prefix) <= 64
            or any(ch not in "0123456789abcdef" for ch in prefix)):
        raise ValueError(label + " record prefix must be 8..64 lowercase hexadecimal characters")
    matches = [item for item in records if isinstance(item, Mapping)
               and type(item.get("record_sha256")) is str
               and item["record_sha256"].startswith(prefix)]
    if len(matches) != 1:
        raise ValueError(label + " prefix must identify exactly one in-memory pair record")
    return dict(matches[0])


def _matrix_entity_byte_span(original_text, alternate_text):
    if type(original_text) is not str or type(alternate_text) is not str:
        raise ValueError("entity-control source text is unavailable")
    original = original_text.encode("utf-8", errors="strict")
    alternate = alternate_text.encode("utf-8", errors="strict")
    if len(original) != len(alternate):
        raise ValueError("entity control must preserve exact UTF-8 byte length")
    left = 0
    while left < len(original) and original[left] == alternate[left]:
        left += 1
    right = len(original)
    while right > left and original[right - 1] == alternate[right - 1]:
        right -= 1
    if left == right:
        raise ValueError("entity control has no source-byte change")
    return [[left, right]]


def _capture_matrix_bos_and_target(runtime, sender_role, receiver_role, pair_record, source_text, target_text):
    """Use a separate INPUT_EMBEDDING_TAP approval for the BOS row and target IDs."""
    from . import native_input_embedding_capture as input_capture
    from .native_input_embedding_extractor import extract_native_input_embedding_rows

    event, source_ref = approval._current_event(runtime)
    if (event.get("event_id") != pair_record.get("event_id")
            or event.get("brain_generation_id") != pair_record.get("brain_generation_id")
            or _source_key(source_ref, "current task") != _source_key(pair_record.get("source_ref"), "main pair")
            or runtime.store.read_source(source_ref) != source_text):
        raise PermissionError("matrix task no longer matches the current authoritative Runtime source")

    with approval.runtime_probe_lease(runtime) as lease_token:
        approval.consume(
            runtime, sender_role, receiver_role, event, source_ref,
            lease_token=lease_token, probe_kind="INPUT_EMBEDDING_TAP",
        )
        model_binding = approval._model_binding(runtime, receiver_role)
        receiver = pair_record["receiver"]
        if (model_binding.get("revision") != receiver.get("model_revision")
                or model_binding.get("sha256") != receiver.get("model_sha256")):
            raise PermissionError("installed receiver model differs from the captured pair record")
        approval._resource_preflight(runtime, model_binding)
        deadline = time.monotonic() + 120.0
        runner = runtime.pool.get_tap(receiver_role)
        try:
            runner.load(runtime.cancel_event, deadline)
            special = runner._json(
                "POST", "/tokenize",
                {"content": source_text, "add_special": True, "parse_special": False, "with_pieces": True},
                deadline, timeout_cap=None,
            )
            target = runner._json(
                "POST", "/tokenize",
                {"content": target_text, "add_special": False, "parse_special": False, "with_pieces": True},
                deadline, timeout_cap=None,
            )
        finally:
            input_capture._unload_pool(runtime)

        special_ids = _matrix_token_ids(special, "BOS/source", 3, 66)
        receiver_ids = receiver.get("token_ids")
        if (not isinstance(receiver_ids, list)
                or special_ids[1:1 + len(receiver_ids)] != receiver_ids):
            raise NativeReceiverMatrixRuntimeError(
                "receiver tokenizer BOS+content sequence differs from the captured pair record"
            )
        target_ids = _matrix_token_ids(target, "generated answer target", 1, MAX_TARGET_TOKENS)

        def prepare_idle():
            if runtime.cancel_event.is_set():
                raise InterruptedError("matrix BOS extraction was cancelled")
            if (getattr(runtime, "current", None) != "probe"
                    or not getattr(runtime, "_native_probe_active", False)
                    or getattr(runtime, "_native_probe_lease_nonce", None) != lease_token):
                raise PermissionError("matrix BOS extraction lost its exclusive Runtime lease")
            if runtime.stop.is_set() or not runtime.jobs.empty():
                raise PermissionError("matrix BOS extraction Runtime is stopping or has queued work")
            if runtime.store.queue_stats().get("count", 0) != 0:
                raise PermissionError("matrix BOS extraction Runtime queue is not empty")
            if input_capture._managed_pids(runtime):
                raise PermissionError("managed native model processes remain before BOS extraction")
            approval._resource_preflight(runtime, model_binding)

        remaining = int(deadline - time.monotonic())
        if remaining < 1:
            raise TimeoutError("matrix BOS extraction deadline expired")
        extracted = extract_native_input_embedding_rows(
            Path(runtime.home) / "bin" / "native_input_embedding_extractor",
            Path(model_binding["canonical_path"]), model_binding["revision"],
            [special_ids[0], special_ids[1]],
            model_root=Path(runtime.home) / "models",
            expected_model_sha256=model_binding["sha256"],
            prepare_idle=prepare_idle, timeout_seconds=min(120, remaining),
        )
        if (not isinstance(extracted, dict) or extracted.get("status") != "COMPLETE"
                or not isinstance(extracted.get("rows"), list) or len(extracted["rows"]) != 2
                or not isinstance(extracted.get("receipt"), dict)):
            raise NativeReceiverMatrixRuntimeError("native BOS extractor returned no complete two-row result")
        bos_rows = [extracted["rows"][0]]
        if (len(bos_rows[0]) != receiver.get("embedding_dim") or not bos_rows[0]
                or any(type(value) not in (int, float) for value in bos_rows[0])):
            raise NativeReceiverMatrixRuntimeError("native BOS row geometry differs from the receiver manifest")
        event_after, source_after = approval._current_event(runtime)
        if (event_after != event or source_after != source_ref
                or runtime.store.read_source(source_ref) != source_text
                or approval._model_binding(runtime, receiver_role) != model_binding):
            raise PermissionError("task source or installed receiver model changed during BOS extraction")
        baseline = {
            "token_kind": "BOS", "token_id": special_ids[0], "rows": bos_rows,
            "receiver_model_sha256": receiver["model_sha256"],
            "receiver_tap_id": receiver["tap_id"],
            "tokenizer_revision": receiver["tokenizer_revision"],
            "extractor_receipt_sha256": _json_sha(extracted["receipt"]),
            "input_sha256": _f32_sha(bos_rows), "input_rows": 1,
            "input_dim": len(bos_rows[0]), "source_ref": dict(source_ref),
            "event_id": event["event_id"], "brain_generation_id": event["brain_generation_id"],
        }
        del extracted
        return baseline, target_ids


def _build_matrix_from_runtime(runtime, args):
    usage = (
        "usage: :callosum matrix-build <task-family> <ood-family> <entity-family> "
        "<ood-record-sha-prefix> <entity-record-sha-prefix> --confirm; "
        "first arm INPUT_EMBEDDING_TAP for the same B1/B2 sender and receiver"
    )
    if len(args) != 7 or args[0] != "matrix-build" or args[6] != "--confirm":
        raise ValueError(usage)
    approval._require_local_tty()
    runtime.require_idle()
    if getattr(runtime, "_native_receiver_condition_matrix", None) is not None:
        raise PermissionError("clear the already-staged matrix before building another")
    task_family, ood_family, entity_family = args[1:4]
    if (task_family not in TASK_FAMILIES or ood_family not in TASK_FAMILIES
            or entity_family not in TASK_FAMILIES or entity_family != task_family
            or ood_family == task_family):
        raise ValueError("task/entity families must match and OOD family must differ")

    candidate = getattr(runtime, "_native_tokenwise_candidate", None)
    if not isinstance(candidate, dict):
        raise ValueError("no source-disjoint tokenwise alignment candidate is staged")
    adapter, main_raw = candidate.get("adapter"), candidate.get("record")
    manifest, cohort = candidate.get("fit_manifest"), candidate.get("cohort_records")
    if (not isinstance(adapter, dict) or adapter.get("projection_scope") != "TOKENWISE"
            or adapter.get("status") != "ALIGNMENT_CANDIDATE"
            or adapter.get("production_route") is not False
            or adapter.get("semantic_use_proven") is not False
            or adapter.get("training_authority") != 0 or adapter.get("native_receiver_authority") != 0
            or not isinstance(manifest, dict) or manifest.get("session_disjoint") is not True
            or manifest.get("source_disjoint") is not True
            or not isinstance(cohort, list) or not 3 <= len(cohort) <= 8):
        raise ValueError("candidate lacks its bounded source/session-disjoint control cohort")
    holdout_sessions, record_hashes = manifest.get("holdout_session_ids"), manifest.get("record_sha256s")
    if (not isinstance(holdout_sessions, list) or runtime.session not in holdout_sessions
            or not isinstance(record_hashes, list)):
        raise ValueError("current Runtime session is not part of the candidate's held-out cohort")

    from . import native_tokenwise_pairing
    def checked_record(value, label):
        try:
            checked = native_tokenwise_pairing._validate_native_pair_record(value)
        except Exception as exc:
            raise ValueError(label + " pair record failed native source/manifest validation") from exc
        if (checked.get("status") != "PAIRED_DIAGNOSTIC" or checked.get("persisted") is not False
                or checked.get("production_route") is not False or checked.get("semantic_use_proven") is not False
                or checked.get("training_authority") != 0 or checked.get("native_receiver_authority") != 0):
            raise ValueError(label + " pair record carries unsupported authority")
        if (checked.get("session_id") != runtime.session
                or checked.get("record_sha256") not in record_hashes
                or checked.get("session_id") not in holdout_sessions):
            raise ValueError(label + " record is not in the current held-out session/cohort")
        return dict(checked)

    main = checked_record(main_raw, "main")
    ood_record = checked_record(_matrix_record_by_prefix(cohort, args[4], "OOD"), "OOD")
    entity_record = checked_record(_matrix_record_by_prefix(cohort, args[5], "entity"), "entity")
    if (len({main["record_sha256"], ood_record["record_sha256"], entity_record["record_sha256"]}) != 3
            or len({main["source_ref"]["source_id"], ood_record["source_ref"]["source_id"],
                    entity_record["source_ref"]["source_id"]}) != 3
            or len({main["source_ref"]["sha256"], ood_record["source_ref"]["sha256"],
                    entity_record["source_ref"]["sha256"]}) != 3):
        raise ValueError("main, OOD and entity controls must use three distinct source records")
    if (main.get("sender") != ood_record.get("sender") or main.get("sender") != entity_record.get("sender")
            or main.get("receiver") != ood_record.get("receiver")
            or main.get("receiver") != entity_record.get("receiver")):
        raise ValueError("control pair records use different sender/receiver model bindings")

    event, source_ref = approval._current_event(runtime)
    if (main.get("event_id") != event.get("event_id")
            or main.get("brain_generation_id") != event.get("brain_generation_id")
            or _source_key(main.get("source_ref"), "main pair") != _source_key(source_ref, "current task")):
        raise PermissionError("held-out main pair is not the current completed Runtime task")
    source_text = runtime.store.read_source(source_ref)
    answer = runtime.last_answer()
    if (not answer or answer.get("status") != "FINAL" or answer.get("event_id") != event.get("event_id")
            or type(answer.get("text")) is not str or not answer["text"].strip()):
        raise ValueError("matrix target requires the current task's FINAL assistant output")
    entity_text = runtime.store.read_source(entity_record["source_ref"])
    runtime.store.read_source(ood_record["source_ref"])
    entity_spans = _matrix_entity_byte_span(source_text, entity_text)

    baseline, target_ids = _capture_matrix_bos_and_target(
        runtime, main["sender"]["role"], main["receiver"]["role"], main, source_text, answer["text"],
    )
    candidate_packet = native_tokenwise_pairing.build_anchor_preserving_native_receiver_input(adapter, main)
    ood_packet = native_tokenwise_pairing.build_anchor_preserving_native_receiver_input(adapter, ood_record)
    entity_packet = native_tokenwise_pairing.build_anchor_preserving_native_receiver_input(adapter, entity_record)
    task = {
        "task_group_id": main["event_id"], "task_family": task_family,
        "session_id": runtime.session, "source_text": source_text, "target_token_ids": target_ids,
    }
    ood_control = {
        "task_group_id": ood_record["event_id"], "task_family": ood_family,
        "session_id": runtime.session, "record": ood_record, "candidate_packet": ood_packet,
    }
    entity_control = {
        "task_group_id": entity_record["event_id"], "task_family": entity_family,
        "session_id": runtime.session, "record": entity_record,
        "candidate_packet": entity_packet, "source_text": entity_text,
        "entity_byte_spans": entity_spans,
    }
    staged = build_and_stage_native_receiver_matrix(
        runtime, task=task, pair_record=main, baseline_packet=baseline,
        candidate_packet=candidate_packet, ood_control=ood_control, entity_control=entity_control,
    )
    runtime._native_receiver_matrix_target_kind = "SELF_GENERATED_FINAL_OUTPUT"
    runtime._native_receiver_matrix_target_event_id = event["event_id"]
    runtime._native_receiver_matrix_task_family_source = "LOCAL_OPERATOR_ASSERTION"
    runtime._native_receiver_matrix_family_labels = {
        "task": task_family, "ood": ood_family, "entity": entity_family,
    }
    return dumps({
        **staged, "target_kind": runtime._native_receiver_matrix_target_kind,
        "target_source": "CURRENT_FINAL_ASSISTANT_OUTPUT",
        "generated_answer_correctness_proven": False,
        "task_family_source": runtime._native_receiver_matrix_task_family_source,
        "task_family_labels": dict(runtime._native_receiver_matrix_family_labels),
        "entity_span_source": "DERIVED_COMMON_PREFIX_SUFFIX_UTF8_BYTES",
        "baseline_source": "PINNED_NATIVE_RECEIVER_BOS_INPUT_EMBEDDING",
        "vectors_persisted": False, "production_route": False, "semantic_use_proven": False,
        "training_authority": 0, "native_receiver_authority": 0,
    })


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
        else None
    )
    return {
        "schema": SCHEMA,
        "status": "READY" if staged else "NO_MATRIX_STAGED",
        "staged": staged,
        "approval_status": approval_status,
        "approval_expires_at": expires_at,
        "android_status": "REDMI_UNVERIFIED",
        "native_execution_environment": "LOCAL_LINUX_ONLY_UNTIL_DEVICE_RECEIPT_INTEGRATION",
        "persisted_vectors": False,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "target_kind": getattr(runtime, "_native_receiver_matrix_target_kind", None),
        "target_event_id": getattr(runtime, "_native_receiver_matrix_target_event_id", None),
        "task_family_source": getattr(runtime, "_native_receiver_matrix_task_family_source", None),
        "task_family_labels": getattr(runtime, "_native_receiver_matrix_family_labels", None),
        "generated_answer_correctness_proven": False if getattr(runtime, "_native_receiver_matrix_target_kind", None) else None,
    }


def _clear(runtime):
    approval._require_local_tty()
    runtime.require_idle()
    record, _ = runtime.store.state(KEY, None)
    if isinstance(record, dict) and record.get("status") == "PENDING":
        raise PermissionError("revoke the pending matrix approval before clearing the staged matrix")
    matrix = getattr(runtime, "_native_receiver_condition_matrix", None)
    if matrix is not None:
        close = getattr(matrix, "close", None)
        if callable(close):
            close()
    runtime._native_receiver_condition_matrix = None
    runtime._native_receiver_matrix_target_token_ids = None
    runtime._native_receiver_matrix_pair_record = None
    runtime._native_receiver_matrix_staged_at = None
    runtime._native_receiver_matrix_target_kind = None
    runtime._native_receiver_matrix_target_event_id = None
    runtime._native_receiver_matrix_task_family_source = None
    runtime._native_receiver_matrix_family_labels = None
    return {"schema": SCHEMA, "status": "CLEARED", "matrix_was_staged": matrix is not None}


def operator_command(runtime, args):
    """Local-TTY commands for the staged native receiver matrix consumer."""
    if args and args[0] == "matrix-build":
        return _build_matrix_from_runtime(runtime, args)
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
        ":callosum matrix-build <task-family> <ood-family> <entity-family> <ood-record-sha-prefix> <entity-record-sha-prefix> --confirm|"
        "matrix-status|matrix-arm --confirm|matrix-run --confirm|matrix-revoke --confirm|matrix-clear --confirm"
    )
