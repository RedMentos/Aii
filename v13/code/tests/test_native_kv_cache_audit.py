from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from v13.native_kv_cache_audit import (
    NativeKVCacheAuditError,
    SCHEMA,
    PINNED_LLAMA_REVISION,
    audit_native_kv_cache,
)


def _fake_native_binary(tmp_path: Path, payload: dict | None = None) -> Path:
    payload = payload or {
        "schema": SCHEMA,
        "runner_revision": PINNED_LLAMA_REVISION,
        "status": "READ_ONLY_AUDITED",
        "llama_version": "pinned-test",
        "token_count": 3,
        "memory_kind": "HYBRID",
        "recurrent_state_present": True,
        "recurrent_state_captured": False,
        "active_cell_count": 3,
        "position_min": 0,
        "position_max": 2,
        "cell_map_checksum_fnv1a64": "0123456789abcdef",
        "layer_count": 1,
        "layers": [{
            "layer_id": 2,
            "k_head_dim": 4,
            "k_heads": 2,
            "v_head_dim": 4,
            "v_heads": 2,
            "k_type": "F16",
            "v_type": "F16",
            "k_bytes": 48,
            "v_bytes": 48,
            "k_checksum_fnv1a64": "0123456789abcdef",
            "v_checksum_fnv1a64": "fedcba9876543210",
        }],
        "read_only_verified": True,
        "persisted": False,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }
    script = tmp_path / "fake-kv-audit"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json,sys\n"
        "sys.stdin.buffer.read()\n"
        "print(" + repr(json.dumps(payload, separators=(",", ":"))) + ")\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def _invoke(tmp_path: Path, *, payload=None, approval=True, model_bytes=b"model", token_ids=(1, 2, 3)):
    model = tmp_path / "model.gguf"
    model.write_bytes(model_bytes)
    binary = _fake_native_binary(tmp_path, payload)
    return audit_native_kv_cache(
        model_path=model,
        binary_path=binary,
        expected_binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
        token_ids=token_ids,
        session_id="session-1",
        generation_id="generation-1",
        approval=approval,
        approval_validator=lambda supplied, binding: supplied is True and len(binding) == 64,
    )


def test_valid_read_only_hybrid_audit_is_bound_and_ephemeral(tmp_path):
    result = _invoke(tmp_path)
    assert result["status"] == "READ_ONLY_AUDITED"
    assert result["target_environment"] == "LOCAL_LINUX"
    assert result["native"]["memory_kind"] == "HYBRID"
    assert result["native"]["recurrent_state_present"] is True
    assert result["native"]["recurrent_state_captured"] is False
    assert result["native"]["layers"][0]["layer_id"] == 2
    assert result["persisted"] is False
    assert result["production_route"] is False
    assert result["training_authority"] == 0
    assert "token_ids" not in result and "vectors" not in result


def test_wrong_revision_is_rejected(tmp_path):
    payload = {
        "schema": SCHEMA, "runner_revision": "wrong", "status": "READ_ONLY_AUDITED",
        "llama_version": "pinned-test", "token_count": 3, "read_only_verified": True, "persisted": False,
        "production_route": False, "semantic_use_proven": False, "training_authority": 0,
        "native_receiver_authority": 0, "recurrent_state_captured": False,
        "memory_kind": "KV_CACHE", "recurrent_state_present": False,
        "active_cell_count": 3, "position_min": 0, "position_max": 2,
        "cell_map_checksum_fnv1a64": "0123456789abcdef", "layer_count": 1, "layers": [],
    }
    with pytest.raises(NativeKVCacheAuditError, match="revision"):
        _invoke(tmp_path, payload=payload)


def test_no_read_only_claim_or_authority_promotion(tmp_path):
    payload = {
        "schema": SCHEMA, "runner_revision": PINNED_LLAMA_REVISION,
        "status": "READ_ONLY_AUDITED", "token_count": 3,
        "llama_version": "pinned-test", "read_only_verified": False, "persisted": False,
        "production_route": False, "semantic_use_proven": False,
        "training_authority": 0, "native_receiver_authority": 0,
        "recurrent_state_captured": False, "memory_kind": "KV_CACHE",
        "recurrent_state_present": False, "active_cell_count": 3,
        "layer_count": 1, "layers": [],
    }
    with pytest.raises(NativeKVCacheAuditError, match="did not preserve"):
        _invoke(tmp_path, payload=payload)


def test_invalid_layer_checksum_is_rejected(tmp_path):
    payload = {
        "schema": SCHEMA, "runner_revision": PINNED_LLAMA_REVISION,
        "status": "READ_ONLY_AUDITED", "token_count": 3,
        "read_only_verified": True, "persisted": False,
        "production_route": False, "semantic_use_proven": False,
        "training_authority": 0, "native_receiver_authority": 0,
        "recurrent_state_captured": False, "memory_kind": "KV_CACHE",
        "recurrent_state_present": False, "active_cell_count": 3,
        "position_min": 0, "position_max": 2, "cell_map_checksum_fnv1a64": "0123456789abcdef",
        "llama_version": "pinned-test", "layer_count": 1, "layers": [{
            "layer_id": 0, "k_head_dim": 4, "k_heads": 1, "v_head_dim": 4, "v_heads": 1,
            "k_type": "F16", "v_type": "F16",
            "k_bytes": 16, "v_bytes": 16,
            "k_checksum_fnv1a64": "not-a-checksum",
            "v_checksum_fnv1a64": "fedcba9876543210",
        }],
    }
    with pytest.raises(NativeKVCacheAuditError, match="checksum"):
        _invoke(tmp_path, payload=payload)


def test_authority_promotion_is_rejected(tmp_path):
    payload = {
        "schema": SCHEMA, "runner_revision": PINNED_LLAMA_REVISION,
        "status": "READ_ONLY_AUDITED", "llama_version": "pinned-test", "token_count": 3,
        "read_only_verified": True, "persisted": False, "production_route": True,
        "semantic_use_proven": False, "training_authority": 0, "native_receiver_authority": 0,
        "recurrent_state_captured": False, "memory_kind": "KV_CACHE",
        "recurrent_state_present": False, "active_cell_count": 3,
        "position_min": 0, "position_max": 2, "cell_map_checksum_fnv1a64": "0123456789abcdef",
        "layer_count": 1, "layers": [{
            "layer_id": 0, "k_head_dim": 4, "k_heads": 1, "v_head_dim": 4, "v_heads": 1,
            "k_type": "F16", "v_type": "F16", "k_bytes": 16, "v_bytes": 16,
            "k_checksum_fnv1a64": "0123456789abcdef", "v_checksum_fnv1a64": "fedcba9876543210",
        }],
    }
    with pytest.raises(NativeKVCacheAuditError, match="authority"):
        _invoke(tmp_path, payload=payload)


def test_unregistered_binary_hash_is_rejected_before_launch(tmp_path):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")
    binary = _fake_native_binary(tmp_path)
    with pytest.raises(NativeKVCacheAuditError, match="installed SHA-256"):
        audit_native_kv_cache(
            model_path=model, binary_path=binary, expected_binary_sha256="0" * 64,
            token_ids=[1, 2, 3], session_id="session-1", generation_id="generation-1",
            approval=True, approval_validator=lambda *_: True,
        )


def test_approval_is_mandatory_and_one_shot_binding_is_passed(tmp_path):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")
    binary = _fake_native_binary(tmp_path)
    seen = []
    with pytest.raises(NativeKVCacheAuditError, match="approval"):
        audit_native_kv_cache(
            model_path=model, binary_path=binary,
            expected_binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            token_ids=[1, 2, 3], session_id="session-1", generation_id="generation-1",
            approval=False, approval_validator=lambda supplied, binding: seen.append(binding) or False,
        )
    assert len(seen) == 1 and len(seen[0]) == 64


def test_bad_token_ids_are_rejected_before_process(tmp_path):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")
    binary = _fake_native_binary(tmp_path)
    with pytest.raises(NativeKVCacheAuditError, match="token IDs"):
        audit_native_kv_cache(
            model_path=model, binary_path=binary,
            expected_binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            token_ids=[1, -1], session_id="session-1", generation_id="generation-1",
            approval=True, approval_validator=lambda *_: True,
        )


def test_model_or_binary_mutation_during_audit_is_rejected(tmp_path, monkeypatch):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")
    binary = _fake_native_binary(tmp_path)
    original_run = __import__("subprocess").run

    def mutate_model(*args, **kwargs):
        completed = original_run(*args, **kwargs)
        model.write_bytes(b"changed")
        return completed

    monkeypatch.setattr("v13.native_kv_cache_audit.subprocess.run", mutate_model)
    with pytest.raises(NativeKVCacheAuditError, match="changed during"):
        audit_native_kv_cache(
            model_path=model, binary_path=binary,
            expected_binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            token_ids=[1, 2, 3], session_id="session-1", generation_id="generation-1",
            approval=True, approval_validator=lambda *_: True,
        )
