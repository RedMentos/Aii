"""Source-bound native receiver input-embedding tap contract.

This module consumes rows returned by a native llama.cpp token-embedding
row extractor. It deliberately distinguishes the receiver input embedding
table from final-RMSNorm prefill activations. It grants no inference,
injection, training, or production-B3 authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Mapping

from .latent_adapter import (
    LatentAdapterError,
    _NATIVE_INPUT_TAP_IDS,
    _activation_vector_sha256,
    _finite_vector,
    token_piece_byte_spans,
)

_SCHEMA = "v14.native-input-embedding-tap/1"


def _required_text(value, name: str) -> str:
    if type(value) is not str or not value or len(value) > 160:
        raise LatentAdapterError("native input-embedding tap requires " + name)
    return value


def _manifest_digest(material: Mapping) -> str:
    payload = json.dumps(
        dict(material), sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(b"V14-NATIVE-INPUT-EMBEDDING-TAP/1\0" + payload).hexdigest()


def build_native_input_embedding_tap_manifest(
    role: str,
    source_text: str,
    content_token_ids,
    content_token_pieces,
    input_embedding_rows,
    *,
    source_id: str,
    event_id: str,
    brain_generation_id: str,
    model_revision: str,
    tokenizer_revision: str,
) -> dict:
    """Bind selected native input-embedding rows to exact source/model/event state.

    content_token_ids and content_token_pieces must come from the same
    llama.cpp /tokenize request with add_special=false and with_pieces=true.
    input_embedding_rows must be returned for those exact IDs by a native
    token-embedding row extractor. The tap ID is role-derived and cannot be
    supplied or overridden by the caller.
    """
    if role not in _NATIVE_INPUT_TAP_IDS:
        raise LatentAdapterError("unsupported native input-embedding role")
    source_id = _required_text(source_id, "source_id")
    event_id = _required_text(event_id, "event_id")
    brain_generation_id = _required_text(brain_generation_id, "brain_generation_id")
    model_revision = _required_text(model_revision, "model_revision")
    tokenizer_revision = _required_text(tokenizer_revision, "tokenizer_revision")
    if not isinstance(content_token_ids, (list, tuple)) or not 2 <= len(content_token_ids) <= 64:
        raise LatentAdapterError("native input-embedding tap requires 2..64 content tokens")
    if any(type(token) is not int or not 0 <= token <= 2_147_483_647 for token in content_token_ids):
        raise LatentAdapterError("native input-embedding tap contains an invalid token ID")
    ids = list(content_token_ids)
    token_meta = token_piece_byte_spans(
        content_token_pieces, source_text, expected_token_ids=ids,
    )
    if not isinstance(input_embedding_rows, (list, tuple)) or len(input_embedding_rows) != len(ids):
        raise LatentAdapterError("native input-embedding rows do not match content token IDs")
    rows = [_finite_vector(row, "native input-embedding row") for row in input_embedding_rows]
    dimension = len(rows[0])
    if any(len(row) != dimension for row in rows):
        raise LatentAdapterError("native input-embedding row dimensions differ")
    if any(sum(value * value for value in row) <= 1e-20 for row in rows):
        raise LatentAdapterError("native input-embedding tap contains a zero row")

    material = {
        "schema": _SCHEMA,
        "role": role,
        "tap_id": _NATIVE_INPUT_TAP_IDS[role],
        "activation_space": "INPUT_EMBEDDING_F32",
        "source_span_unit": "UTF8_BYTE",
        "source_id": source_id,
        "source_sha256": token_meta["source_sha256"],
        "source_length": token_meta["source_length"],
        "event_id": event_id,
        "brain_generation_id": brain_generation_id,
        "model_revision": model_revision,
        "tokenizer_revision": tokenizer_revision,
        "token_ids": ids,
        "token_spans": token_meta["token_spans"],
        "row_positions": list(range(len(ids))),
        "embedding_dim": dimension,
        "row_sha256": [_activation_vector_sha256(row) for row in rows],
    }
    manifest = dict(material)
    manifest["manifest_sha256"] = _manifest_digest(material)
    return {"manifest": manifest, "vectors": rows}


def validate_native_input_embedding_tap_manifest(
    manifest: Mapping,
    source_text: str,
    content_token_pieces,
    input_embedding_rows,
) -> dict:
    """Rebuild a persisted manifest and reject any source, row, or binding drift."""
    if not isinstance(manifest, Mapping) or manifest.get("schema") != _SCHEMA:
        raise LatentAdapterError("unsupported native input-embedding tap manifest")
    role = manifest.get("role")
    rebuilt = build_native_input_embedding_tap_manifest(
        role,
        source_text,
        manifest.get("token_ids"),
        content_token_pieces,
        input_embedding_rows,
        source_id=manifest.get("source_id"),
        event_id=manifest.get("event_id"),
        brain_generation_id=manifest.get("brain_generation_id"),
        model_revision=manifest.get("model_revision"),
        tokenizer_revision=manifest.get("tokenizer_revision"),
    )
    if dict(manifest) != rebuilt["manifest"]:
        raise LatentAdapterError("native input-embedding manifest digest/binding mismatch")
    return rebuilt
