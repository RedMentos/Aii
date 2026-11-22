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

SCHEMA = "v14.native-latent-receiver/2"
POSITION_MODE = "ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL"
MAX_POSITION = 131072
PINNED_LLAMA_REVISION = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
SENDER_ROLES = frozenset({"B1_DETAIL", "B2_GIST"})
RECEIVER_ROLES = frozenset({"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"})
MAX_ROWS = 64
MAX_DIM = 8192
MAX_ELEMENTS = 262144
TOKEN_ROW_SCHEMA = "v14.native-token-rows/1"
MAX_TOKEN_ROWS = 32
MAX_TOKEN_ROW_ELEMENTS = 262144
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


def _validate_positions(position_ids, rows, position_mode):
    if position_mode != POSITION_MODE:
        raise NativeReceiverError("unsupported sender position mode")
    if not isinstance(position_ids, (list, tuple)) or len(position_ids) != rows:
        raise NativeReceiverError("position row count differs from tap rows")
    positions = []
    previous = -1
    for value in position_ids:
        if type(value) is not int or value < 0 or value >= MAX_POSITION or value <= previous:
            raise NativeReceiverError("position IDs must be bounded, unique and strictly increasing")
        positions.append(value)
        previous = value
    if positions != list(range(rows)):
        raise NativeReceiverError("position IDs are not the verified zero-based tokenizer-prefill sequence")
    return positions


def register_packet_contract():
    """Register the optional native receiver packet only when this organ is loaded."""
    from . import contracts
    schema = {
        "sender_role": str, "receiver_role": str, "source_ref": dict,
        "sender_tap_packet_id": str, "sender_tap_id": str,
        "sender_model_revision": str, "sender_model_sha256": str,
        "tokenizer_revision": (str, type(None)),
        "receiver_model_revision": str, "receiver_model_sha256": str,
        "runner_revision": str, "llama_version": str,
        "input_rows": int, "input_dim": int, "receiver_input_dim": int,
        "output_dim": int, "input_sha256": str,
        "position_ids": list, "position_mode": str,
        "decode_status": int, "output_norm": (int, float),
        "input_effect_rms": (int, float),
        "zero_control_cosine": (int, float, type(None)),
        "shuffle_control_cosine": (int, float, type(None)),
        "row_shuffle_control_cosine": (int, float, type(None)),
        "row_shuffle_control_applicable": bool,
        "repeat_cosine": (int, float, type(None)),
        "native_input_consumed": bool, "input_effect_detected": bool,
        "production_route": bool, "semantic_use_proven": bool,
        "training_authority": int, "native_receiver_authority": int,
        "status": str,
    }
    existing = contracts.FIELDS.get("LatentReceiverPacket")
    if existing is not None and existing != schema:
        raise RuntimeError("LatentReceiverPacket contract registration conflict")
    contracts.FIELDS["LatentReceiverPacket"] = schema


def validate_packet(value):
    """Validate the optional packet's typed fields and zero-authority invariants."""
    register_packet_contract()
    from .contracts import validate
    validate("LatentReceiverPacket", value)
    if value["sender_role"] not in SENDER_ROLES or value["receiver_role"] not in RECEIVER_ROLES or value["sender_role"] == value["receiver_role"]:
        raise NativeReceiverError("LatentReceiverPacket role binding")
    if value["runner_revision"] != PINNED_LLAMA_REVISION:
        raise NativeReceiverError("LatentReceiverPacket runner revision is not pinned")
    source_ref = value["source_ref"]
    if not isinstance(source_ref.get("source_id"), str) or source_ref not in value.get("provenance", []):
        raise NativeReceiverError("LatentReceiverPacket source provenance")
    for name in ("sender_model_sha256", "receiver_model_sha256", "input_sha256"):
        digest = value[name]
        if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest.lower()):
            raise NativeReceiverError("LatentReceiverPacket " + name)
    if type(value["input_rows"]) is not int or type(value["input_dim"]) is not int:
        raise NativeReceiverError("LatentReceiverPacket input geometry type")
    if not 1 <= value["input_rows"] <= MAX_ROWS or not 1 <= value["input_dim"] <= MAX_DIM or value["input_rows"] * value["input_dim"] > MAX_ELEMENTS:
        raise NativeReceiverError("LatentReceiverPacket input geometry")
    _validate_positions(value["position_ids"], value["input_rows"], value["position_mode"])
    if type(value["receiver_input_dim"]) is not int or type(value["output_dim"]) is not int or not 1 <= value["receiver_input_dim"] <= MAX_DIM or not 1 <= value["output_dim"] <= MAX_DIM:
        raise NativeReceiverError("LatentReceiverPacket receiver geometry")
    for name in ("output_norm", "input_effect_rms"):
        if not _finite_number(value[name]) or float(value[name]) < 0:
            raise NativeReceiverError("LatentReceiverPacket metric " + name)
    for name in ("zero_control_cosine", "shuffle_control_cosine", "row_shuffle_control_cosine", "repeat_cosine"):
        metric = value[name]
        if metric is not None and (not _finite_number(metric) or not -1.00001 <= float(metric) <= 1.00001):
            raise NativeReceiverError("LatentReceiverPacket metric " + name)
    if value["production_route"] is not False or value["semantic_use_proven"] is not False or value["training_authority"] != 0 or value["native_receiver_authority"] != 0:
        raise NativeReceiverError("LatentReceiverPacket probe cannot grant production or learning authority")
    if value["status"] == "DIMENSION_MISMATCH":
        if value["receiver_input_dim"] == value["input_dim"] or value["decode_status"] != -100 or value["native_input_consumed"] or value["input_effect_detected"] or value["row_shuffle_control_applicable"] or value["row_shuffle_control_cosine"] is not None:
            raise NativeReceiverError("LatentReceiverPacket dimension mismatch receipt")
    elif value["status"] in {"NATIVE_INPUT_EFFECT", "NATIVE_DECODE_NO_EFFECT"}:
        if value["receiver_input_dim"] != value["input_dim"] or value["decode_status"] != 0 or not value["native_input_consumed"]:
            raise NativeReceiverError("LatentReceiverPacket native decode receipt")
        if value["input_effect_detected"] != (value["status"] == "NATIVE_INPUT_EFFECT"):
            raise NativeReceiverError("LatentReceiverPacket input-effect status")
        if value["input_effect_detected"] and value["input_effect_rms"] <= EFFECT_EPSILON:
            raise NativeReceiverError("LatentReceiverPacket input effect is below threshold")
        if not value["input_effect_detected"] and value["input_effect_rms"] > EFFECT_EPSILON:
            raise NativeReceiverError("LatentReceiverPacket no-effect threshold")
        if value["input_rows"] >= 2:
            if not value["row_shuffle_control_applicable"]:
                raise NativeReceiverError("LatentReceiverPacket row-order control was not executed")
        elif value["row_shuffle_control_applicable"] or value["row_shuffle_control_cosine"] is not None:
            raise NativeReceiverError("LatentReceiverPacket row-order control must be marked not applicable")
    else:
        raise NativeReceiverError("LatentReceiverPacket status")
    if value["tokenizer_revision"] is not None and (not isinstance(value["tokenizer_revision"], str) or not value["tokenizer_revision"]):
        raise NativeReceiverError("LatentReceiverPacket tokenizer revision")
    return value


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


def _json_output(raw: bytes, stage: str, *, schema: str = SCHEMA) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NativeReceiverError("native receiver returned invalid " + stage + " JSON") from exc
    if not isinstance(value, dict) or value.get("schema") != schema:
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



def extract_token_rows(*, home, model_path, expected_model_sha256, model_revision,
                       tokenizer_revision, token_ids, deadline, binary_path=None,
                       cancel_event=None):
    """Read a bounded set of receiver input-embedding rows from an installed model.

    This is a local, read-only diagnostic. It is not a production B3 route,
    semantic-use proof, trained adapter, or learning permission. The native
    executable uses a pinned internal llama.cpp header and copies only the
    requested rows; this wrapper binds the result to exact model bytes and
    tokenizer/model revisions.
    """
    if not isinstance(model_revision, str) or not model_revision:
        raise NativeReceiverError("receiver model revision is missing")
    if not isinstance(tokenizer_revision, str) or not tokenizer_revision:
        raise NativeReceiverError("receiver tokenizer revision is missing")
    if not isinstance(expected_model_sha256, str) or len(expected_model_sha256) != 64:
        raise NativeReceiverError("receiver model hash missing")
    if any(ch not in "0123456789abcdef" for ch in expected_model_sha256.lower()):
        raise NativeReceiverError("receiver model hash malformed")
    if not isinstance(token_ids, (list, tuple)) or not 1 <= len(token_ids) <= MAX_TOKEN_ROWS:
        raise NativeReceiverError("token row request must contain 1..32 token IDs")
    ids = []
    for token_id in token_ids:
        if type(token_id) is not int or token_id < 0 or token_id > 2147483647:
            raise NativeReceiverError("token IDs must be bounded nonnegative integers")
        if token_id in ids:
            raise NativeReceiverError("duplicate token IDs are not allowed")
        ids.append(token_id)
    if not _finite_number(deadline) or float(deadline) <= time.monotonic():
        raise TimeoutError("native token row deadline expired")
    expected_model_sha256 = expected_model_sha256.lower()

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
        raise TimeoutError("native token row deadline expired")
    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError("native token row extraction cancelled")
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
        raise TimeoutError("native token row deadline expired")
    returncode, stdout, stderr = _run_cancelable(
        [str(binary), "--token-rows", "--model", str(model),
         "--token-ids", ",".join(str(value) for value in ids)],
        b"", deadline, cancel_event,
    )
    if returncode != 0:
        raise NativeReceiverError("native receiver token row read failed")
    raw = _json_output(stdout, "token rows", schema=TOKEN_ROW_SCHEMA)
    if raw.get("llama_version") != version_data.get("llama_version"):
        raise NativeReceiverError("native receiver version changed between invocations")
    if raw.get("status") != "ROWS_READ" or raw.get("source") != "RECEIVER_INPUT_TOKEN_EMBEDDING_TABLE":
        raise NativeReceiverError("native receiver did not return input token embedding rows")
    if raw.get("full_table_copied") is not False or raw.get("read_only") is not True:
        raise NativeReceiverError("native receiver did not attest to bounded read-only extraction")
    if raw.get("max_rows") != MAX_TOKEN_ROWS or raw.get("requested_token_ids") != ids:
        raise NativeReceiverError("native receiver token row request differs from caller")

    vocab = raw.get("model_vocab")
    dim = raw.get("embedding_dim")
    row_bytes = raw.get("row_bytes")
    stride = raw.get("tensor_row_stride_bytes")
    tensor_type = raw.get("tensor_type")
    if (type(vocab) is not int or vocab < 1 or type(dim) is not int or
            not 1 <= dim <= MAX_DIM or dim * len(ids) > MAX_TOKEN_ROW_ELEMENTS or
            type(row_bytes) is not int or row_bytes < 1 or
            type(stride) is not int or stride < row_bytes or
            not isinstance(tensor_type, str) or not tensor_type):
        raise NativeReceiverError("native receiver token row dimensions or layout are invalid")
    if any(value >= vocab for value in ids):
        raise NativeReceiverError("requested token ID is outside the receiver vocabulary")

    rows = raw.get("rows")
    if not isinstance(rows, list) or len(rows) != len(ids):
        raise NativeReceiverError("native receiver token row count differs from request")
    checked_rows = []
    for expected_id, row in zip(ids, rows):
        if not isinstance(row, dict) or row.get("token_id") != expected_id:
            raise NativeReceiverError("native receiver token row identity differs from request")
        values = row.get("values")
        if (not isinstance(values, list) or len(values) != dim or
                any(not _finite_number(value) for value in values)):
            raise NativeReceiverError("native receiver token row contains invalid values")
        checked_rows.append({"token_id": expected_id, "values": [float(value) for value in values]})

    if _sha256_file(model) != expected_model_sha256:
        raise NativeReceiverError("receiver model changed during token row extraction")
    return {
        "schema": TOKEN_ROW_SCHEMA,
        "status": "NATIVE_TOKEN_ROWS_READ_ONLY",
        "source": "RECEIVER_INPUT_TOKEN_EMBEDDING_TABLE",
        "model_revision": model_revision,
        "tokenizer_revision": tokenizer_revision,
        "model_sha256": expected_model_sha256,
        "runner_revision": PINNED_LLAMA_REVISION,
        "llama_version": str(raw.get("llama_version", ""))[:80],
        "model_vocab": vocab,
        "embedding_dim": dim,
        "tensor_type": tensor_type,
        "row_bytes": row_bytes,
        "tensor_row_stride_bytes": stride,
        "requested_token_ids": ids,
        "rows": checked_rows,
        "full_table_copied": False,
        "read_only": True,
        "training_authority": 0,
        "production_route": False,
        "semantic_use_proven": False,
    }


def probe(*, home, model_path, expected_model_sha256, sender_role, receiver_role,
          sender_tap_id, sender_model_revision, sender_model_sha256, tokenizer_revision,
          receiver_model_revision, source_id, generation_id, vectors, position_ids,
          position_mode, deadline, threads=1, binary_path=None, cancel_event=None):
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
    if not isinstance(sender_model_sha256, str) or len(sender_model_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sender_model_sha256.lower()):
        raise NativeReceiverError("sender model hash missing or malformed")
    if tokenizer_revision is not None and (not isinstance(tokenizer_revision, str) or not tokenizer_revision):
        raise NativeReceiverError("tokenizer revision malformed")
    expected_model_sha256 = expected_model_sha256.lower()
    sender_model_sha256 = sender_model_sha256.lower()
    rows, input_dim, payload, input_sha256 = _vector_payload(vectors)
    positions = _validate_positions(position_ids, rows, position_mode)

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
         "--input-dim", str(input_dim), "--positions", ",".join(str(x) for x in positions),
         "--threads", str(max(1, min(int(threads), 2)))],
        payload, deadline, cancel_event,
    )
    if returncode != 0:
        raise NativeReceiverError("native receiver model probe failed")
    raw = _json_output(stdout, "probe")
    if raw.get("llama_version") != version_data.get("llama_version"):
        raise NativeReceiverError("native receiver version changed between invocations")
    if raw.get("position_ids") != positions or raw.get("position_mode") != position_mode:
        raise NativeReceiverError("native receiver position mapping differs from the sender tap")

    receiver_input_dim = raw.get("receiver_input_dim")
    output_dim = raw.get("output_dim")
    decode_status = raw.get("decode_status")
    if type(receiver_input_dim) is not int or type(output_dim) is not int or output_dim < 1:
        raise NativeReceiverError("native receiver dimensions missing")
    if raw.get("status") == "DIMENSION_MISMATCH":
        if (receiver_input_dim == input_dim or decode_status != -100
                or raw.get("row_shuffle_control_applicable") is not False
                or raw.get("row_shuffle_control_cosine") is not None):
            raise NativeReceiverError("invalid dimension-mismatch receipt")
        status = "DIMENSION_MISMATCH"
        consumed = False
        effect = False
        output_norm = 0.0
        effect_rms = 0.0
        zero_cosine = shuffle_cosine = row_shuffle_cosine = repeat_cosine = None
        row_shuffle_applicable = False
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
        row_shuffle_cosine = raw.get("row_shuffle_control_cosine")
        row_shuffle_applicable = raw.get("row_shuffle_control_applicable")
        repeat_cosine = raw.get("repeat_cosine")
        for value in (zero_cosine, shuffle_cosine, row_shuffle_cosine, repeat_cosine):
            if value is not None and (not _finite_number(value) or not -1.00001 <= float(value) <= 1.00001):
                raise NativeReceiverError("invalid native negative-control cosine")
        if type(row_shuffle_applicable) is not bool:
            raise NativeReceiverError("native row-order control applicability missing")
        if rows >= 2 and not row_shuffle_applicable:
            raise NativeReceiverError("native row-order control was not executed")
        if rows < 2 and (row_shuffle_applicable or row_shuffle_cosine is not None):
            raise NativeReceiverError("native row-order control should be not applicable")
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
        "sender_model_sha256": sender_model_sha256,
        "tokenizer_revision": tokenizer_revision,
        "receiver_model_revision": receiver_model_revision,
        "receiver_model_sha256": expected_model_sha256,
        "runner_revision": PINNED_LLAMA_REVISION,
        "llama_version": str(raw.get("llama_version", ""))[:80],
        "input_rows": rows,
        "input_dim": input_dim,
        "position_ids": positions,
        "position_mode": position_mode,
        "receiver_input_dim": receiver_input_dim,
        "output_dim": output_dim,
        "input_sha256": input_sha256,
        "decode_status": int(decode_status),
        "output_norm": float(output_norm),
        "input_effect_rms": float(effect_rms),
        "zero_control_cosine": None if zero_cosine is None else float(zero_cosine),
        "shuffle_control_cosine": None if shuffle_cosine is None else float(shuffle_cosine),
        "row_shuffle_control_cosine": None if row_shuffle_cosine is None else float(row_shuffle_cosine),
        "row_shuffle_control_applicable": row_shuffle_applicable,
        "repeat_cosine": None if repeat_cosine is None else float(repeat_cosine),
        "native_input_consumed": consumed,
        "input_effect_detected": effect,
        "status": status,
    }
