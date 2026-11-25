"""Native tokenwise receiver diagnostic using source-bound anchor-preserving input."""
from __future__ import annotations

import hashlib
import math
import os
import struct
import stat
import threading
import time
from pathlib import Path

SCHEMA = "v14.native-tokenwise-receiver-probe/1"
APPROVAL_KIND = "NATIVE_RECEIVER"
DEFAULT_TIMEOUT_SECONDS = 90
POSITION_MODE = "ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL"


class NativeTokenwiseReceiverProbeError(RuntimeError):
    pass


def _source_binding(value):
    if not isinstance(value, dict):
        raise NativeTokenwiseReceiverProbeError("source binding is missing")
    keys = ("source_id", "sha256", "char_start", "char_end")
    binding = {key: value.get(key) for key in keys}
    if (type(binding["source_id"]) is not str or not binding["source_id"]
            or type(binding["sha256"]) is not str or len(binding["sha256"]) != 64
            or any(ch not in "0123456789abcdef" for ch in binding["sha256"])
            or type(binding["char_start"]) is not int or binding["char_start"] < 0
            or type(binding["char_end"]) is not int or binding["char_end"] <= binding["char_start"]):
        raise NativeTokenwiseReceiverProbeError("source binding is malformed")
    return binding


def _file_identity(binding, label):
    path_value = binding.get("canonical_path")
    expected = binding.get("file_identity")
    if (type(path_value) is not str or not path_value
            or not isinstance(expected, (list, tuple)) or len(expected) != 5):
        raise NativeTokenwiseReceiverProbeError(label + " model file identity is incomplete")
    path = Path(path_value)
    if path.is_symlink():
        raise NativeTokenwiseReceiverProbeError(label + " model path is a symlink")
    try:
        info = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise NativeTokenwiseReceiverProbeError(label + " model path is unavailable") from exc
    if not stat.S_ISREG(info.st_mode):
        raise NativeTokenwiseReceiverProbeError(label + " model is not a regular file")
    actual = [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]
    if actual != list(expected):
        raise NativeTokenwiseReceiverProbeError(label + " model file identity changed")
    return path


def _validate_packet(packet, *, adapter, record):
    if not isinstance(packet, dict):
        raise NativeTokenwiseReceiverProbeError("anchor-preserving builder returned no packet")
    if (packet.get("schema") != "v14.native-tokenwise-anchor-residual-input/1"
            or packet.get("input_strategy") != "ANCHOR_PLUS_CAPPED_RESIDUAL_V1"
            or packet.get("anchor_rows_preserved_as_base") is not True
            or packet.get("production_route") is not False
            or packet.get("semantic_use_proven") is not False
            or packet.get("training_authority") != 0
            or packet.get("native_receiver_authority") != 0
            or packet.get("persisted") is not False):
        raise NativeTokenwiseReceiverProbeError("receiver input packet carries unsupported authority or status")
    adapter_sha = adapter.get("adapter_sha256") if isinstance(adapter, dict) else None
    if (type(adapter_sha) is not str or len(adapter_sha) != 64
            or any(ch not in "0123456789abcdef" for ch in adapter_sha)
            or packet.get("adapter_sha256") != adapter_sha):
        raise NativeTokenwiseReceiverProbeError("receiver packet is not bound to the supplied adapter")
    if (packet.get("record_sha256") != record.get("record_sha256")
            or packet.get("event_id") != record.get("event_id")
            or packet.get("brain_generation_id") != record.get("brain_generation_id")
            or packet.get("session_id") != record.get("session_id")
            or _source_binding(packet.get("source_ref")) != _source_binding(record.get("source_ref"))):
        raise NativeTokenwiseReceiverProbeError("receiver packet lost its pair-record provenance")
    vectors = packet.get("vectors")
    positions = packet.get("position_ids")
    rows = packet.get("input_rows")
    dimension = packet.get("input_dim")
    if (not isinstance(vectors, list) or not 1 <= len(vectors) <= 64
            or type(rows) is not int or rows != len(vectors)
            or type(dimension) is not int or not 1 <= dimension <= 8192
            or rows * dimension > 262144
            or not isinstance(positions, list) or positions != list(range(rows))
            or packet.get("position_mode") != POSITION_MODE
            or type(packet.get("input_sha256")) is not str or len(packet["input_sha256"]) != 64
            or any(ch not in "0123456789abcdef" for ch in packet["input_sha256"])
            or type(packet.get("anchor_sha256")) is not str or len(packet["anchor_sha256"]) != 64
            or any(ch not in "0123456789abcdef" for ch in packet["anchor_sha256"])):
        raise NativeTokenwiseReceiverProbeError("receiver packet geometry or digest is invalid")
    flat = []
    for row in vectors:
        if not isinstance(row, (list, tuple)) or len(row) != dimension:
            raise NativeTokenwiseReceiverProbeError("receiver packet contains ragged vectors")
        for value in row:
            if type(value) not in (int, float) or not math.isfinite(float(value)) or abs(float(value)) > 1.0e6:
                raise NativeTokenwiseReceiverProbeError("receiver packet contains a non-finite or unbounded value")
            flat.append(float(value))
    payload = struct.pack("<" + "f" * len(flat), *flat)
    if hashlib.sha256(payload).hexdigest() != packet["input_sha256"]:
        raise NativeTokenwiseReceiverProbeError("receiver packet input digest differs from its vectors")
    if type(packet.get("tokenizer_revision")) is not str or not packet["tokenizer_revision"]:
        raise NativeTokenwiseReceiverProbeError("receiver packet tokenizer binding is missing")
    return packet


def _run_interruptibly(runtime, receiver_fn, kwargs):
    outcome = {}

    def invoke():
        try:
            outcome["result"] = receiver_fn(**kwargs)
        except BaseException as exc:
            outcome["error"] = exc

    worker = threading.Thread(target=invoke, name="v14-tokenwise-native-receiver", daemon=True)
    worker.start()
    interrupted = False
    while worker.is_alive():
        try:
            worker.join(0.1)
        except KeyboardInterrupt:
            runtime.cancel_event.set()
            interrupted = True
        if runtime.stop.is_set():
            runtime.cancel_event.set()
    if interrupted:
        raise InterruptedError("tokenwise native receiver probe cancelled by local operator")
    error = outcome.get("error")
    if error is not None:
        raise error
    if runtime.cancel_event.is_set():
        raise InterruptedError("tokenwise native receiver probe cancelled by Runtime")
    result = outcome.get("result")
    if not isinstance(result, dict):
        raise NativeTokenwiseReceiverProbeError("native receiver returned no metrics")
    return result


def probe_native_tokenwise_candidate(
    runtime, adapter, record, *, timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    threads=1, residual_gain=0.10, max_relative_residual=0.25,
    approval_module=None, packet_builder=None, receiver_fn=None,
    target_token_ids=None, task_score_metadata=None, target_environment=None,
    device_execution_receipt_sha256=None, device_runtime_build_id=None,
):
    """Run one local-TTY-approved native receiver diagnostic on an in-memory pair.

    The separate NATIVE_RECEIVER approval is consumed; TOKENWISE_PAIR_CAPTURE
    approval is not interchangeable. No vectors or adapter are persisted.
    """
    injected_receiver_fn = receiver_fn is not None
    if type(timeout_seconds) is not int or not 10 <= timeout_seconds <= 120:
        raise ValueError("tokenwise native receiver timeout must be 10..120 seconds")
    if type(threads) is not int or not 1 <= threads <= 2:
        raise ValueError("tokenwise native receiver threads must be 1 or 2")
    target_ids = None
    target_ids_sha256 = None
    if target_token_ids is not None:
        if (not isinstance(target_token_ids, (list, tuple)) or not 1 <= len(target_token_ids) <= 512
                or any(type(token) is not int or token < 0 or token > 2147483647 for token in target_token_ids)):
            raise ValueError("target token IDs must be 1..512 non-negative int32 values")
        target_ids = tuple(target_token_ids)
        target_ids_sha256 = hashlib.sha256(struct.pack("<" + "i" * len(target_ids), *target_ids)).hexdigest()
        if (not isinstance(task_score_metadata, dict)
                or task_score_metadata.get("condition") != "LATENT_CANDIDATE"
                or type(task_score_metadata.get("task_group_id")) is not str
                or not task_score_metadata["task_group_id"]
                or task_score_metadata.get("task_family") not in {"ARITHMETIC", "ENTITY_RECALL", "RELATION", "MULTI_STEP", "OTHER"}
                or type(task_score_metadata.get("context_sha256")) is not str
                or len(task_score_metadata["context_sha256"]) != 64
                or any(ch not in "0123456789abcdef" for ch in task_score_metadata["context_sha256"])):
            raise ValueError("LATENT_CANDIDATE task-score metadata is incomplete or malformed")
        if task_score_metadata.get("session_id") not in (None, getattr(runtime, "session", None)):
            raise ValueError("task-score session differs from the active Runtime session")
        if injected_receiver_fn:
            if target_environment not in (None, "SYNTHETIC") or device_execution_receipt_sha256 is not None or device_runtime_build_id is not None:
                raise ValueError("injected receiver functions are synthetic fixtures only")
            target_environment = "SYNTHETIC"
        elif target_environment not in {"LOCAL_LINUX", "TERMUX_ANDROID", "REDMI"}:
            raise ValueError("native target scoring requires an explicit execution environment")
        if target_environment in {"TERMUX_ANDROID", "REDMI"}:
            if (type(device_execution_receipt_sha256) is not str or len(device_execution_receipt_sha256) != 64
                    or any(ch not in "0123456789abcdef" for ch in device_execution_receipt_sha256)
                    or type(device_runtime_build_id) is not str or not device_runtime_build_id
                    or len(device_runtime_build_id) > 128):
                raise ValueError("Android target scoring requires a device receipt and runtime build ID")
        elif device_execution_receipt_sha256 is not None or device_runtime_build_id is not None:
            raise ValueError("local Linux target scoring must not carry Android device metadata")
    elif any(value is not None for value in (task_score_metadata, target_environment, device_execution_receipt_sha256, device_runtime_build_id)):
        raise ValueError("task-score metadata requires target token IDs")
    if not isinstance(record, dict) or record.get("schema") != "v14.native-tokenwise-pairing/1":
        raise NativeTokenwiseReceiverProbeError("a native tokenwise pair record is required")
    if (record.get("status") != "PAIRED_DIAGNOSTIC" or record.get("persisted") is not False
            or record.get("production_route") is not False or record.get("semantic_use_proven") is not False
            or record.get("training_authority") != 0 or record.get("native_receiver_authority") != 0):
        raise NativeTokenwiseReceiverProbeError("pair record is not an authority-zero diagnostic")
    if approval_module is None:
        from . import native_probe_approval as approval_module
    if packet_builder is None:
        from .native_tokenwise_pairing import build_anchor_preserving_native_receiver_input as packet_builder
    if receiver_fn is None:
        from .native_latent_receiver import probe as receiver_fn

    sender_role = record.get("sender", {}).get("role") if isinstance(record.get("sender"), dict) else None
    receiver_role = record.get("receiver", {}).get("role") if isinstance(record.get("receiver"), dict) else None
    approval_module._roles(sender_role, receiver_role)
    started = time.monotonic()

    with approval_module.runtime_probe_lease(runtime) as lease_token:
        event, source_ref = approval_module._current_event(runtime)
        source_binding = _source_binding(source_ref)
        if (_source_binding(record.get("source_ref")) != source_binding
                or record.get("session_id") != runtime.session
                or record.get("event_id") != event.get("event_id")
                or record.get("brain_generation_id") != event.get("brain_generation_id")):
            raise PermissionError("tokenwise pair record is not the current source/session/event")
        source_text = runtime.store.read_source(source_ref)
        source_bytes = source_text.encode("utf-8", errors="strict") if type(source_text) is str else b""
        if (not source_bytes or hashlib.sha256(source_bytes).hexdigest() != source_binding["sha256"]
                or source_binding["char_start"] != 0 or source_binding["char_end"] != len(source_text)):
            raise PermissionError("current source bytes differ from the approved pair record")

        sender_binding = approval_module._model_binding(runtime, sender_role)
        receiver_binding = approval_module._model_binding(runtime, receiver_role)
        sender_record, receiver_record = record["sender"], record["receiver"]
        if (sender_record.get("model_revision") != sender_binding.get("revision")
                or sender_record.get("model_sha256") != sender_binding.get("sha256")
                or receiver_record.get("model_revision") != receiver_binding.get("revision")
                or receiver_record.get("model_sha256") != receiver_binding.get("sha256")):
            raise PermissionError("pair record differs from installed sender/receiver models")

        if (not isinstance(adapter, dict) or adapter.get("status") != "ALIGNMENT_CANDIDATE"
                or adapter.get("projection_scope") != "TOKENWISE"
                or adapter.get("production_route") is not False
                or adapter.get("semantic_use_proven") is not False
                or adapter.get("training_authority") != 0
                or adapter.get("native_receiver_authority") != 0):
            raise NativeTokenwiseReceiverProbeError("adapter is not an authority-zero TOKENWISE candidate")
        packet = packet_builder(
            adapter, record, residual_gain=residual_gain,
            max_relative_residual=max_relative_residual,
        )
        packet = _validate_packet(packet, adapter=adapter, record=record)
        if (packet.get("sender_role") != sender_role or packet.get("receiver_role") != receiver_role
                or packet.get("sender_model_sha256") != sender_binding.get("sha256")
                or packet.get("receiver_model_sha256") != receiver_binding.get("sha256")
                or packet.get("sender_model_revision") != sender_binding.get("revision")
                or packet.get("receiver_model_revision") != receiver_binding.get("revision")):
            raise PermissionError("anchor-preserving input differs from installed model bindings")

        approval = approval_module.consume(
            runtime, sender_role, receiver_role, event, source_ref,
            lease_token=lease_token, probe_kind=APPROVAL_KIND,
        )
        preflight = approval.get("resource_preflight") if isinstance(approval, dict) else None
        if (not isinstance(approval, dict) or not isinstance(approval.get("approval_id"), str)
                or approval.get("probe_kind") != APPROVAL_KIND or approval.get("consumed") is not True
                or not isinstance(preflight, dict) or preflight.get("status") != "PASS"):
            raise PermissionError("separate local NATIVE_RECEIVER approval or resource preflight failed")
        consumed_record, _ = runtime.store.state(approval_module.KEY, None)
        if (not isinstance(consumed_record, dict) or consumed_record.get("status") != "CONSUMED"
                or consumed_record.get("probe_kind") != APPROVAL_KIND
                or consumed_record.get("sender_role") != sender_role
                or consumed_record.get("receiver_role") != receiver_role
                or consumed_record.get("session_id") != runtime.session
                or consumed_record.get("event_id") != event.get("event_id")
                or consumed_record.get("source_ref") != source_ref):
            raise PermissionError("consumed approval is not bound to this exact native receiver probe")

        if (runtime.current != "probe" or not getattr(runtime, "_native_probe_active", False)
                or getattr(runtime, "_native_probe_lease_nonce", None) != lease_token
                or not runtime.jobs.empty() or runtime.store.queue_stats().get("count", 0) != 0):
            raise PermissionError("exclusive Runtime lease or empty queue was lost")
        if runtime.cancel_event.is_set() or runtime.stop.is_set():
            raise InterruptedError("tokenwise native receiver probe cancelled before execution")
        if (runtime.pool.pids() or runtime.needle.pids()
                or runtime.memory.semantic_keys.encoder.pids()):
            raise PermissionError("known managed model processes remain before native receiver load")

        sender_path = _file_identity(sender_binding, "sender")
        receiver_path = _file_identity(receiver_binding, "receiver")
        deadline = time.monotonic() + timeout_seconds
        if deadline <= time.monotonic():
            raise TimeoutError("tokenwise native receiver deadline expired before model load")
        receiver_kwargs = {
            "home": runtime.home,
            "model_path": receiver_path,
            "expected_model_sha256": receiver_binding["sha256"],
            "sender_role": sender_role,
            "receiver_role": receiver_role,
            "sender_tap_id": sender_record["tap_id"],
            "sender_model_revision": sender_binding["revision"],
            "sender_model_sha256": sender_binding["sha256"],
            "tokenizer_revision": packet["tokenizer_revision"],
            "receiver_model_revision": receiver_binding["revision"],
            "source_id": source_binding["source_id"],
            "generation_id": event["brain_generation_id"],
            "vectors": packet["vectors"],
            "position_ids": packet["position_ids"],
            "position_mode": packet["position_mode"],
            "deadline": deadline,
            "threads": threads,
            "cancel_event": runtime.cancel_event,
        }
        if target_ids is not None:
            receiver_kwargs.update({
                "target_token_ids": target_ids,
                "target_environment": target_environment,
                "device_execution_receipt_sha256": device_execution_receipt_sha256,
                "device_runtime_build_id": device_runtime_build_id,
            })
        native_result = _run_interruptibly(runtime, receiver_fn, receiver_kwargs)
        if (event, source_ref) != approval_module._current_event(runtime):
            raise NativeTokenwiseReceiverProbeError("source/event changed during native receiver probe")
        if runtime.store.read_source(source_ref) != source_text:
            raise NativeTokenwiseReceiverProbeError("source bytes changed during native receiver probe")
        _file_identity(sender_binding, "sender")
        _file_identity(receiver_binding, "receiver")
        from .native_latent_receiver import PINNED_LLAMA_REVISION
        native_status = native_result.get("status")
        consumed = native_result.get("native_input_consumed")
        effect_detected = native_result.get("input_effect_detected")
        effect_rms = native_result.get("input_effect_rms")
        if (native_result.get("runner_revision") != PINNED_LLAMA_REVISION
                or native_status not in {"DIMENSION_MISMATCH", "NATIVE_INPUT_EFFECT", "NATIVE_DECODE_NO_EFFECT"}
                or type(consumed) is not bool or type(effect_detected) is not bool
                or type(effect_rms) not in (int, float) or not math.isfinite(float(effect_rms))
                or (native_status == "DIMENSION_MISMATCH" and (consumed or effect_detected))
                or (native_status == "NATIVE_INPUT_EFFECT" and (not consumed or not effect_detected))
                or (native_status == "NATIVE_DECODE_NO_EFFECT" and (not consumed or effect_detected))):
            raise NativeTokenwiseReceiverProbeError("native receiver status or pinned runner evidence is invalid")
        if (native_result.get("sender_role") != sender_role
                or native_result.get("receiver_role") != receiver_role
                or native_result.get("sender_tap_id") != sender_record["tap_id"]
                or native_result.get("sender_model_revision") != sender_binding["revision"]
                or native_result.get("sender_model_sha256") != sender_binding["sha256"]
                or native_result.get("receiver_model_revision") != receiver_binding["revision"]
                or native_result.get("receiver_model_sha256") != receiver_binding["sha256"]
                or native_result.get("tokenizer_revision") != packet["tokenizer_revision"]
                or native_result.get("input_sha256") != packet["input_sha256"]
                or native_result.get("position_ids") != packet["position_ids"]
                or native_result.get("position_mode") != packet["position_mode"]
                or native_result.get("input_rows") != packet["input_rows"]
                or native_result.get("input_dim") != packet["input_dim"]
                or type(native_result.get("native_input_consumed")) is not bool):
            raise NativeTokenwiseReceiverProbeError("native receiver result lost its input/model binding")

        task_score_receipt = None
        task_score_cohort = None
        if target_ids is not None:
            native_score = native_result.get("target_score")
            if (not isinstance(native_score, dict)
                    or native_score.get("schema") != "v14.native-receiver-target-score/1"
                    or native_score.get("target_token_ids_sha256") != target_ids_sha256
                    or native_score.get("target_token_count") != len(target_ids)
                    or native_score.get("input_sha256") != packet["input_sha256"]
                    or native_score.get("receiver_model_sha256") != receiver_binding["sha256"]
                    or native_score.get("native_input_consumed") is not True
                    or native_score.get("decode_status") != 0):
                raise NativeTokenwiseReceiverProbeError("native target score is not bound to the exact input/target/model")
            from .native_receiver_task_score import build_and_record_task_score_receipt
            source_for_score = {"source_id": source_binding["source_id"], "sha256": source_binding["sha256"]}
            task_score_receipt, task_score_cohort = build_and_record_task_score_receipt(
                runtime,
                condition="LATENT_CANDIDATE",
                task_group_id=task_score_metadata["task_group_id"],
                task_family=task_score_metadata["task_family"],
                session_id=runtime.session,
                source_ref=source_for_score,
                message_source_ref=source_for_score,
                receiver={
                    "role": receiver_role,
                    "model_revision": receiver_binding["revision"],
                    "model_sha256": receiver_binding["sha256"],
                    "tokenizer_revision": packet["tokenizer_revision"],
                },
                target_token_ids_sha256=target_ids_sha256,
                target_token_count=len(target_ids),
                context_sha256=task_score_metadata["context_sha256"],
                input_sha256=packet["input_sha256"],
                native_receipt=native_score,
                adapter_sha256=adapter["adapter_sha256"],
            )

        audit = {
            "operation": "TOKENWISE_NATIVE_RECEIVER_PROBE",
            "schema": SCHEMA,
            "sender_role": sender_role,
            "receiver_role": receiver_role,
            "source_ref": source_binding,
            "event_id": event["event_id"],
            "session_id": runtime.session,
            "sender_model_revision": sender_binding["revision"],
            "sender_model_sha256": sender_binding["sha256"],
            "receiver_model_revision": receiver_binding["revision"],
            "receiver_model_sha256": receiver_binding["sha256"],
            "sender_tap_id": sender_record["tap_id"],
            "receiver_tap_id": receiver_record["tap_id"],
            "record_sha256": record["record_sha256"],
            "adapter_sha256": adapter["adapter_sha256"],
            "receiver_runner_revision": native_result.get("runner_revision"),
            "input_strategy": packet["input_strategy"],
            "input_sha256": packet["input_sha256"],
            "anchor_sha256": packet["anchor_sha256"],
            "input_rows": packet["input_rows"],
            "input_dim": packet["input_dim"],
            "residual_gain": packet["residual_gain"],
            "max_relative_residual": packet["max_relative_residual"],
            "mean_applied_relative_residual": packet["mean_applied_relative_residual"],
            "native_status": native_result.get("status"),
            "native_input_consumed": native_result.get("native_input_consumed"),
            "input_effect_detected": native_result.get("input_effect_detected"),
            "input_effect_rms": native_result.get("input_effect_rms"),
            "output_norm": native_result.get("output_norm"),
            "decode_status": native_result.get("decode_status"),
            "row_shuffle_control_applicable": native_result.get("row_shuffle_control_applicable"),
            "zero_control_cosine": native_result.get("zero_control_cosine"),
            "shuffle_control_cosine": native_result.get("shuffle_control_cosine"),
            "row_shuffle_control_cosine": native_result.get("row_shuffle_control_cosine"),
            "repeat_cosine": native_result.get("repeat_cosine"),
            "target_score_present": task_score_receipt is not None,
            "target_token_ids_sha256": target_ids_sha256,
            "target_token_count": len(target_ids) if target_ids is not None else 0,
            "task_score_receipt_sha256": task_score_receipt.get("receipt_sha256") if task_score_receipt else None,
            "task_score_collection_status": task_score_cohort.get("status") if isinstance(task_score_cohort, dict) else None,
            "duration_s": round(time.monotonic() - started, 3),
            "production_route": False,
            "semantic_use_proven": False,
            "semantic_utility_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
            "vectors_persisted": False,
            "adapter_persisted": False,
        }
        runtime.store.log("native_tokenwise_receiver_probe", event["event_id"], audit)
        return {
            "schema": SCHEMA,
            "status": "NATIVE_RECEIVER_DIAGNOSTIC",
            "native_status": native_result.get("status"),
            "event_id": event["event_id"],
            "session_id": runtime.session,
            "source_sha256": source_binding["sha256"],
            "sender_role": sender_role,
            "receiver_role": receiver_role,
            "sender_model_revision": sender_binding["revision"],
            "receiver_model_revision": receiver_binding["revision"],
            "record_sha256": record["record_sha256"],
            "adapter_sha256": adapter["adapter_sha256"],
            "receiver_runner_revision": native_result.get("runner_revision"),
            "input_rows": packet["input_rows"],
            "input_dim": packet["input_dim"],
            "input_sha256": packet["input_sha256"],
            "anchor_sha256": packet["anchor_sha256"],
            "native_input_consumed": native_result.get("native_input_consumed"),
            "input_effect_detected": native_result.get("input_effect_detected"),
            "input_effect_rms": native_result.get("input_effect_rms"),
            "output_norm": native_result.get("output_norm"),
            "decode_status": native_result.get("decode_status"),
            "row_shuffle_control_applicable": native_result.get("row_shuffle_control_applicable"),
            "zero_control_cosine": native_result.get("zero_control_cosine"),
            "shuffle_control_cosine": native_result.get("shuffle_control_cosine"),
            "row_shuffle_control_cosine": native_result.get("row_shuffle_control_cosine"),
            "repeat_cosine": native_result.get("repeat_cosine"),
            "task_score": ({
                "receipt_sha256": task_score_receipt["receipt_sha256"],
                "task_group_id": task_score_receipt["task_group_id"],
                "condition": task_score_receipt["condition"],
                "mean_target_logprob": task_score_receipt["mean_target_logprob"],
                "collection_status": task_score_cohort.get("status"),
                "receipt_count": task_score_cohort.get("receipt_count", 0),
                "persisted": False,
            } if task_score_receipt else None),
            "production_route": False,
            "semantic_use_proven": False,
            "semantic_utility_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
            "vectors_persisted": False,
            "adapter_persisted": False,
        }


def fit_and_probe_native_tokenwise_cohort(
    runtime, records, train_session_ids, holdout_session_ids, heldout_record, *,
    fit_fn=None, probe_fn=None, **probe_kwargs,
):
    """Fit an in-memory session-disjoint candidate, then probe one current holdout record.

    Pair records and the fitted adapter remain in memory. This helper deliberately
    does not persist activations/adapters or promote B3; alignment and native input
    effect are separate from held-out semantic utility.
    """
    if not isinstance(heldout_record, dict):
        raise ValueError("a held-out native pair record is required")
    if (not isinstance(records, (list, tuple)) or not records
            or not isinstance(holdout_session_ids, (list, tuple, set))
            or heldout_record.get("session_id") not in holdout_session_ids
            or not any(
                isinstance(item, dict)
                and item.get("record_sha256") == heldout_record.get("record_sha256")
                for item in records
            )):
        raise ValueError("native receiver probe record must be a member of a declared holdout session")
    if fit_fn is None:
        from .native_tokenwise_pair_capture import fit_native_tokenwise_pair_cohort as fit_fn
    if probe_fn is None:
        probe_fn = probe_native_tokenwise_candidate
    fitted = fit_fn(records, train_session_ids, holdout_session_ids)
    if not isinstance(fitted, dict) or not isinstance(fitted.get("adapter"), dict):
        raise NativeTokenwiseReceiverProbeError("tokenwise cohort fitter returned no adapter")
    adapter = fitted["adapter"]
    if (adapter.get("status") != "ALIGNMENT_CANDIDATE"
            or adapter.get("projection_scope") != "TOKENWISE"
            or adapter.get("production_route") is not False
            or adapter.get("semantic_use_proven") is not False
            or adapter.get("training_authority") != 0
            or adapter.get("native_receiver_authority") != 0):
        raise NativeTokenwiseReceiverProbeError("cohort fitter returned an ineligible adapter")
    probe = probe_fn(runtime, adapter, heldout_record, **probe_kwargs)
    manifest = fitted.get("fit_manifest", {})
    if not isinstance(manifest, dict) or manifest.get("session_disjoint") is not True:
        raise NativeTokenwiseReceiverProbeError("cohort fitter did not prove session-disjoint holdout")
    return {
        "schema": "v14.native-tokenwise-cohort-probe/1",
        "status": "ALIGNMENT_CANDIDATE_NATIVE_DIAGNOSTIC",
        "fit_manifest": {
            key: manifest.get(key)
            for key in (
                "session_disjoint", "train_session_count", "holdout_session_count",
                "train_source_count", "holdout_source_count", "train_pair_count",
                "holdout_pair_count",
            )
        },
        "adapter_sha256": adapter.get("adapter_sha256"),
        "probe": probe,
        "adapter_persisted": False,
        "pair_records_persisted": False,
        "production_route": False,
        "semantic_utility_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }
