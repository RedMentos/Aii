"""Verified caller for the pinned native llama.cpp input-embedding row extractor.

This wrapper supplies hashes computed from the installed files, validates the
native receipt against those hashes, and returns rows without persisting source
text or model data. Token IDs must come from the caller's exact tokenizer request.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import stat
import subprocess
import time

PINNED_LLAMA_REVISION = "2851b3bcbf8d993a2243ae751c0a7dfa8e944a40"
RECEIPT_SCHEMA = "v14.llama-token-embedding-rows-receipt/1"
OUTPUT_SCHEMA = "v14.native-input-embedding-extractor/1"
API_SYMBOL = "llama_model_get_tok_embd_rows"
API_HEADER = "src/llama-ext.h"
API_STABILITY = "STAGING_WIP"
MAX_TOKENS = 64
MAX_DIM = 8192
MAX_ELEMENTS = MAX_TOKENS * MAX_DIM
MAX_MODEL_BYTES = 128 * 1024 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_TIMEOUT_SECONDS = 120
_RECEIPT_FIELDS = frozenset({
    "schema", "api_symbol", "api_header", "api_stability",
    "llama_cpp_revision", "extractor_binary_sha256",
    "model_revision", "model_sha256", "source_tensor_type",
    "output_dtype", "vocab_size", "embedding_dim",
    "requested_token_ids", "elements_written",
})


class NativeInputEmbeddingError(ValueError):
    """The native input-embedding extraction contract failed closed."""


def _hex_digest(value, name):
    if (type(value) is not str or len(value) != 64
            or any(ch not in "0123456789abcdef" for ch in value)):
        raise NativeInputEmbeddingError(name + " must be lowercase SHA-256")
    return value


def _file_identity(value):
    return (
        value.st_dev, value.st_ino, value.st_size,
        value.st_mtime_ns, value.st_ctime_ns,
    )


def _hash_regular_file(path):
    """Hash a stable regular file without following symlinks or blocking on special files."""
    path = Path(path)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    nonblock = getattr(os, "O_NONBLOCK", None)
    if nofollow is None or nonblock is None:
        raise NativeInputEmbeddingError("platform lacks safe no-follow file opening")
    flags = os.O_RDONLY | nofollow | nonblock | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(str(path), flags)
    except OSError as exc:
        raise NativeInputEmbeddingError("model or extractor file cannot be opened safely") from exc
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_size <= 0
                or before.st_size > MAX_MODEL_BYTES):
            raise NativeInputEmbeddingError("model or extractor must be a bounded regular file")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(fd)
        try:
            path_stat = os.stat(path, follow_symlinks=False)
        except OSError as exc:
            raise NativeInputEmbeddingError("model or extractor path changed while hashing") from exc
        if (not stat.S_ISREG(path_stat.st_mode)
                or _file_identity(before) != _file_identity(after)
                or _file_identity(after) != _file_identity(path_stat)):
            raise NativeInputEmbeddingError("model or extractor changed while hashing")
        return digest.hexdigest(), _file_identity(after)
    finally:
        os.close(fd)


def _stat_regular_file(path):
    path = Path(path)
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(str(path), flags)
    except OSError as exc:
        raise NativeInputEmbeddingError("model or extractor path changed during extraction") from exc
    try:
        opened = os.fstat(fd)
        current = os.stat(path, follow_symlinks=False)
        if (not stat.S_ISREG(opened.st_mode) or not stat.S_ISREG(current.st_mode)
                or _file_identity(opened) != _file_identity(current)):
            raise NativeInputEmbeddingError("model or extractor changed during extraction")
        return _file_identity(opened)
    finally:
        os.close(fd)


def _safe_file(path, name, *, executable=False):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise NativeInputEmbeddingError(name + " must be an existing regular non-symlink file")
    resolved = path.resolve(strict=True)
    if executable and not os.access(resolved, os.X_OK):
        raise NativeInputEmbeddingError("native extractor is not executable")
    return resolved


def _reject_json_constant(value):
    raise NativeInputEmbeddingError("native extractor returned a non-finite JSON constant")


def _validate_rows(rows, token_ids, receipt):
    dimension = receipt.get("embedding_dim")
    if type(dimension) is not int or not 1 <= dimension <= MAX_DIM:
        raise NativeInputEmbeddingError("native extractor embedding dimension is invalid")
    if not isinstance(rows, list) or len(rows) != len(token_ids):
        raise NativeInputEmbeddingError("native extractor row count differs from token IDs")
    validated = []
    for row in rows:
        if not isinstance(row, list) or len(row) != dimension:
            raise NativeInputEmbeddingError("native extractor row geometry is invalid")
        vector = []
        norm_squared = 0.0
        for value in row:
            if (type(value) not in (int, float) or not math.isfinite(float(value))
                    or abs(float(value)) > 1.0e6):
                raise NativeInputEmbeddingError("native extractor row contains invalid F32 values")
            number = float(value)
            vector.append(number)
            norm_squared += number * number
        if not math.isfinite(norm_squared) or norm_squared <= 1.0e-20:
            raise NativeInputEmbeddingError("native extractor returned a zero row")
        validated.append(vector)
    return validated



class _NativeOutputLimit(Exception):
    pass


def _kill_and_reap(process):
    if process is None:
        return
    try:
        if process.poll() is None:
            process.kill()
    except OSError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def _run_bounded_native_process(argv, timeout_seconds):
    """Capture at most MAX_OUTPUT_BYTES and kill/reap a runaway native child."""
    process = None
    selector = None
    chunks = []
    total = 0
    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
            close_fds=True,
        )
        if process.stdout is None:
            raise NativeInputEmbeddingError("native extractor stdout pipe is unavailable")
        os.set_blocking(process.stdout.fileno(), False)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout_seconds
        eof = False
        while not eof:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            events = selector.select(min(remaining, 0.1))
            if not events:
                continue
            chunk = os.read(
                process.stdout.fileno(),
                min(65536, MAX_OUTPUT_BYTES + 1 - total),
            )
            if not chunk:
                eof = True
                break
            total += len(chunk)
            if total > MAX_OUTPUT_BYTES:
                raise _NativeOutputLimit
            chunks.append(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        return_code = process.wait(timeout=remaining)
        if return_code != 0:
            raise NativeInputEmbeddingError("native input-embedding extractor failed")
        try:
            return b"".join(chunks).decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise NativeInputEmbeddingError("native input-embedding extractor returned invalid UTF-8") from exc
    except _NativeOutputLimit as exc:
        _kill_and_reap(process)
        raise NativeInputEmbeddingError("native input-embedding extractor output exceeded its bound") from exc
    except TimeoutError as exc:
        _kill_and_reap(process)
        raise NativeInputEmbeddingError("native input-embedding extraction timed out") from exc
    except subprocess.TimeoutExpired as exc:
        _kill_and_reap(process)
        raise NativeInputEmbeddingError("native input-embedding extraction timed out") from exc
    except OSError as exc:
        _kill_and_reap(process)
        raise NativeInputEmbeddingError("native input-embedding extractor could not start or stream output") from exc
    except BaseException:
        _kill_and_reap(process)
        raise
    finally:
        if selector is not None:
            selector.close()
        if process is not None and process.stdout is not None:
            process.stdout.close()


def extract_native_input_embedding_rows(
    binary_path,
    model_path,
    model_revision,
    token_ids,
    *,
    model_root=None,
    expected_model_sha256=None,
    prepare_idle=None,
    timeout_seconds=120,
):
    """Read selected receiver token-embedding rows from an already-installed GGUF.

    token_ids must be the exact ordered IDs from the same tokenizer request
    that produced the caller's source token pieces. This function does not
    tokenize, persist rows, change model files, or grant inference/training/B3
    authority.
    """
    if (type(model_revision) is not str or not model_revision
            or len(model_revision) > 160
            or any(ord(ch) < 0x21 or ord(ch) > 0x7e for ch in model_revision)):
        raise NativeInputEmbeddingError("installed model revision is invalid")
    if (not isinstance(token_ids, (list, tuple)) or not 2 <= len(token_ids) <= MAX_TOKENS
            or any(type(token_id) is not int or not 0 <= token_id <= 2_147_483_647
                   for token_id in token_ids)):
        raise NativeInputEmbeddingError("native input tap requires 2..64 exact nonnegative token IDs")
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise NativeInputEmbeddingError("native extractor timeout is outside the bounded limit")

    if model_root is None or expected_model_sha256 is None or not callable(prepare_idle):
        raise NativeInputEmbeddingError("registered model root, manifest hash and idle guard are required")
    binary = _safe_file(binary_path, "native extractor", executable=True)
    model = _safe_file(model_path, "installed model")
    if model_root is not None:
        root = Path(model_root)
        if root.is_symlink() or not root.is_dir():
            raise NativeInputEmbeddingError("registered model root is missing or linked")
        root = root.resolve(strict=True)
        if not model.is_relative_to(root):
            raise NativeInputEmbeddingError("installed model escaped its registered root")

    model_sha, model_identity = _hash_regular_file(model)
    binary_sha, binary_identity = _hash_regular_file(binary)
    if expected_model_sha256 is not None:
        expected_model_sha256 = _hex_digest(expected_model_sha256, "installed model hash")
        if model_sha != expected_model_sha256:
            raise NativeInputEmbeddingError("installed model hash differs from its manifest")

    try:
        prepare_idle()
    except Exception as exc:
        raise NativeInputEmbeddingError("runtime must be idle and native model pool released") from exc

    argv = [
        str(binary), "--extract",
        "--model", str(model),
        "--model-revision", model_revision,
        "--model-sha256", model_sha,
        "--extractor-sha256", binary_sha,
        "--token-ids", ",".join(str(token_id) for token_id in token_ids),
    ]
    native_stdout = _run_bounded_native_process(argv, timeout_seconds)

    try:
        result = json.loads(native_stdout, parse_constant=_reject_json_constant)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise NativeInputEmbeddingError("native input-embedding extractor returned invalid JSON") from exc

    model_identity_after = _stat_regular_file(model)
    binary_identity_after = _stat_regular_file(binary)
    if (model_identity_after != model_identity or binary_identity_after != binary_identity):
        raise NativeInputEmbeddingError("model or extractor changed during native extraction")

    if (not isinstance(result, dict)
            or set(result) != {"schema", "status", "receipt", "rows"}
            or result.get("schema") != OUTPUT_SCHEMA
            or result.get("status") != "COMPLETE"):
        raise NativeInputEmbeddingError("native input-embedding output schema/status differs")
    receipt = result.get("receipt")
    if not isinstance(receipt, dict) or set(receipt) != _RECEIPT_FIELDS:
        raise NativeInputEmbeddingError("native extractor receipt fields are not canonical")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise NativeInputEmbeddingError("native extractor receipt schema is unsupported")
    if (receipt.get("api_symbol") != API_SYMBOL
            or receipt.get("api_header") != API_HEADER
            or receipt.get("api_stability") != API_STABILITY
            or receipt.get("llama_cpp_revision") != PINNED_LLAMA_REVISION):
        raise NativeInputEmbeddingError("native extractor API identity/revision differs")
    if (receipt.get("extractor_binary_sha256") != binary_sha
            or receipt.get("model_sha256") != model_sha
            or receipt.get("model_revision") != model_revision):
        raise NativeInputEmbeddingError("native extractor receipt does not bind installed files")
    tensor_type = receipt.get("source_tensor_type")
    if (type(tensor_type) is not str or not 1 <= len(tensor_type) <= 32
            or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_" for ch in tensor_type)):
        raise NativeInputEmbeddingError("native extractor source tensor type is invalid")
    if receipt.get("output_dtype") != "f32":
        raise NativeInputEmbeddingError("native extractor output is not F32")
    vocab_size = receipt.get("vocab_size")
    if type(vocab_size) is not int or not 2 <= vocab_size <= 1_000_000:
        raise NativeInputEmbeddingError("native extractor vocabulary size is invalid")
    if any(token_id >= vocab_size for token_id in token_ids):
        raise NativeInputEmbeddingError("native extractor token ID is outside its vocabulary")
    returned_ids = receipt.get("requested_token_ids")
    if (not isinstance(returned_ids, list)
            or any(type(token_id) is not int for token_id in returned_ids)
            or returned_ids != list(token_ids)):
        raise NativeInputEmbeddingError("native extractor token IDs/order differ from request")
    dimension = receipt.get("embedding_dim")
    expected_elements = len(token_ids) * dimension if type(dimension) is int else 0
    if (type(receipt.get("elements_written")) is not int
            or receipt["elements_written"] != expected_elements
            or not 1 <= expected_elements <= MAX_ELEMENTS):
        raise NativeInputEmbeddingError("native extractor returned an incomplete row count")

    rows = _validate_rows(result.get("rows"), token_ids, receipt)
    return {
        "status": "COMPLETE",
        "receipt": dict(receipt),
        "rows": rows,
        "model_sha256": model_sha,
        "extractor_binary_sha256": binary_sha,
    }
