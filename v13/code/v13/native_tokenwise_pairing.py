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
    _require_exact_span_partition,
    _validate_span_sequence,
    _validate_tokenwise_pairs,
    align_token_rows_by_byte_pieces,
    build_tokenwise_tap_manifest,
    fit_adapter,
    project_rows,
)
from .native_input_embedding_tap import (
    _manifest_digest,
    _validate_extractor_receipt,
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
_RECORD_MATERIAL_FIELDS = (
    "schema", "status", "source_ref", "session_id", "event_id", "brain_generation_id",
    "sender", "receiver", "alignment_method", "pair_ids", "alignment_coverage",
    "production_route", "semantic_use_proven", "training_authority",
    "native_receiver_authority", "persisted",
)


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
    for pair in pairs:
        pair["session_id"] = session_id

    sender_meta = {
        "role": sender_role,
        "tap_id": sender_tap_id,
        "model_revision": sender_model_revision,
        "model_sha256": sender_model_sha256,
        "tokenizer_revision": sender_tokenizer_revision,
        "feature_sha256": sender_tap_packet["feature_sha256"],
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



def _validate_receiver_manifest_binding(record: Mapping, pairs: list[Mapping]) -> dict:
    """Bind every aligned receiver vector back to the native extractor manifest."""
    receiver = record.get("receiver")
    source_ref = record.get("source_ref")
    if not isinstance(receiver, Mapping) or not isinstance(source_ref, Mapping):
        raise LatentAdapterError("native pair record lacks receiver manifest/source binding")
    expected_fields = {
        "role", "tap_id", "model_revision", "model_sha256", "tokenizer_revision",
        "token_ids", "token_spans", "embedding_dim", "row_sha256",
        "extractor_receipt", "manifest_sha256",
    }
    if set(receiver) != expected_fields:
        raise LatentAdapterError("native receiver manifest field set is not canonical")
    role = receiver.get("role")
    if role not in _RECEIVER_TAPS or receiver.get("tap_id") != _RECEIVER_TAPS[role]:
        raise LatentAdapterError("native receiver manifest role/tap binding differs")
    token_ids = receiver.get("token_ids")
    token_spans = receiver.get("token_spans")
    row_hashes = receiver.get("row_sha256")
    pair_count = len(pairs)
    if (not isinstance(token_ids, list) or len(token_ids) != pair_count
            or any(type(token_id) is not int or token_id < 0 for token_id in token_ids)
            or not isinstance(token_spans, list) or len(token_spans) != pair_count
            or not isinstance(row_hashes, list) or len(row_hashes) != pair_count):
        raise LatentAdapterError("native receiver manifest row count differs from tokenwise pairs")
    dimension = receiver.get("embedding_dim")
    if type(dimension) is not int or not 1 <= dimension <= 8192:
        raise LatentAdapterError("native receiver manifest embedding dimension is invalid")
    if any(type(value) is not str or len(value) != 64
           or any(ch not in "0123456789abcdef" for ch in value) for value in row_hashes):
        raise LatentAdapterError("native receiver manifest row digest is invalid")
    source_length = pairs[0].get("source_length") if pairs else None
    if (type(source_length) is not int or not 1 <= source_length <= 1_048_576
            or any(pair.get("source_length") != source_length for pair in pairs)):
        raise LatentAdapterError("native receiver manifest source length differs from aligned pairs")
    spans = _validate_span_sequence(token_spans, "receiver.token_spans")
    _require_exact_span_partition(spans, source_length, "receiver")
    if record.get("alignment_method") != "UTF8_BYTE_PIECE_OVERLAP_V1":
        raise LatentAdapterError("native receiver manifest requires exact UTF-8 byte-piece alignment")
    receipt = _validate_extractor_receipt(
        receiver.get("extractor_receipt"),
        list(token_ids),
        dimension,
        receiver.get("model_revision"),
        receiver.get("model_sha256"),
    )
    if dict(receipt) != dict(receiver.get("extractor_receipt", {})):
        raise LatentAdapterError("native receiver extractor receipt is not canonical")
    material = {
        "schema": "v14.native-input-embedding-tap/2",
        "role": role,
        "tap_id": receiver["tap_id"],
        "activation_space": "INPUT_EMBEDDING_F32",
        "source_span_unit": "UTF8_BYTE",
        "source_id": source_ref.get("source_id"),
        "source_sha256": source_ref.get("sha256"),
        "source_length": source_length,
        "event_id": record.get("event_id"),
        "brain_generation_id": record.get("brain_generation_id"),
        "model_revision": receiver["model_revision"],
        "model_sha256": receiver["model_sha256"],
        "tokenizer_revision": receiver["tokenizer_revision"],
        "token_ids": list(token_ids),
        "token_spans": [list(span) for span in spans],
        "row_positions": list(range(pair_count)),
        "embedding_dim": dimension,
        "row_sha256": list(row_hashes),
        "extractor_receipt": dict(receipt),
    }
    if _manifest_digest(material) != receiver.get("manifest_sha256"):
        raise LatentAdapterError("native receiver manifest digest mismatch")
    alignment_method = _validate_tokenwise_pairs(pairs, "native pair record")
    if alignment_method != record.get("alignment_method"):
        raise LatentAdapterError("native receiver manifest alignment method differs")
    ordered = sorted(pairs, key=lambda item: item["token_position"])
    if [item["token_position"] for item in ordered] != list(range(pair_count)):
        raise LatentAdapterError("native receiver rows are not in contiguous tokenizer order")
    for index, pair in enumerate(ordered):
        if (pair.get("source_span") != list(spans[index])
                or pair.get("source_span_unit") != "UTF8_BYTE"
                or pair.get("receiver_vector_sha256") != row_hashes[index]
                or len(pair.get("receiver_vector", ())) != dimension):
            raise LatentAdapterError("aligned receiver vector differs from its native manifest row")
    return dict(receiver)


def _validate_native_pair_record(record: Mapping) -> dict:
    """Verify the exact in-memory pair-record envelope before fitting."""
    expected_fields = set(_RECORD_MATERIAL_FIELDS) | {
        "pairs", "pair_count", "minimum_coverage", "mean_coverage", "record_sha256",
    }
    if not isinstance(record, Mapping) or set(record) != expected_fields:
        raise LatentAdapterError("native tokenwise pair record has an unexpected field set")
    material = {key: record[key] for key in _RECORD_MATERIAL_FIELDS}
    if record.get("schema") != SCHEMA or record.get("status") != "PAIRED_DIAGNOSTIC":
        raise LatentAdapterError("native tokenwise pair record schema/status is unsupported")
    if (record.get("production_route") is not False
            or record.get("semantic_use_proven") is not False
            or record.get("training_authority") != 0
            or record.get("native_receiver_authority") != 0
            or record.get("persisted") is not False):
        raise LatentAdapterError("native tokenwise pair record carries forbidden authority or persistence")
    source_ref = record.get("source_ref")
    if not isinstance(source_ref, Mapping):
        raise LatentAdapterError("native tokenwise pair record lacks SourceRef")
    source_id = _required_id(source_ref.get("source_id"), "source_ref.source_id")
    source_sha = _sha256(source_ref.get("sha256"), "source_ref.sha256")
    if (type(source_ref.get("char_start")) is not int or source_ref["char_start"] != 0
            or type(source_ref.get("char_end")) is not int or not 1 <= source_ref["char_end"] <= 1_048_576):
        raise LatentAdapterError("native tokenwise pair record SourceRef range is invalid")
    session_id = _required_id(record.get("session_id"), "session_id")
    _required_id(record.get("event_id"), "event_id")
    _required_id(record.get("brain_generation_id"), "brain_generation_id")
    if not isinstance(record.get("sender"), Mapping) or not isinstance(record.get("receiver"), Mapping):
        raise LatentAdapterError("native tokenwise pair record model bindings are missing")
    pairs = record.get("pairs")
    pair_ids = record.get("pair_ids")
    coverages = record.get("alignment_coverage")
    if (not isinstance(pairs, list) or not pairs or any(not isinstance(item, Mapping) for item in pairs)
            or type(record.get("pair_count")) is not int or record["pair_count"] != len(pairs)
            or not isinstance(pair_ids, list) or any(type(item) is not str or not item for item in pair_ids)
            or pair_ids != [item.get("pair_id") for item in pairs]
            or len(set(pair_ids)) != len(pair_ids)
            or not isinstance(coverages, list) or len(coverages) != len(pairs)):
        raise LatentAdapterError("native tokenwise pair record row manifest is inconsistent")
    _validate_receiver_manifest_binding(record, pairs)
    for pair, coverage in zip(pairs, coverages):
        pair_coverage = pair.get("alignment_coverage")
        if (pair.get("source_id") != source_id
                or pair.get("source_sha256") != source_sha
                or pair.get("session_id") != session_id
                or pair.get("alignment_method") != record.get("alignment_method")
                or type(coverage) not in (int, float) or not math.isfinite(float(coverage))
                or type(pair_coverage) not in (int, float) or not math.isfinite(float(pair_coverage))
                or abs(float(pair_coverage) - float(coverage)) > 1e-12):
            raise LatentAdapterError("native tokenwise pair row differs from its source/session record")
    minimum, mean = record.get("minimum_coverage"), record.get("mean_coverage")
    if (type(minimum) not in (int, float) or not math.isfinite(float(minimum))
            or type(mean) not in (int, float) or not math.isfinite(float(mean))
            or abs(float(minimum) - min(float(v) for v in coverages)) > 1e-12
            or abs(float(mean) - sum(float(v) for v in coverages) / len(coverages)) > 1e-12):
        raise LatentAdapterError("native tokenwise pair coverage summary is inconsistent")
    _sha256(record.get("record_sha256"), "record_sha256")
    if _record_digest(material) != record["record_sha256"]:
        raise LatentAdapterError("native tokenwise pair record digest mismatch")
    return dict(record)


def fit_adapter_from_native_pair_records(
    records,
    *,
    train_session_ids,
    holdout_session_ids,
    rank: int = 16,
    ridge: float = 1e-4,
    min_relative_improvement: float = 0.02,
    seed: int = 7,
) -> dict:
    """Fit a TOKENWISE alignment candidate from source-bound native pair records.

    The split is declared by whole session IDs; source IDs and source hashes
    must also be disjoint. The result is an offline PCA+ridge alignment
    candidate only. It does not persist vectors, run receiver inference,
    change model weights, or prove semantic/task utility.
    """
    if not isinstance(records, (list, tuple)) or not 1 <= len(records) <= 1024:
        raise LatentAdapterError("native pair records must be a bounded non-empty sequence")

    def session_set(values, name):
        if not isinstance(values, (list, tuple)) or len(values) < 2:
            raise LatentAdapterError(name + " requires at least two session IDs")
        normalized = [_required_id(value, name) for value in values]
        if len(set(normalized)) != len(normalized):
            raise LatentAdapterError(name + " contains duplicate session IDs")
        return set(normalized)

    train_sessions = session_set(train_session_ids, "train_session_ids")
    holdout_sessions = session_set(holdout_session_ids, "holdout_session_ids")
    if train_sessions & holdout_sessions:
        raise LatentAdapterError("session leakage: train and holdout session IDs overlap")

    checked = [_validate_native_pair_record(record) for record in records]
    observed_sessions = {record["session_id"] for record in checked}
    if observed_sessions != train_sessions | holdout_sessions:
        raise LatentAdapterError("pair records do not exactly cover the declared train/holdout sessions")

    source_ids, source_hashes = set(), set()
    first = checked[0]
    sender, receiver = first["sender"], first["receiver"]
    binding_fields = ("role", "tap_id", "model_revision", "model_sha256", "tokenizer_revision")
    for record in checked:
        source_id = record["source_ref"]["source_id"]
        source_sha = record["source_ref"]["sha256"]
        if source_id in source_ids or source_sha in source_hashes:
            raise LatentAdapterError("native pair cohort repeats a source ID or source hash")
        source_ids.add(source_id)
        source_hashes.add(source_sha)
        if record["alignment_method"] != first["alignment_method"]:
            raise LatentAdapterError("native pair cohort mixes token alignment methods")
        for side, expected in (("sender", sender), ("receiver", receiver)):
            actual = record[side]
            if any(actual.get(field) != expected.get(field) for field in binding_fields):
                raise LatentAdapterError("native pair cohort mixes model, role, tap or tokenizer bindings")

    train_records = [record for record in checked if record["session_id"] in train_sessions]
    holdout_records = [record for record in checked if record["session_id"] in holdout_sessions]
    train_pairs = [pair for record in train_records for pair in record["pairs"]]
    holdout_pairs = [pair for record in holdout_records for pair in record["pairs"]]
    adapter = fit_adapter(
        train_pairs, holdout_pairs,
        sender_role=sender["role"],
        receiver_role=receiver["role"],
        sender_tap_id=sender["tap_id"],
        receiver_tap_id=receiver["tap_id"],
        sender_model_revision=sender["model_revision"],
        receiver_model_revision=receiver["model_revision"],
        sender_model_sha256=sender["model_sha256"],
        receiver_model_sha256=receiver["model_sha256"],
        sender_tokenizer_revision=sender["tokenizer_revision"],
        receiver_tokenizer_revision=receiver["tokenizer_revision"],
        rank=rank,
        ridge=ridge,
        min_relative_improvement=min_relative_improvement,
        seed=seed,
        projection_scope="TOKENWISE",
    )
    manifest_material = {
        "schema": "v14.native-tokenwise-adapter-fit/1",
        "record_sha256s": sorted(record["record_sha256"] for record in checked),
        "train_session_ids": sorted(train_sessions),
        "holdout_session_ids": sorted(holdout_sessions),
    }
    fit_manifest_material = manifest_material | {
        "status": adapter["status"],
        "train_record_count": len(train_records),
        "holdout_record_count": len(holdout_records),
        "train_source_count": len({record["source_ref"]["source_id"] for record in train_records}),
        "holdout_source_count": len({record["source_ref"]["source_id"] for record in holdout_records}),
        "train_pair_count": len(train_pairs),
        "holdout_pair_count": len(holdout_pairs),
        "source_disjoint": True,
        "session_disjoint": True,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }
    fit_manifest = fit_manifest_material | {
        "manifest_sha256": _record_digest(fit_manifest_material),
    }
    return {"adapter": adapter, "fit_manifest": fit_manifest}


def build_anchor_preserving_native_receiver_input(
    adapter: Mapping,
    record: Mapping,
    *,
    residual_gain: float = 0.10,
    max_relative_residual: float = 0.25,
) -> dict:
    """Build a bounded tokenwise receiver input while keeping exact receiver rows as anchors.

    This optional diagnostic strategy interpolates from each exact receiver
    input-embedding row toward the projected sender row. The per-row residual
    is clipped relative to the exact anchor norm before the global gain is
    applied. It is not XBridge LEB/cross-attention and does not prove semantic
    utility; the native receiver must still beat exact/no-message and negative
    controls on held-out tasks.
    """
    checked = _validate_native_pair_record(record)
    receiver = checked["receiver"]
    sender = checked["sender"]
    if type(residual_gain) not in (int, float) or not math.isfinite(float(residual_gain)) or not 0.0 <= float(residual_gain) <= 0.5:
        raise LatentAdapterError("anchor residual gain must be finite and in [0, 0.5]")
    if (type(max_relative_residual) not in (int, float)
            or not math.isfinite(float(max_relative_residual))
            or not 0.0 <= float(max_relative_residual) <= 1.0):
        raise LatentAdapterError("maximum relative residual must be finite and in [0, 1]")
    if not isinstance(adapter, Mapping) or adapter.get("projection_scope") != "TOKENWISE":
        raise LatentAdapterError("anchor-preserving receiver input requires a tokenwise adapter")
    adapter_bindings = {
        "sender_role": sender.get("role"),
        "receiver_role": receiver.get("role"),
        "sender_tap_id": sender.get("tap_id"),
        "receiver_tap_id": receiver.get("tap_id"),
        "sender_model_revision": sender.get("model_revision"),
        "receiver_model_revision": receiver.get("model_revision"),
        "sender_model_sha256": sender.get("model_sha256"),
        "receiver_model_sha256": receiver.get("model_sha256"),
        "sender_tokenizer_revision": sender.get("tokenizer_revision"),
        "receiver_tokenizer_revision": receiver.get("tokenizer_revision"),
    }
    if any(adapter.get(key) != value for key, value in adapter_bindings.items()):
        raise LatentAdapterError("anchor-preserving adapter model/tap/tokenizer binding mismatch")
    pairs = sorted(checked["pairs"], key=lambda item: item["token_position"])
    sender_vectors = [pair["sender_vector"] for pair in pairs]
    anchor_vectors = [pair["receiver_vector"] for pair in pairs]
    projected_rows = project_rows(
        adapter,
        sender_vectors,
        sender_model_sha256=sender["model_sha256"],
        receiver_model_sha256=receiver["model_sha256"],
        sender_tap_id=sender["tap_id"],
        receiver_tap_id=receiver["tap_id"],
    )
    output_rows = []
    preclip_ratios = []
    applied_ratios = []
    clipped_rows = 0
    for anchor, projected in zip(anchor_vectors, projected_rows):
        anchor_norm = math.sqrt(sum(float(value) * float(value) for value in anchor))
        if not math.isfinite(anchor_norm) or anchor_norm <= 1e-10:
            raise LatentAdapterError("native receiver anchor row has an invalid norm")
        delta = [float(p) - float(a) for a, p in zip(anchor, projected)]
        residual_norm = math.sqrt(sum(value * value for value in delta))
        relative = residual_norm / anchor_norm
        if not math.isfinite(relative):
            raise LatentAdapterError("anchor residual is non-finite")
        preclip_ratios.append(relative)
        scale = 1.0
        if relative > float(max_relative_residual):
            scale = float(max_relative_residual) / relative if relative > 0.0 else 1.0
            clipped_rows += 1
        applied_gain = float(residual_gain) * scale
        output = [float(a) + applied_gain * value for a, value in zip(anchor, delta)]
        if any(not math.isfinite(value) for value in output):
            raise LatentAdapterError("anchor-preserving receiver row is non-finite")
        applied_norm = math.sqrt(sum((value - float(a)) ** 2 for value, a in zip(output, anchor)))
        applied_ratios.append(applied_norm / anchor_norm)
        output_rows.append(output)

    from . import native_latent_receiver
    rows, dimension, _payload, input_sha256 = native_latent_receiver._vector_payload(output_rows)
    anchor_rows, anchor_dimension, _anchor_payload, anchor_sha256 = native_latent_receiver._vector_payload(anchor_vectors)
    if (rows != len(pairs) or dimension != adapter.get("receiver_dim")
            or anchor_dimension != dimension):
        raise LatentAdapterError("anchor-preserving receiver input geometry differs from the native contract")
    positions = native_latent_receiver._validate_positions(
        list(range(rows)), rows, native_latent_receiver.POSITION_MODE,
    )
    adapter_sha = adapter.get("adapter_sha256")
    if (type(adapter_sha) is not str or len(adapter_sha) != 64
            or any(ch not in "0123456789abcdef" for ch in adapter_sha)):
        raise LatentAdapterError("anchor-preserving adapter digest is missing or invalid")
    return {
        "schema": "v14.native-tokenwise-anchor-residual-input/1",
        "input_strategy": "ANCHOR_PLUS_CAPPED_RESIDUAL_V1",
        "vectors": output_rows,
        "position_ids": positions,
        "position_mode": native_latent_receiver.POSITION_MODE,
        "input_rows": rows,
        "input_dim": dimension,
        "input_sha256": input_sha256,
        "anchor_sha256": anchor_sha256,
        "tokenizer_revision": receiver["tokenizer_revision"],
        "token_count": len(receiver["token_ids"]),
        "source_ref": dict(checked["source_ref"]),
        "event_id": checked["event_id"],
        "brain_generation_id": checked["brain_generation_id"],
        "session_id": checked["session_id"],
        "record_sha256": checked["record_sha256"],
        "adapter_sha256": adapter_sha,
        "sender_role": sender["role"],
        "receiver_role": receiver["role"],
        "sender_model_revision": sender["model_revision"],
        "receiver_model_revision": receiver["model_revision"],
        "sender_model_sha256": sender["model_sha256"],
        "receiver_model_sha256": receiver["model_sha256"],
        "sender_tap_id": sender["tap_id"],
        "receiver_tap_id": receiver["tap_id"],
        "residual_gain": float(residual_gain),
        "max_relative_residual": float(max_relative_residual),
        "mean_preclip_relative_residual": sum(preclip_ratios) / len(preclip_ratios),
        "max_preclip_relative_residual": max(preclip_ratios),
        "mean_applied_relative_residual": sum(applied_ratios) / len(applied_ratios),
        "max_applied_relative_residual": max(applied_ratios),
        "clipped_rows": clipped_rows,
        "anchor_rows_preserved_as_base": True,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "persisted": False,
    }
