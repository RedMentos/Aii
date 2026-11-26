"""Opt-in read-only audit of llama.cpp attention K/V cache access.

This diagnostic exports only geometry, occupied-cell metadata and non-cryptographic
checksums. It never returns K/V values, persists cache data, updates weights or
promotes B3 authority. The native executable is pinned to one llama.cpp revision.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess

SCHEMA = "v14.native-kv-cache-audit/1"
PINNED_LLAMA_REVISION = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
MAX_TOKENS = 64
MAX_THREADS = 2


class NativeKVCacheAuditError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _id(value, name: str) -> str:
    if type(value) is not str or not value or len(value) > 128:
        raise NativeKVCacheAuditError(name + " is missing or malformed")
    return value


def _validate_native_result(value: object, *, token_count: int) -> dict:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise NativeKVCacheAuditError("native K/V audit schema mismatch")
    if value.get("runner_revision") != PINNED_LLAMA_REVISION:
        raise NativeKVCacheAuditError("native K/V audit llama.cpp revision mismatch")
    if value.get("status") != "READ_ONLY_AUDITED":
        raise NativeKVCacheAuditError("native K/V audit did not complete")
    if value.get("token_count") != token_count or type(value.get("token_count")) is not int:
        raise NativeKVCacheAuditError("native K/V audit token count mismatch")
    if value.get("read_only_verified") is not True:
        raise NativeKVCacheAuditError("native K/V cache read did not preserve the source cache")
    if type(value.get("llama_version")) is not str or not value["llama_version"]:
        raise NativeKVCacheAuditError("native llama.cpp version is missing")
    if value.get("persisted") is not False or value.get("production_route") is not False:
        raise NativeKVCacheAuditError("native K/V audit carries forbidden persistence or route authority")
    if value.get("semantic_use_proven") is not False or value.get("training_authority") != 0 or value.get("native_receiver_authority") != 0:
        raise NativeKVCacheAuditError("native K/V audit carries forbidden semantic or learning authority")
    if value.get("recurrent_state_captured") is not False:
        raise NativeKVCacheAuditError("native K/V audit must not claim recurrent-state capture")
    if value.get("memory_kind") not in {"HYBRID", "KV_CACHE"}:
        raise NativeKVCacheAuditError("native memory kind is unsupported")
    if type(value.get("recurrent_state_present")) is not bool:
        raise NativeKVCacheAuditError("recurrent-state presence flag is invalid")
    if type(value.get("active_cell_count")) is not int or value["active_cell_count"] != token_count:
        raise NativeKVCacheAuditError("native active-cell count differs from the fresh prefill token count")
    if (type(value.get("position_min")) is not int or type(value.get("position_max")) is not int
            or value["position_min"] != 0 or value["position_max"] != token_count - 1):
        raise NativeKVCacheAuditError("native active-position range differs from the fresh prefill")
    cell_map_checksum = value.get("cell_map_checksum_fnv1a64")
    if type(cell_map_checksum) is not str or len(cell_map_checksum) != 16 or any(ch not in "0123456789abcdef" for ch in cell_map_checksum):
        raise NativeKVCacheAuditError("native cell-map checksum is invalid")
    if type(value.get("layer_count")) is not int or value["layer_count"] < 1:
        raise NativeKVCacheAuditError("native attention layer count is invalid")
    layers = value.get("layers")
    if not isinstance(layers, list) or len(layers) != value["layer_count"]:
        raise NativeKVCacheAuditError("native layer audit list is incomplete")
    seen = set()
    for layer in layers:
        if not isinstance(layer, dict):
            raise NativeKVCacheAuditError("native layer audit entry is malformed")
        layer_id = layer.get("layer_id")
        if type(layer_id) is not int or layer_id < 0 or layer_id in seen:
            raise NativeKVCacheAuditError("native layer ID is invalid or duplicated")
        seen.add(layer_id)
        for field in ("k_checksum_fnv1a64", "v_checksum_fnv1a64"):
            checksum = layer.get(field)
            if type(checksum) is not str or len(checksum) != 16 or any(ch not in "0123456789abcdef" for ch in checksum):
                raise NativeKVCacheAuditError("native layer checksum is invalid")
        for field in ("k_bytes", "v_bytes", "k_head_dim", "k_heads", "v_head_dim", "v_heads"):
            if type(layer.get(field)) is not int or layer[field] <= 0:
                raise NativeKVCacheAuditError("native layer geometry or byte count is invalid")
        if layer["k_head_dim"] != layer["v_head_dim"] or layer["k_heads"] != layer["v_heads"]:
            raise NativeKVCacheAuditError("native K/V layer geometry differs")
        for field in ("k_type", "v_type"):
            if layer.get(field) not in {"F16", "F32"}:
                raise NativeKVCacheAuditError("native layer cache dtype is unsupported")
        k_size = 2 if layer["k_type"] == "F16" else 4
        v_size = 2 if layer["v_type"] == "F16" else 4
        if layer["k_bytes"] != token_count * layer["k_heads"] * layer["k_head_dim"] * k_size:
            raise NativeKVCacheAuditError("native K byte count does not match selected geometry")
        if layer["v_bytes"] != token_count * layer["v_heads"] * layer["v_head_dim"] * v_size:
            raise NativeKVCacheAuditError("native V byte count does not match selected geometry")
    return value


def audit_native_kv_cache(
    *,
    model_path: str | os.PathLike,
    binary_path: str | os.PathLike,
    expected_binary_sha256: str,
    token_ids,
    session_id: str,
    generation_id: str,
    approval,
    approval_validator,
    threads: int = 1,
    timeout_s: float = 60.0,
) -> dict:
    """Run a one-shot, approved local K/V audit and return metadata/checksums only.

    The caller must supply a Runtime one-shot approval validator. The native process
    receives token IDs on stdin; token IDs, source text and K/V values are never
    placed in argv or written to disk by this wrapper.
    """
    if not callable(approval_validator):
        raise NativeKVCacheAuditError("one-shot native K/V audit approval validator is required")
    session = _id(session_id, "session_id")
    generation = _id(generation_id, "generation_id")
    if not isinstance(token_ids, (list, tuple)) or not 1 <= len(token_ids) <= MAX_TOKENS:
        raise NativeKVCacheAuditError("token IDs must contain 1..64 values")
    if any(type(token) is not int or token < 0 or token > 2147483647 for token in token_ids):
        raise NativeKVCacheAuditError("token IDs must be non-negative int32 values")
    if type(threads) is not int or not 1 <= threads <= MAX_THREADS:
        raise NativeKVCacheAuditError("native K/V audit threads must be 1 or 2")
    if type(timeout_s) not in (int, float) or not math.isfinite(float(timeout_s)) or timeout_s <= 0 or timeout_s > 180:
        raise NativeKVCacheAuditError("native K/V audit timeout is invalid")

    model = Path(model_path).expanduser().resolve()
    binary = Path(binary_path).expanduser().resolve()
    if not model.is_file() or not binary.is_file() or not os.access(binary, os.X_OK):
        raise NativeKVCacheAuditError("installed model or native audit executable is unavailable")
    model_sha = _sha256_file(model)
    binary_sha = _sha256_file(binary)
    if type(expected_binary_sha256) is not str or len(expected_binary_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in expected_binary_sha256):
        raise NativeKVCacheAuditError("expected native binary SHA-256 is malformed")
    if binary_sha != expected_binary_sha256:
        raise NativeKVCacheAuditError("native audit executable does not match its installed SHA-256")
    token_payload = struct.pack("<" + "i" * len(token_ids), *token_ids)
    token_sha = _sha256_bytes(token_payload)
    binding = hashlib.sha256(json.dumps({
        "schema": SCHEMA,
        "model_sha256": model_sha,
        "binary_sha256": binary_sha,
        "token_ids_sha256": token_sha,
        "session_id": session,
        "generation_id": generation,
        "threads": threads,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    try:
        approved = approval_validator(approval, binding)
    except Exception as exc:
        raise NativeKVCacheAuditError("native K/V audit approval validation failed") from exc
    if approved is not True:
        raise NativeKVCacheAuditError("native K/V audit approval does not bind this exact request")

    try:
        completed = subprocess.run(
            [str(binary), "--model", str(model), "--token-count", str(len(token_ids)), "--threads", str(threads)],
            input=token_payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=float(timeout_s),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NativeKVCacheAuditError("native K/V audit process failed or timed out") from exc
    if completed.returncode != 0:
        raise NativeKVCacheAuditError("native K/V audit returned a non-zero status")
    if _sha256_file(model) != model_sha or _sha256_file(binary) != binary_sha:
        raise NativeKVCacheAuditError("model or native audit executable changed during the audit")
    try:
        native = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NativeKVCacheAuditError("native K/V audit output is not valid JSON") from exc
    native = _validate_native_result(native, token_count=len(token_ids))
    return {
        "schema": SCHEMA,
        "status": "READ_ONLY_AUDITED",
        "target_environment": "LOCAL_LINUX",
        "runner_revision": PINNED_LLAMA_REVISION,
        "model_sha256": model_sha,
        "binary_sha256": binary_sha,
        "token_ids_sha256": token_sha,
        "session_id": session,
        "generation_id": generation,
        "approval_binding_sha256": binding,
        "native": native,
        "persisted": False,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }
