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
import stat
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
EFFECT_EPSILON = 1.0e-7


class NativeReceiverUnavailable(RuntimeError):
    pass


class NativeReceiverError(ValueError):
    pass


def _fd_identity(info):
    return (
        info.st_dev, info.st_ino, info.st_size,
        info.st_mtime_ns, info.st_ctime_ns,
    )


def _sha256_fd(fd: int) -> str:
    """Hash an already-open regular file without reopening its mutable pathname."""
    digest = hashlib.sha256()
    offset = 0
    while True:
        block = os.pread(fd, 8 * 1024 * 1024, offset)
        if not block:
            break
        digest.update(block)
        offset += len(block)
    return digest.hexdigest()


def _open_model_descriptor(model: Path, models_root: Path, expected_digest: str):
    """Open the exact installed model beneath models_root and pin its inode for the child.

    Every path component is opened relative to a held directory descriptor with
    O_NOFOLLOW. The final regular-file descriptor is inherited by the native
    child and addressed as /proc/self/fd/N, so a pathname replacement after
    verification cannot redirect llama_model_load_from_file().
    """
    if os.name != "posix" or not Path("/proc/self/fd").is_dir():
        raise NativeReceiverUnavailable("descriptor-pinned model loading requires POSIX /proc/self/fd")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    nonblock = getattr(os, "O_NONBLOCK", 0)
    if not nofollow or not directory or not nonblock or os.open not in getattr(os, "supports_dir_fd", set()):
        raise NativeReceiverUnavailable("descriptor-pinned model loading requires no-follow dirfd support")
    try:
        relative = model.relative_to(models_root)
    except ValueError as exc:
        raise NativeReceiverError("receiver model escaped the installed models root") from exc
    if not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise NativeReceiverError("receiver model relative path is unsafe")

    directory_flags = os.O_RDONLY | directory | nofollow | getattr(os, "O_CLOEXEC", 0)
    file_flags = os.O_RDONLY | nofollow | nonblock | getattr(os, "O_CLOEXEC", 0)
    try:
        root_fd = os.open(models_root, directory_flags)
    except OSError as exc:
        raise NativeReceiverError("receiver models root cannot be opened without following links") from exc
    parent_fd = root_fd
    fd = None
    try:
        for component in relative.parts[:-1]:
            next_fd = os.open(component, directory_flags, dir_fd=parent_fd)
            if parent_fd != root_fd:
                os.close(parent_fd)
            parent_fd = next_fd
        fd = os.open(relative.parts[-1], file_flags, dir_fd=parent_fd)
    except OSError as exc:
        if fd is not None:
            os.close(fd)
        raise NativeReceiverError("receiver model path changed or contains a linked/non-directory component") from exc
    finally:
        if parent_fd != root_fd:
            os.close(parent_fd)
        os.close(root_fd)

    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size < 1:
            raise NativeReceiverError("receiver model descriptor is not a non-empty regular file")
        actual = _sha256_fd(fd)
        after = os.fstat(fd)
        if _fd_identity(before) != _fd_identity(after):
            raise NativeReceiverError("receiver model changed while its descriptor was hashed")
        if actual != expected_digest:
            raise NativeReceiverError("receiver model hash differs from installed manifest")
        return fd, _fd_identity(after)
    except Exception:
        os.close(fd)
        raise


def _verify_model_descriptor(fd: int, expected_digest: str, expected_identity):
    # A rename of the verified inode changes ctime even though the inherited
    # descriptor still names the exact approved file. Keep dev/inode/size/mtime
    # stable and re-hash the descriptor; do not confuse a pathname replacement
    # with an in-place model mutation.
    content_identity = lambda info: (
        info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
    )
    expected_content_identity = expected_identity[:4]
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or content_identity(before) != expected_content_identity:
        raise NativeReceiverError("receiver model descriptor identity changed during native probe")
    actual = _sha256_fd(fd)
    after = os.fstat(fd)
    if content_identity(after) != expected_content_identity or actual != expected_digest:
        raise NativeReceiverError("receiver model bytes changed during native probe")




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


def _run_cancelable(command, payload, deadline, cancel_event, *, pass_fds=()):
    kwargs = {}
    if pass_fds:
        if os.name != "posix":
            raise NativeReceiverUnavailable("native model descriptor inheritance requires POSIX")
        kwargs["pass_fds"] = tuple(pass_fds)
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs
    )
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
    models_dir = root / "models"
    if models_dir.is_symlink():
        raise NativeReceiverError("receiver models root symlink refused")
    models_root = models_dir.resolve(strict=True)
    if not models_root.is_relative_to(root):
        raise NativeReceiverError("receiver models root escaped home")
    model = Path(model_path)
    if model.is_symlink():
        raise NativeReceiverError("receiver model symlink refused")
    model = model.resolve(strict=True)
    if not model.is_relative_to(models_root) or not model.is_file():
        raise NativeReceiverError("receiver model must be an installed file under home/models")

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
    model_fd, model_identity = _open_model_descriptor(model, models_root, expected_model_sha256)
    try:
        returncode, stdout, stderr = _run_cancelable(
            [str(binary), "--model", f"/proc/self/fd/{model_fd}", "--rows", str(rows),
             "--input-dim", str(input_dim), "--positions", ",".join(str(x) for x in positions),
             "--threads", str(max(1, min(int(threads), 2)))],
            payload, deadline, cancel_event, pass_fds=(model_fd,),
        )
        _verify_model_descriptor(model_fd, expected_model_sha256, model_identity)
    finally:
        os.close(model_fd)
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
