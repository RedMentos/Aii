"""Opt-in native llama.cpp input-embedding receiver probe.

This is a diagnostic L1 ingress probe, not a production B3 channel, trained
cross-model adapter, KV-cache injection, or learning path. It deliberately
loads only the already-installed receiver model and never changes its weights.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import subprocess
import time
from pathlib import Path

SCHEMA = "v14.native-latent-receiver/1"
PINNED_LLAMA_REVISION = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
SENDER_ROLES = frozenset({"B1_DETAIL", "B2_GIST"})
RECEIVER_ROLES = frozenset({"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"})
MAX_ROWS = 64
MAX_DIM = 8192
MAX_ELEMENTS = 262144
EFFECT_EPSILON = 1.0e-7


class NativeReceiverUnavailable(RuntimeError):
    pass


class NativeReceiverError(ValueError):
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


def _finite_number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def _vector_payload(vectors):
    if not isinstance(vectors, (list, tuple)) or not 1 <= len(vectors) <= MAX_ROWS:
        raise NativeReceiverError("tap rows outside native receiver limit")
    rows = len(vectors)
    if not isinstance(vectors[0], (list, tuple)):
        raise NativeReceiverError("tap row must be a vector")
    dim = len(vectors[0])
    if not 1 <= dim <= MAX_DIM or rows * dim > MAX_ELEMENTS:
        raise NativeReceiverError("tap dimension outside native receiver limit")
    flat = []
    for row in vectors:
        if not isinstance(row, (list, tuple)) or len(row) != dim:
            raise NativeReceiverError("ragged tap vectors")
        for value in row:
            if not _finite_number(value) or abs(float(value)) > 1.0e6:
                raise NativeReceiverError("non-finite or unbounded tap value")
            flat.append(float(value))
    try:
        payload = struct.pack("<" + "f" * len(flat), *flat)
    except (OverflowError, struct.error) as exc:
        raise NativeReceiverError("tap cannot be represented as float32") from exc
    return rows, dim, payload, hashlib.sha256(payload).hexdigest()


def _json_output(raw: bytes, stage: str) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NativeReceiverError("native receiver returned invalid " + stage + " JSON") from exc
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise NativeReceiverError("native receiver schema mismatch")
    if value.get("runner_revision") != PINNED_LLAMA_REVISION:
        raise NativeReceiverError("native receiver is not built from the pinned llama.cpp revision")
    return value


def _run_cancelable(command, payload, deadline, cancel_event):
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    first = True
    while True:
        if cancel_event is not None and cancel_event.is_set():
            process.kill()
            process.communicate()
            raise InterruptedError("native receiver probe cancelled")
        remaining = float(deadline) - time.monotonic()
        if not math.isfinite(remaining) or remaining <= 0:
            process.kill()
            process.communicate()
            raise TimeoutError("native receiver model probe timed out")
        try:
            if first:
                stdout, stderr = process.communicate(payload, timeout=min(0.25, remaining))
                first = False
            else:
                stdout, stderr = process.communicate(timeout=min(0.25, remaining))
            return process.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            first = False


def probe(*, home, model_path, expected_model_sha256, sender_role, receiver_role,
          sender_tap_id, sender_model_revision, receiver_model_revision,
          source_id, generation_id, vectors, deadline, threads=1, binary_path=None, cancel_event=None):
    """Inject a source-bound tap into a separate receiver context and return metrics only.

    Production callers omit binary_path; tests may inject a temporary fake executable.
    The model path must resolve under <home>/models and the executable under <home>/bin.
    """
    if sender_role not in SENDER_ROLES or receiver_role not in RECEIVER_ROLES or sender_role == receiver_role:
        raise NativeReceiverError("unsupported or identical sender/receiver roles")
    if not all(isinstance(value, str) and value for value in (
        sender_tap_id, sender_model_revision, receiver_model_revision, source_id, generation_id
    )):
        raise NativeReceiverError("missing tap/model/source/generation binding")
    if not isinstance(expected_model_sha256, str) or len(expected_model_sha256) != 64:
        raise NativeReceiverError("receiver model hash missing")
    if any(ch not in "0123456789abcdef" for ch in expected_model_sha256.lower()):
        raise NativeReceiverError("receiver model hash malformed")
    rows, input_dim, payload, input_sha256 = _vector_payload(vectors)

    root = Path(home).resolve()
    model = Path(model_path)
    if model.is_symlink():
        raise NativeReceiverError("receiver model symlink refused")
    model = model.resolve(strict=True)
    models_root = (root / "models").resolve()
    if not model.is_relative_to(models_root) or not model.is_file():
        raise NativeReceiverError("receiver model must be an installed file under home/models")
    if _sha256_file(model) != expected_model_sha256:
        raise NativeReceiverError("receiver model hash differs from installed manifest")

    injected_binary = binary_path is not None
    binary = Path(binary_path) if injected_binary else root / "bin" / "native_latent_receiver"
    if binary.is_symlink() or not binary.is_file() or not os.access(binary, os.X_OK):
        raise NativeReceiverUnavailable("pinned native_latent_receiver executable is not installed")
    binary = binary.resolve(strict=True)
    if not injected_binary and not binary.is_relative_to((root / "bin").resolve()):
        raise NativeReceiverError("native receiver executable escaped home/bin")

    remaining = float(deadline) - time.monotonic()
    if not math.isfinite(remaining) or remaining <= 0:
        raise TimeoutError("native receiver probe deadline expired")
    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError("native receiver probe cancelled")
    try:
        version = subprocess.run(
            [str(binary), "--version"], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=min(5.0, remaining), check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("native receiver version check timed out") from exc
    if version.returncode != 0:
        raise NativeReceiverUnavailable("native receiver version check failed")
    version_data = _json_output(version.stdout, "version")

    remaining = float(deadline) - time.monotonic()
    if not math.isfinite(remaining) or remaining <= 0:
        raise TimeoutError("native receiver probe deadline expired")
    returncode, stdout, stderr = _run_cancelable(
        [str(binary), "--model", str(model), "--rows", str(rows),
         "--input-dim", str(input_dim), "--threads", str(max(1, min(int(threads), 2)))],
        payload, deadline, cancel_event,
    )
    if returncode != 0:
        raise NativeReceiverError("native receiver model probe failed")
    raw = _json_output(stdout, "probe")
    if raw.get("llama_version") != version_data.get("llama_version"):
        raise NativeReceiverError("native receiver version changed between invocations")

    receiver_input_dim = raw.get("receiver_input_dim")
    output_dim = raw.get("output_dim")
    decode_status = raw.get("decode_status")
    if type(receiver_input_dim) is not int or type(output_dim) is not int or output_dim < 1:
        raise NativeReceiverError("native receiver dimensions missing")
    if raw.get("status") == "DIMENSION_MISMATCH":
        if receiver_input_dim == input_dim or decode_status != -100:
            raise NativeReceiverError("invalid dimension-mismatch receipt")
        status = "DIMENSION_MISMATCH"
        consumed = False
        effect = False
        output_norm = 0.0
        effect_rms = 0.0
        zero_cosine = shuffle_cosine = repeat_cosine = None
    elif raw.get("status") == "DECODED":
        if receiver_input_dim != input_dim or decode_status != 0 or raw.get("finite_output") is not True:
            raise NativeReceiverError("native receiver decode receipt failed validation")
        output_norm = raw.get("output_norm")
        effect_rms = raw.get("input_effect_rms")
        if not _finite_number(output_norm) or float(output_norm) < 0:
            raise NativeReceiverError("invalid native output norm")
        if not _finite_number(effect_rms) or float(effect_rms) < 0:
            raise NativeReceiverError("invalid native input-effect measurement")
        zero_cosine = raw.get("zero_control_cosine")
        shuffle_cosine = raw.get("shuffle_control_cosine")
        repeat_cosine = raw.get("repeat_cosine")
        for value in (zero_cosine, shuffle_cosine, repeat_cosine):
            if value is not None and (not _finite_number(value) or not -1.00001 <= float(value) <= 1.00001):
                raise NativeReceiverError("invalid native negative-control cosine")
        consumed = True  # llama_decode returned 0 after receiving llama_batch.embd
        effect = float(effect_rms) > EFFECT_EPSILON
        status = "NATIVE_INPUT_EFFECT" if effect else "NATIVE_DECODE_NO_EFFECT"
    else:
        raise NativeReceiverError("unknown native receiver status")

    if _sha256_file(model) != expected_model_sha256:
        raise NativeReceiverError("receiver model changed during native probe")

    return {
        "sender_role": sender_role,
        "receiver_role": receiver_role,
        "sender_tap_id": sender_tap_id,
        "sender_model_revision": sender_model_revision,
        "receiver_model_revision": receiver_model_revision,
        "receiver_model_sha256": expected_model_sha256,
        "runner_revision": PINNED_LLAMA_REVISION,
        "llama_version": str(raw.get("llama_version", ""))[:80],
        "input_rows": rows,
        "input_dim": input_dim,
        "receiver_input_dim": receiver_input_dim,
        "output_dim": output_dim,
        "input_sha256": input_sha256,
        "decode_status": int(decode_status),
        "output_norm": float(output_norm),
        "input_effect_rms": float(effect_rms),
        "zero_control_cosine": None if zero_cosine is None else float(zero_cosine),
        "shuffle_control_cosine": None if shuffle_cosine is None else float(shuffle_cosine),
        "repeat_cosine": None if repeat_cosine is None else float(repeat_cosine),
        "native_input_consumed": consumed,
        "input_effect_detected": effect,
        "status": status,
    }
