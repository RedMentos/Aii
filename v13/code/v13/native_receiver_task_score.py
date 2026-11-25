"""Source-bound teacher-forced target scoring through a native llama.cpp receiver.

The executable consumes receiver-native input embeddings followed by target token
IDs, then returns only per-token log-probabilities and bounded provenance. It does
not persist vectors/tokens, generate text, update weights, or grant B3 authority.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import time

SCHEMA = "v14.native-receiver-target-score/1"
SCORE_METHOD = "TEACHER_FORCED_TARGET_LOGPROB_V1"
PINNED_LLAMA_REVISION = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
MAX_ROWS = 64
MAX_DIM = 8192
MAX_ELEMENTS = 262144
MAX_TARGET_TOKENS = 512
MAX_POSITION = 131072
POSITION_MODE = "ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL"


class NativeReceiverTaskScoreError(ValueError):
    pass


class NativeReceiverTaskScoreUnavailable(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(8 * 1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _vector_payload(vectors):
    if not isinstance(vectors, (list, tuple)) or not vectors or len(vectors) > MAX_ROWS:
        raise NativeReceiverTaskScoreError("receiver input rows must be a non-empty bounded sequence")
    if not isinstance(vectors[0], (list, tuple)) or not vectors[0]:
        raise NativeReceiverTaskScoreError("receiver input vectors must be non-empty rows")
    dim = len(vectors[0])
    if dim > MAX_DIM or len(vectors) * dim > MAX_ELEMENTS:
        raise NativeReceiverTaskScoreError("receiver input dimensions exceed the native bound")
    flat = []
    for row in vectors:
        if not isinstance(row, (list, tuple)) or len(row) != dim:
            raise NativeReceiverTaskScoreError("receiver input vectors are ragged")
        for value in row:
            if type(value) not in (int, float) or not math.isfinite(float(value)) or abs(float(value)) > 1.0e6:
                raise NativeReceiverTaskScoreError("receiver input contains non-finite or unbounded values")
            flat.append(float(value))
    try:
        payload = struct.pack("<" + "f" * len(flat), *flat)
    except (OverflowError, struct.error) as exc:
        raise NativeReceiverTaskScoreError("receiver input cannot be represented as float32") from exc
    return len(vectors), dim, payload, _sha256_bytes(payload)


def _target_payload(target_token_ids):
    if (not isinstance(target_token_ids, (list, tuple)) or not 1 <= len(target_token_ids) <= MAX_TARGET_TOKENS
            or any(type(token) is not int or not 0 <= token <= 0x7FFFFFFF for token in target_token_ids)):
        raise NativeReceiverTaskScoreError("target token IDs must be 1..512 non-negative int32 values")
    try:
        payload = struct.pack("<" + "i" * len(target_token_ids), *target_token_ids)
    except (OverflowError, struct.error) as exc:
        raise NativeReceiverTaskScoreError("target token IDs cannot be represented as int32") from exc
    return payload, _sha256_bytes(payload)


def _positions(position_ids, rows, position_mode):
    if position_mode != POSITION_MODE or not isinstance(position_ids, (list, tuple)) or len(position_ids) != rows:
        raise NativeReceiverTaskScoreError("unsupported receiver position mapping")
    positions = []
    for index, value in enumerate(position_ids):
        if type(value) is not int or value != index or value >= MAX_POSITION:
            raise NativeReceiverTaskScoreError("receiver positions must be contiguous zero-based prefill positions")
        positions.append(value)
    return positions


def _json_output(raw: bytes, stage: str) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NativeReceiverTaskScoreError("native task scorer returned invalid " + stage + " JSON") from exc
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise NativeReceiverTaskScoreError("native task scorer schema mismatch")
    if value.get("runner_revision") != PINNED_LLAMA_REVISION:
        raise NativeReceiverTaskScoreError("native task scorer is not built from the pinned llama.cpp revision")
    return value


def _run_cancelable(command, payload, deadline, cancel_event):
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    first = True
    while True:
        if cancel_event is not None and cancel_event.is_set():
            process.kill()
            process.communicate()
            raise InterruptedError("native receiver task-score probe cancelled")
        remaining = float(deadline) - time.monotonic()
        if not math.isfinite(remaining) or remaining <= 0:
            process.kill()
            process.communicate()
            raise TimeoutError("native receiver task-score probe timed out")
        try:
            if first:
                stdout, stderr = process.communicate(payload, timeout=min(0.2, remaining))
                first = False
            else:
                stdout, stderr = process.communicate(timeout=min(0.2, remaining))
            return process.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            first = False


def _environment_fields(environment, device_execution_receipt_sha256, device_runtime_build_id, injected_binary):
    if injected_binary:
        if environment != "SYNTHETIC":
            raise NativeReceiverTaskScoreError("injected native scorer binaries are SYNTHETIC only")
        if device_execution_receipt_sha256 is not None or device_runtime_build_id is not None:
            raise NativeReceiverTaskScoreError("synthetic execution cannot claim a device receipt")
        return "SYNTHETIC_FIXTURE", "SYNTHETIC", {}
    if environment not in {"LOCAL_LINUX", "TERMUX_ANDROID", "REDMI"}:
        raise NativeReceiverTaskScoreError("native execution environment must be explicit")
    if environment in {"TERMUX_ANDROID", "REDMI"}:
        if (type(device_execution_receipt_sha256) is not str or len(device_execution_receipt_sha256) != 64
                or any(c not in "0123456789abcdef" for c in device_execution_receipt_sha256)
                or type(device_runtime_build_id) is not str or not device_runtime_build_id or len(device_runtime_build_id) > 160):
            raise NativeReceiverTaskScoreError("Android/Redmi scoring requires a private execution-receipt digest and runtime build ID")
        return "NATIVE_LLAMA_CPP_GGUF", environment, {
            "device_execution_receipt_sha256": device_execution_receipt_sha256,
            "device_runtime_build_id": device_runtime_build_id,
        }
    if device_execution_receipt_sha256 is not None or device_runtime_build_id is not None:
        raise NativeReceiverTaskScoreError("LOCAL_LINUX scoring must not carry Android receipt metadata")
    return "NATIVE_LLAMA_CPP_GGUF", environment, {}


def probe_native_receiver_task_score(*, home, model_path, expected_model_sha256,
        receiver_role, receiver_model_revision, tokenizer_revision, vectors,
        position_ids, position_mode, target_token_ids, deadline, environment,
        condition, task_group_id, task_family, session_id, source_ref,
        message_source_ref, context_sha256, adapter_sha256=None, threads=1,
        binary_path=None, cancel_event=None, device_execution_receipt_sha256=None,
        device_runtime_build_id=None):
    """Run native teacher-forced scoring and build one authority-zero task receipt.

    Input vectors and target IDs are passed over stdin only. The returned receipt
    contains hashes/counts/log-probabilities, never raw vectors, IDs, or text.
    binary_path is a test-only injected executable and is always marked SYNTHETIC.
    """
    if receiver_role not in {"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"}:
        raise NativeReceiverTaskScoreError("unsupported receiver role")
    if not all(type(value) is str and value for value in (receiver_model_revision, tokenizer_revision)):
        raise NativeReceiverTaskScoreError("receiver model and tokenizer revisions are required")
    if type(expected_model_sha256) is not str or len(expected_model_sha256) != 64 or any(c not in "0123456789abcdef" for c in expected_model_sha256):
        raise NativeReceiverTaskScoreError("receiver model hash must be lowercase SHA-256")
    if not tokenizer_revision.startswith("llama-server:") or not tokenizer_revision.endswith(";gguf:" + expected_model_sha256):
        raise NativeReceiverTaskScoreError("receiver tokenizer revision is not bound to the exact GGUF")
    if type(threads) is not int or not 1 <= threads <= 2:
        raise NativeReceiverTaskScoreError("native receiver task scorer supports one or two threads")
    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError("native receiver task-score probe cancelled")
    from . import native_receiver_utility
    if condition not in native_receiver_utility.CONDITIONS or task_family not in native_receiver_utility.TASK_FAMILIES:
        raise NativeReceiverTaskScoreError("unsupported held-out task condition or family")
    rows, input_dim, input_bytes, input_sha256 = _vector_payload(vectors)
    positions = _positions(position_ids, rows, position_mode)
    target_bytes, target_sha256 = _target_payload(target_token_ids)
    if positions[-1] + len(target_token_ids) > MAX_POSITION:
        raise NativeReceiverTaskScoreError("target scoring exceeds the bounded receiver position range")
    execution_kind, normalized_environment, device_fields = _environment_fields(
        environment, device_execution_receipt_sha256, device_runtime_build_id, binary_path is not None)

    root = Path(home).resolve()
    model = Path(model_path)
    if model.is_symlink():
        raise NativeReceiverTaskScoreError("receiver model symlink refused")
    model = model.resolve(strict=True)
    models_root = (root / "models").resolve()
    if not model.is_relative_to(models_root) or not model.is_file():
        raise NativeReceiverTaskScoreError("receiver model must be an installed file under home/models")
    if _sha256_file(model) != expected_model_sha256:
        raise NativeReceiverTaskScoreError("receiver model hash differs from installed manifest")

    injected_binary = binary_path is not None
    binary = Path(binary_path) if injected_binary else root / "bin" / "native_receiver_task_score"
    if binary.is_symlink() or not binary.is_file() or not os.access(binary, os.X_OK):
        raise NativeReceiverTaskScoreUnavailable("pinned native_receiver_task_score executable is not installed")
    binary = binary.resolve(strict=True)
    binary_sha256_before = _sha256_file(binary)
    if not injected_binary and not binary.is_relative_to((root / "bin").resolve()):
        raise NativeReceiverTaskScoreError("native task scorer executable escaped home/bin")

    remaining = float(deadline) - time.monotonic()
    if not math.isfinite(remaining) or remaining <= 0:
        raise TimeoutError("native receiver task-score deadline expired")
    try:
        version = subprocess.run([str(binary), "--version"], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=min(5.0, remaining), check=False)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("native receiver task-score version check timed out") from exc
    if version.returncode != 0:
        raise NativeReceiverTaskScoreUnavailable("native receiver task-score version check failed")
    version_data = _json_output(version.stdout, "version")
    if not isinstance(version_data.get("llama_version"), str) or not version_data["llama_version"]:
        raise NativeReceiverTaskScoreError("native task scorer version receipt is missing llama_version")

    command = [str(binary), "--model", str(model), "--rows", str(rows),
        "--input-dim", str(input_dim), "--positions", ",".join(str(x) for x in positions),
        "--threads", str(threads), "--target-count", str(len(target_token_ids))]
    returncode, stdout, _stderr = _run_cancelable(command, input_bytes + target_bytes, deadline, cancel_event)
    if returncode != 0:
        raise NativeReceiverTaskScoreError("native receiver target-score execution failed")
    raw = _json_output(stdout, "score")
    if raw.get("llama_version") != version_data.get("llama_version"):
        raise NativeReceiverTaskScoreError("native task scorer version changed between invocations")
    if (raw.get("status") != "TARGET_SCORED" or type(raw.get("decode_status")) is not int
            or raw["decode_status"] != 0 or raw.get("native_input_consumed") is not True
            or raw.get("score_method") != SCORE_METHOD
            or type(raw.get("target_token_count")) is not int
            or raw.get("target_token_count") != len(target_token_ids)
            or raw.get("finite_scores") is not True):
        raise NativeReceiverTaskScoreError("native target-score receipt failed validation")
    scores = raw.get("token_logprobs")
    if (not isinstance(scores, list) or len(scores) != len(target_token_ids)
            or any(type(value) not in (int, float) or not math.isfinite(float(value)) or float(value) > 1.0e-7 for value in scores)):
        raise NativeReceiverTaskScoreError("native target log-probabilities are invalid")
    if raw.get("input_rows") != rows or raw.get("input_dim") != input_dim or raw.get("receiver_input_dim") != input_dim:
        raise NativeReceiverTaskScoreError("native receiver input geometry differs from the supplied rows")
    if raw.get("position_ids") != positions or raw.get("position_mode") != POSITION_MODE:
        raise NativeReceiverTaskScoreError("native receiver position mapping changed")
    if _sha256_file(model) != expected_model_sha256:
        raise NativeReceiverTaskScoreError("receiver model changed during native task scoring")
    binary_sha256_after = _sha256_file(binary)
    if binary_sha256_after != binary_sha256_before:
        raise NativeReceiverTaskScoreError("native task scorer binary changed during execution")

    native_receipt = {
        "schema": "v14.native-receiver-target-score/1",
        "execution_kind": execution_kind,
        "environment": normalized_environment,
        "llama_cpp_revision": PINNED_LLAMA_REVISION,
        "binary_sha256": binary_sha256_before,
        "receiver_model_sha256": expected_model_sha256,
        "input_sha256": input_sha256,
        "target_token_ids_sha256": target_sha256,
        "target_token_count": len(target_token_ids),
        "score_method": SCORE_METHOD,
        "token_logprobs": [float(value) for value in scores],
        "decode_status": 0,
        "native_input_consumed": True,
        "llama_version": version_data["llama_version"][:120],
    }
    native_receipt.update(device_fields)
    task_receipt = native_receiver_utility.build_native_receiver_task_score_receipt(
        condition=condition, task_group_id=task_group_id, task_family=task_family,
        session_id=session_id, source_ref=source_ref, message_source_ref=message_source_ref,
        receiver={"role": receiver_role, "model_revision": receiver_model_revision,
            "model_sha256": expected_model_sha256, "tokenizer_revision": tokenizer_revision},
        target_token_ids_sha256=target_sha256, target_token_count=len(target_token_ids),
        context_sha256=context_sha256, input_sha256=input_sha256,
        native_receipt=native_receipt, adapter_sha256=adapter_sha256)
    return {"native_receipt": native_receipt, "task_score_receipt": task_receipt,
        "input_rows": rows, "input_dim": input_dim, "input_sha256": input_sha256,
        "target_token_count": len(target_token_ids), "target_token_ids_sha256": target_sha256,
        "persisted": False, "training_authority": 0, "native_receiver_authority": 0}
