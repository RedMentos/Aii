"""Source-bound native receiver input-embedding tap contract.

This module consumes rows returned by a native llama.cpp token-embedding
row extractor. It deliberately distinguishes the receiver input embedding
table from final-RMSNorm prefill activations. It grants no inference,
injection, training, or production-B3 authority.

The extractor receipt is a provenance envelope emitted by the native wrapper.
The public llama.cpp row API returns an element count, not row IDs; therefore
the wrapper must echo the exact requested token IDs and the successful element
count only after validating every ID and the API return value. The caller must
independently hash the installed model and extractor binary before constructing
this manifest. The manifest SHA is integrity, not a signature.
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

_SCHEMA = "v14.native-input-embedding-tap/2"
_RECEIPT_SCHEMA = "v14.llama-token-embedding-rows-receipt/1"
_API_SYMBOL = "llama_model_get_tok_embd_rows"
_API_HEADER = "src/llama-ext.h"
_API_STABILITY = "STAGING_WIP"
_RECEIPT_FIELDS = frozenset({
    "schema", "api_symbol", "api_header", "api_stability",
    "llama_cpp_revision", "extractor_binary_sha256",
    "model_revision", "model_sha256", "source_tensor_type",
    "output_dtype", "vocab_size", "embedding_dim",
    "requested_token_ids", "elements_written",
})


def _required_text(value, name: str) -> str:
    if type(value) is not str or not value or len(value) > 160:
        raise LatentAdapterError("native input-embedding tap requires " + name)
    return value


def _hex_digest(value, name: str, length: int) -> str:
    if (type(value) is not str or len(value) != length
            or any(ch not in "0123456789abcdef" for ch in value)):
        raise LatentAdapterError("native input-embedding tap " + name + " must be lowercase hex")
    return value


def _manifest_digest(material: Mapping) -> str:
    payload = json.dumps(
        dict(material), sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(b"V14-NATIVE-INPUT-EMBEDDING-TAP/2\0" + payload).hexdigest()


def _validate_extractor_receipt(
    receipt: Mapping,
    token_ids: list[int],
    dimension: int,
    model_revision: str,
    model_sha256: str,
) -> dict:
    if not isinstance(receipt, Mapping) or set(receipt) != _RECEIPT_FIELDS:
        raise LatentAdapterError("native extractor receipt fields are not canonical")
    if receipt.get("schema") != _RECEIPT_SCHEMA:
        raise LatentAdapterError("native extractor receipt schema is unsupported")
    if (receipt.get("api_symbol") != _API_SYMBOL
            or receipt.get("api_header") != _API_HEADER
            or receipt.get("api_stability") != _API_STABILITY):
        raise LatentAdapterError("native extractor API identity/stability differs")
    llama_cpp_revision = receipt.get("llama_cpp_revision")
    if (type(llama_cpp_revision) is not str or len(llama_cpp_revision) != 40
            or any(ch not in "0123456789abcdef" for ch in llama_cpp_revision)):
        raise LatentAdapterError("native extractor llama.cpp revision is invalid")
    extractor_sha = _hex_digest(receipt.get("extractor_binary_sha256"), "binary SHA-256", 64)
    receipt_model_sha = _hex_digest(receipt.get("model_sha256"), "model SHA-256", 64)
    if receipt.get("model_revision") != model_revision or receipt_model_sha != model_sha256:
        raise LatentAdapterError("native extractor model binding differs from installed manifest")
    tensor_type = receipt.get("source_tensor_type")
    if (type(tensor_type) is not str or not 1 <= len(tensor_type) <= 32
            or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_" for ch in tensor_type)):
        raise LatentAdapterError("native extractor source tensor type is invalid")
    if receipt.get("output_dtype") != "f32":
        raise LatentAdapterError("native extractor output must be F32")
    vocab_size = receipt.get("vocab_size")
    if type(vocab_size) is not int or not 2 <= vocab_size <= 1_000_000:
        raise LatentAdapterError("native extractor vocabulary size is invalid")
    if any(token_id >= vocab_size for token_id in token_ids):
        raise LatentAdapterError("native extractor token ID is outside the receiver vocabulary")
    if type(receipt.get("embedding_dim")) is not int or receipt["embedding_dim"] != dimension:
        raise LatentAdapterError("native extractor embedding dimension differs from rows")
    if (not isinstance(receipt.get("requested_token_ids"), list)
            or receipt["requested_token_ids"] != token_ids
            or any(type(token_id) is not int for token_id in receipt["requested_token_ids"])):
        raise LatentAdapterError("native extractor requested token IDs/order differ from source")
    expected_elements = len(token_ids) * dimension
    if (type(receipt.get("elements_written")) is not int
            or receipt["elements_written"] != expected_elements
            or not 1 <= expected_elements <= 64 * 8192):
        raise LatentAdapterError("native extractor returned element count differs from requested rows")
    return {
        "schema": _RECEIPT_SCHEMA,
        "api_symbol": _API_SYMBOL,
        "api_header": _API_HEADER,
        "api_stability": _API_STABILITY,
        "llama_cpp_revision": llama_cpp_revision,
        "extractor_binary_sha256": extractor_sha,
        "model_revision": model_revision,
        "model_sha256": model_sha256,
        "source_tensor_type": tensor_type,
        "output_dtype": "f32",
        "vocab_size": vocab_size,
        "embedding_dim": dimension,
        "requested_token_ids": list(token_ids),
        "elements_written": expected_elements,
    }


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
    model_sha256: str,
    tokenizer_revision: str,
    extractor_receipt: Mapping,
) -> dict:
    """Bind selected native input-embedding rows to exact source/model/event state.

    content_token_ids and content_token_pieces must come from the same
    llama.cpp /tokenize request with add_special=false and with_pieces=true.
    input_embedding_rows must be the F32 rows returned for those exact IDs.
    extractor_receipt must echo the exact request IDs and successful element
    count from the pinned native wrapper; model and binary SHA-256 values must
    have been independently checked by the caller.
    """
    if role not in _NATIVE_INPUT_TAP_IDS:
        raise LatentAdapterError("unsupported native input-embedding role")
    source_id = _required_text(source_id, "source_id")
    event_id = _required_text(event_id, "event_id")
    brain_generation_id = _required_text(brain_generation_id, "brain_generation_id")
    model_revision = _required_text(model_revision, "model_revision")
    tokenizer_revision = _required_text(tokenizer_revision, "tokenizer_revision")
    model_sha256 = _hex_digest(model_sha256, "model SHA-256", 64)
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
    receipt = _validate_extractor_receipt(
        extractor_receipt, ids, dimension, model_revision, model_sha256,
    )

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
        "model_sha256": model_sha256,
        "tokenizer_revision": tokenizer_revision,
        "token_ids": ids,
        "token_spans": token_meta["token_spans"],
        "row_positions": list(range(len(ids))),
        "embedding_dim": dimension,
        "row_sha256": [_activation_vector_sha256(row) for row in rows],
        "extractor_receipt": receipt,
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
        model_sha256=manifest.get("model_sha256"),
        tokenizer_revision=manifest.get("tokenizer_revision"),
        extractor_receipt=manifest.get("extractor_receipt"),
    )
    if dict(manifest) != rebuilt["manifest"]:
        raise LatentAdapterError("native input-embedding manifest digest/binding mismatch")
    return rebuilt
