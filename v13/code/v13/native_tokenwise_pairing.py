"""Source-bound assembly of sender final-RMSNorm rows and receiver input rows.

This is a Perception-owned diagnostic adapter input builder. It keeps the
TOKENWISE receiver-input path separate from LATENT_PREFIX_V1 event pooling.
It performs no persistence, fitting, inference, weight update, or authority
promotion; callers must apply the existing consent/lab gates before fitting.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import math

from .latent_adapter import (
    LatentAdapterError,
    align_token_rows_by_byte_pieces,
    build_tokenwise_tap_manifest,
)
from .native_input_embedding_tap import (
    build_native_input_embedding_tap_manifest_from_extractor_output,
)

SCHEMA = "v14.native-tokenwise-pairing/1"
_SENDER_ROLES = frozenset({"B1_DETAIL", "B2_GIST"})
_RECEIVER_TAPS = {
    "B1_DETAIL": "b1.input-embedding.v1",
    "B2_GIST": "b2.input-embedding.v1",
    "C3_LANGUAGE": "c3.input-embedding.v1",
}
_ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-")


def _required_id(value, name: str) -> str:
    if (type(value) is not str or not 1 <= len(value) <= 128
            or any(ch not in _ID_CHARS for ch in value)):
        raise LatentAdapterError(name + " must be a bounded opaque identifier")
    return value


def _sha256(value, name: str) -> str:
    if (type(value) is not str or len(value) != 64
            or any(ch not in "0123456789abcdef" for ch in value)):
        raise LatentAdapterError(name + " must be lowercase SHA-256")
    return value


def _record_digest(material: Mapping) -> str:
    raw = json.dumps(
        dict(material), sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(b"V14-NATIVE-TOKENWISE-PAIRING/1\0" + raw).hexdigest()


def build_native_tokenwise_pair_record(
    source_text: str,
    source_ref: Mapping,
    sender_content_token_ids,
    sender_content_token_pieces,
    sender_tap_packet: Mapping,
    sender_tap_data: Mapping,
    receiver_content_token_ids,
    receiver_content_token_pieces,
    receiver_extractor_output: Mapping,
    *,
    source_id: str,
    session_id: str,
    event_id: str,
    brain_generation_id: str,
    sender_role: str,
    receiver_role: str,
    sender_tap_id: str,
    receiver_tap_id: str,
    sender_model_revision: str,
    receiver_model_revision: str,
    sender_model_sha256: str,
    receiver_model_sha256: str,
    sender_tokenizer_revision: str,
    receiver_tokenizer_revision: str,
) -> dict:
    """Pair two native token streams by exact UTF-8 byte overlap.

    sender_tap_data must be the result of Cognition.read_tap(sender_tap_packet),
    which verifies the stored packet, source and feature-blob digest before this
    helper is called. Model hashes still come from the caller's independently
    verified ModelRegistry manifest.

    The sender rows are selected from its add_special=true final-RMSNorm
    prefill by matching the exact add_special=false content-token sequence.
    Receiver rows come from the pinned native selected-input-embedding extractor.
    Different tokenizers are supported; positional zip/alignment is forbidden.
    """
    source_id = _required_id(source_id, "source_id")
    session_id = _required_id(session_id, "session_id")
    event_id = _required_id(event_id, "event_id")
    brain_generation_id = _required_id(brain_generation_id, "brain_generation_id")
    if sender_role not in _SENDER_ROLES or receiver_role not in _RECEIVER_TAPS or sender_role == receiver_role:
        raise LatentAdapterError("native tokenwise pairing requires distinct B1/B2 sender and B1/B2/C3 receiver roles")
    for name, value in (("sender_tap_id", sender_tap_id),
                        ("sender_model_revision", sender_model_revision),
                        ("receiver_model_revision", receiver_model_revision),
                        ("sender_tokenizer_revision", sender_tokenizer_revision),
                        ("receiver_tokenizer_revision", receiver_tokenizer_revision)):
        if type(value) is not str or not value or len(value) > 160:
            raise LatentAdapterError(name + " is required and bounded")
    expected_receiver_tap = _RECEIVER_TAPS[receiver_role]
    if receiver_tap_id != expected_receiver_tap:
        raise LatentAdapterError("receiver tap ID is not the role's native input-embedding space")
    sender_model_sha256 = _sha256(sender_model_sha256, "sender_model_sha256")
    receiver_model_sha256 = _sha256(receiver_model_sha256, "receiver_model_sha256")

    if not isinstance(source_ref, Mapping):
        raise LatentAdapterError("full source reference is required")
    ref_source_id = source_ref.get("source_id")
    ref_sha256 = _sha256(source_ref.get("sha256"), "source_ref.sha256")
    char_start, char_end = source_ref.get("char_start"), source_ref.get("char_end")
    if (ref_source_id != source_id or type(char_start) is not int or type(char_end) is not int
            or char_start != 0 or type(source_text) is not str or not source_text
            or char_end != len(source_text)):
        raise LatentAdapterError("source reference must identify the exact full tapped text")

    if not isinstance(sender_tap_packet, Mapping) or not isinstance(sender_tap_data, Mapping):
        raise LatentAdapterError("validated sender LatentTapPacket and tap data are required")
    if set(sender_tap_data) != {"token_ids", "vectors"}:
        raise LatentAdapterError("sender tap data must be the exact Cognition.read_tap result")
    sender_prefill_token_ids = sender_tap_data.get("token_ids")
    sender_prefill_activation_rows = sender_tap_data.get("vectors")
    if (not isinstance(sender_prefill_token_ids, (list, tuple))
            or not isinstance(sender_prefill_activation_rows, (list, tuple))):
        raise LatentAdapterError("sender tap data lacks native token IDs or activation rows")
    sender_metrics = sender_tap_packet.get("metrics")
    if (sender_tap_packet.get("role") != sender_role
            or sender_tap_packet.get("event_id") != event_id
            or sender_tap_packet.get("brain_generation_id") != brain_generation_id
            or sender_tap_packet.get("source_ref") != dict(source_ref)
            or sender_tap_packet.get("tap_id") != sender_tap_id
            or sender_tap_packet.get("model_revision") != sender_model_revision
            or sender_tap_packet.get("token_ids") != sender_prefill_token_ids
            or sender_tap_packet.get("role_state") != "INDEPENDENT_READ_ONLY_PREFILL"
            or sender_tap_packet.get("receiver_read_authority") != 0
            or sender_tap_packet.get("receiver_injection_authority") != 0
            or sender_tap_packet.get("body_learning_authority") != 0
            or not isinstance(sender_tap_packet.get("feature_path"), str)
            or not sender_tap_packet.get("feature_path", "").startswith("data/blobs/")
            or not isinstance(sender_tap_packet.get("feature_sha256"), str)
            or len(sender_tap_packet.get("feature_sha256", "")) != 64
            or any(ch not in "0123456789abcdef" for ch in sender_tap_packet.get("feature_sha256", ""))
            or not isinstance(sender_metrics, Mapping)
            or sender_metrics.get("whole_sequence_prefill") is not True
            or sender_metrics.get("pooling") != "none"
            or sender_metrics.get("prompt_tokens") != len(sender_prefill_token_ids)
            or len(sender_prefill_activation_rows) != len(sender_prefill_token_ids)
            or sender_tap_packet.get("shape") != [
                len(sender_prefill_activation_rows),
                len(sender_prefill_activation_rows[0]) if sender_prefill_activation_rows else 0,
            ]):
        raise LatentAdapterError("sender LatentTapPacket is not the exact read-only whole-sequence prefill")

    sender_tap = build_tokenwise_tap_manifest(
        source_text,
        sender_content_token_ids,
        sender_content_token_pieces,
        sender_prefill_token_ids,
        sender_prefill_activation_rows,
    )
    receiver_tap = build_native_input_embedding_tap_manifest_from_extractor_output(
        receiver_role,
        source_text,
        receiver_content_token_ids,
        receiver_content_token_pieces,
        receiver_extractor_output,
        source_id=source_id,
        event_id=event_id,
        brain_generation_id=brain_generation_id,
        model_revision=receiver_model_revision,
        model_sha256=receiver_model_sha256,
        tokenizer_revision=receiver_tokenizer_revision,
    )
    receiver_manifest = receiver_tap["manifest"]
    if (sender_tap.get("source_sha256") != ref_sha256
            or receiver_manifest.get("source_sha256") != ref_sha256
            or sender_tap.get("source_length") != receiver_manifest.get("source_length")):
        raise LatentAdapterError("sender, receiver and SourceRef do not bind the same exact source bytes")
    if (receiver_manifest.get("source_id") != source_id
            or receiver_manifest.get("event_id") != event_id
            or receiver_manifest.get("brain_generation_id") != brain_generation_id
            or receiver_manifest.get("role") != receiver_role
            or receiver_manifest.get("tap_id") != expected_receiver_tap
            or receiver_manifest.get("model_revision") != receiver_model_revision
            or receiver_manifest.get("model_sha256") != receiver_model_sha256
            or receiver_manifest.get("tokenizer_revision") != receiver_tokenizer_revision):
        raise LatentAdapterError("receiver input tap manifest binding differs from the requested runtime identity")

    pairs = align_token_rows_by_byte_pieces(
        sender_tap["vectors"], sender_content_token_pieces,
        receiver_tap["vectors"], receiver_content_token_pieces,
        source_id=source_id,
        source_text=source_text,
    )
    if (len(pairs) != len(receiver_content_token_ids)
            or not pairs
            or any(pair.get("source_id") != source_id or pair.get("source_sha256") != ref_sha256
                   for pair in pairs)):
        raise LatentAdapterError("aligned native token pairs do not preserve receiver row count/source")
    coverages = [pair.get("alignment_coverage") for pair in pairs]
    if any(type(value) not in (int, float) or not math.isfinite(float(value))
            or not 0.80 <= float(value) <= 1.0 for value in coverages):
        raise LatentAdapterError("native token pair coverage is outside the accepted byte-overlap range")

    sender_meta = {
        "role": sender_role,
        "tap_id": sender_tap_id,
        "model_revision": sender_model_revision,
        "model_sha256": sender_model_sha256,
        "tokenizer_revision": sender_tokenizer_revision,
        "token_ids": list(sender_tap["token_ids"]),
        "token_spans": [list(span) for span in sender_tap["token_spans"]],
        "prefill_positions": list(sender_tap["prefill_positions"]),
        "special_prefix_tokens": sender_tap["special_prefix_tokens"],
        "special_suffix_tokens": sender_tap["special_suffix_tokens"],
    }
    receiver_meta = {
        "role": receiver_role,
        "tap_id": expected_receiver_tap,
        "model_revision": receiver_model_revision,
        "model_sha256": receiver_model_sha256,
        "tokenizer_revision": receiver_tokenizer_revision,
        "token_ids": list(receiver_manifest["token_ids"]),
        "token_spans": [list(span) for span in receiver_manifest["token_spans"]],
        "embedding_dim": receiver_manifest["embedding_dim"],
        "row_sha256": list(receiver_manifest["row_sha256"]),
        "extractor_receipt": dict(receiver_manifest["extractor_receipt"]),
        "manifest_sha256": receiver_manifest["manifest_sha256"],
    }
    ref_meta = {
        "source_id": source_id,
        "sha256": ref_sha256,
        "char_start": char_start,
        "char_end": char_end,
    }
    material = {
        "schema": SCHEMA,
        "status": "PAIRED_DIAGNOSTIC",
        "source_ref": ref_meta,
        "session_id": session_id,
        "event_id": event_id,
        "brain_generation_id": brain_generation_id,
        "sender": sender_meta,
        "receiver": receiver_meta,
        "alignment_method": "UTF8_BYTE_PIECE_OVERLAP_V1",
        "pair_ids": [pair["pair_id"] for pair in pairs],
        "alignment_coverage": [float(value) for value in coverages],
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "persisted": False,
    }
    return material | {
        "pairs": pairs,
        "pair_count": len(pairs),
        "minimum_coverage": min(float(value) for value in coverages),
        "mean_coverage": sum(float(value) for value in coverages) / len(coverages),
        "record_sha256": _record_digest(material),
    }
