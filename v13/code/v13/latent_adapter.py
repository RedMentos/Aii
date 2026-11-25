"""Typed low-rank cross-organ activation adapter for B3 research.

Generic paired-vector fitting can target an explicitly declared receiver space.
The persisted B1/B2 tap fitter instead mean-pools non-position-zero final-RMSNorm
rows and therefore produces an EVENT_POOLED_NONZERO_MEAN adapter, not a tokenwise
native input-embedding adapter. Native receiver input construction requires a
separately trained TOKENWISE adapter bound to the receiver input-embedding tap.
Alignment metrics are not semantic utility; all results remain diagnostic,
non-promoted and authority-zero.
"""
from __future__ import annotations

from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
from typing import Mapping, Sequence

SCHEMA = "v14.cross-organ-latent-adapter/2"
TOKENWISE_SCHEMA = "v14.cross-organ-latent-adapter/3"
_TOKEN_ALIGNMENT_METHOD = "CHAR_SPAN_OVERLAP_V1"
_TOKEN_ALIGNMENT_BYTE_METHOD = "UTF8_BYTE_PIECE_OVERLAP_V1"
_TOKEN_ALIGNMENT_METHODS = frozenset({_TOKEN_ALIGNMENT_METHOD, _TOKEN_ALIGNMENT_BYTE_METHOD})
_TOKEN_ALIGNMENT_MIN_COVERAGE = 0.80
_MAGIC = b"V14LAT1\0"
_MAX_DIM = 8192
_MAX_RANK = 64
_MAX_PAIRS = 4096
_MAX_FILE_BYTES = 64 * 1024 * 1024
_ROLES = frozenset({"B1_DETAIL", "B2_GIST"})
_RECEIVERS = frozenset({"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"})
_PROJECTION_SCOPES = frozenset({"PAIRED_VECTOR", "EVENT_POOLED_NONZERO_MEAN", "TOKENWISE"})
_NATIVE_INPUT_TAP_IDS = {
    "B1_DETAIL": "b1.input-embedding.v1",
    "B2_GIST": "b2.input-embedding.v1",
    "C3_LANGUAGE": "c3.input-embedding.v1",
}


class LatentAdapterError(ValueError):
    pass


class LatentAdapterUnavailable(RuntimeError):
    pass


def _sha256_text(value: str, name: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower()):
        raise LatentAdapterError(name + " must be a SHA-256 hex digest")
    return value.lower()


def _finite_vector(value, name: str, expected_dim: int | None = None) -> list[float]:
    if not isinstance(value, (list, tuple)) or not value or len(value) > _MAX_DIM:
        raise LatentAdapterError(name + " has invalid vector geometry")
    if expected_dim is not None and len(value) != expected_dim:
        raise LatentAdapterError(name + " dimension mismatch")
    out = []
    for item in value:
        if type(item) not in (int, float) or not math.isfinite(float(item)):
            raise LatentAdapterError(name + " contains a non-finite or non-numeric value")
        out.append(float(item))
    return out


def _validate_pairs(pairs, name: str):
    if not isinstance(pairs, (list, tuple)) or not pairs or len(pairs) > _MAX_PAIRS:
        raise LatentAdapterError(name + " must contain a bounded non-empty pair list")
    pair_ids, source_ids, senders, receivers = set(), set(), [], []
    source_dim = receiver_dim = None
    for pair in pairs:
        if not isinstance(pair, Mapping):
            raise LatentAdapterError(name + " pair must be a mapping")
        pair_id, source_id = pair.get("pair_id"), pair.get("source_id")
        if type(pair_id) is not str or not pair_id or len(pair_id) > 128 or pair_id in pair_ids:
            raise LatentAdapterError(name + " pair IDs must be unique non-empty strings")
        if type(source_id) is not str or not source_id or len(source_id) > 128:
            raise LatentAdapterError(name + " source IDs must be non-empty strings")
        pair_ids.add(pair_id)
        source_ids.add(source_id)
        sender = _finite_vector(pair.get("sender_vector"), name + " sender_vector", source_dim)
        receiver = _finite_vector(pair.get("receiver_vector"), name + " receiver_vector", receiver_dim)
        source_dim = len(sender) if source_dim is None else source_dim
        receiver_dim = len(receiver) if receiver_dim is None else receiver_dim
        senders.append(sender)
        receivers.append(receiver)
    return pair_ids, source_ids, senders, receivers


def _validate_span_sequence(spans, name: str) -> list[tuple[int, int]]:
    if not isinstance(spans, (list, tuple)) or not 2 <= len(spans) <= 64:
        raise LatentAdapterError(name + " must contain 2..64 token spans")
    clean = []
    previous_end = -1
    for span in spans:
        if (not isinstance(span, (list, tuple)) or len(span) != 2
                or type(span[0]) is not int or type(span[1]) is not int
                or span[0] < 0 or span[1] <= span[0]):
            raise LatentAdapterError(name + " contains an invalid source span")
        start, end = span
        if start < previous_end:
            raise LatentAdapterError(name + " spans overlap or are out of order")
        clean.append((start, end))
        previous_end = end
    return clean


def _activation_vector_sha256(vector) -> str:
    """Hash one activation row using a canonical little-endian float64 encoding."""
    values = _finite_vector(vector, "activation vector")
    payload = struct.pack("<" + ("d" * len(values)), *values)
    return hashlib.sha256(b"V14-LATENT-ACTIVATION-F64LE\0" + payload).hexdigest()


def _token_pair_id(*, source_id: str, source_sha256: str, token_position: int,
                   source_span: Sequence[int], alignment_id: str, alignment_coverage: float,
                   sender_vector_sha256: str, receiver_vector_sha256: str) -> str:
    material = json.dumps({
        "source_id": source_id,
        "source_sha256": source_sha256,
        "token_position": token_position,
        "source_span": list(source_span),
        "alignment_id": alignment_id,
        "alignment_coverage": float(alignment_coverage),
        "sender_vector_sha256": sender_vector_sha256,
        "receiver_vector_sha256": receiver_vector_sha256,
    }, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(b"V14-LATENT-TOKEN-PAIR/1\0" + material).hexdigest()


def _alignment_manifest_sha256(*, method: str, source_id: str, source_sha256: str,
                               sender_spans, receiver_spans, source_span_unit: str,
                               source_length: int | None = None) -> str:
    material = {
        "method": method,
        "source_id": source_id,
        "source_sha256": source_sha256,
        "source_span_unit": source_span_unit,
        "sender_spans": [list(span) for span in sender_spans],
        "receiver_spans": [list(span) for span in receiver_spans],
    }
    if source_length is not None:
        material["source_length"] = source_length
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _span_coverage(sender_spans, receiver_span) -> float:
    start, end = receiver_span
    covered = sum(max(0, min(end, sender_end) - max(start, sender_start))
                  for sender_start, sender_end in sender_spans)
    return covered / (end - start)


def _require_exact_span_partition(spans, source_length: int, name: str) -> None:
    if (type(source_length) is not int or not 1 <= source_length <= 1_048_576
            or not spans or spans[0][0] != 0 or spans[-1][1] != source_length
            or any(left[1] != right[0] for left, right in zip(spans, spans[1:]))):
        raise LatentAdapterError(name + " byte spans must exactly partition the source")


def token_piece_byte_spans(token_pieces, source_text: str, *, expected_token_ids=None) -> dict:
    """Build exact UTF-8 byte spans from llama.cpp /tokenize with_pieces output.

    Callers must request add_special=false. The endpoint may return each piece as
    UTF-8 text or as raw byte integers when a token splits a Unicode code point.
    We reject any stream that does not reconstruct the exact tapped source bytes.
    """
    if type(source_text) is not str or not source_text:
        raise LatentAdapterError("token span source_text must be non-empty UTF-8 text")
    try:
        source_bytes = source_text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise LatentAdapterError("token span source_text is not valid UTF-8") from exc
    if len(source_bytes) > 1_048_576:
        raise LatentAdapterError("token span source exceeds the 1 MiB byte bound")
    if not isinstance(token_pieces, (list, tuple)) or not 2 <= len(token_pieces) <= 64:
        raise LatentAdapterError("token pieces must contain 2..64 entries")

    if expected_token_ids is not None:
        if (not isinstance(expected_token_ids, (list, tuple))
                or len(expected_token_ids) != len(token_pieces)
                or any(type(token_id) is not int or not 0 <= token_id <= 2_147_483_647
                       for token_id in expected_token_ids)):
            raise LatentAdapterError("expected token IDs do not match the token-piece count")
    pieces = []
    for index, token in enumerate(token_pieces):
        if expected_token_ids is not None:
            if (not isinstance(token, Mapping) or type(token.get("id")) is not int
                    or token.get("id") != expected_token_ids[index]):
                raise LatentAdapterError("llama.cpp token-piece ID differs from the native token ID")
        piece = token.get("piece") if isinstance(token, Mapping) else token
        if isinstance(piece, str):
            try:
                raw = piece.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise LatentAdapterError("token piece is not valid UTF-8 text") from exc
        elif isinstance(piece, (bytes, bytearray)):
            raw = bytes(piece)
        elif isinstance(piece, (list, tuple)):
            if any(type(value) is not int or not 0 <= value <= 255 for value in piece):
                raise LatentAdapterError("token piece byte list contains an invalid byte")
            raw = bytes(piece)
        else:
            raise LatentAdapterError("token piece must be UTF-8 text or a byte sequence")
        if not raw:
            raise LatentAdapterError("empty/special token pieces cannot be source-aligned")
        pieces.append(raw)

    if b"".join(pieces) != source_bytes:
        raise LatentAdapterError("token pieces do not reconstruct the exact source UTF-8 bytes")
    spans = []
    cursor = 0
    for piece in pieces:
        spans.append([cursor, cursor + len(piece)])
        cursor += len(piece)
    return {
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_length": len(source_bytes),
        "token_spans": spans,
    }



def build_tokenwise_tap_manifest(source_text: str, content_token_ids, content_token_pieces,
                                 prefill_token_ids, activation_rows) -> dict:
    """Bind source bytes and content-token spans to exact native prefill rows.

    The caller obtains content_token_ids/pieces with add_special=false and
    prefill_token_ids/activation_rows from the same raw source text with
    add_special=true. No chat template or extra prompt text may be inserted.
    A unique contiguous content-token subsequence is required; at most two
    unmatched special-token rows (normally BOS) are tolerated.
    """
    def token_ids(value, name, *, minimum, maximum):
        if not isinstance(value, (list, tuple)) or not minimum <= len(value) <= maximum:
            raise LatentAdapterError(name + " has an invalid token count")
        if any(type(token) is not int or not 0 <= token <= 2_147_483_647 for token in value):
            raise LatentAdapterError(name + " contains an invalid native token ID")
        return list(value)

    content_ids = token_ids(content_token_ids, "content_token_ids", minimum=2, maximum=64)
    prefill_ids = token_ids(
        prefill_token_ids, "prefill_token_ids",
        minimum=len(content_ids), maximum=len(content_ids) + 2,
    )
    piece_meta = token_piece_byte_spans(content_token_pieces, source_text, expected_token_ids=content_ids)
    if len(piece_meta["token_spans"]) != len(content_ids):
        raise LatentAdapterError("content token IDs and token pieces have different row counts")
    if not isinstance(activation_rows, (list, tuple)) or len(activation_rows) != len(prefill_ids):
        raise LatentAdapterError("prefill activation rows do not match native prefill token IDs")
    rows = [_finite_vector(row, "prefill activation row") for row in activation_rows]
    dimension = len(rows[0])
    if any(len(row) != dimension for row in rows):
        raise LatentAdapterError("prefill activation row dimensions differ")

    matches = [
        start for start in range(len(prefill_ids) - len(content_ids) + 1)
        if prefill_ids[start:start + len(content_ids)] == content_ids
    ]
    if len(matches) != 1:
        raise LatentAdapterError("content token IDs must map to exactly one contiguous prefill-row span")
    start = matches[0]
    end = start + len(content_ids)
    return {
        "schema": "v14.source-bound-tokenwise-tap/1",
        "source_sha256": piece_meta["source_sha256"],
        "source_length": piece_meta["source_length"],
        "token_ids": content_ids,
        "token_spans": piece_meta["token_spans"],
        "prefill_positions": list(range(start, end)),
        "special_prefix_tokens": start,
        "special_suffix_tokens": len(prefill_ids) - end,
        "vectors": rows[start:end],
    }


def _align_token_rows_by_spans(sender_vectors, sender_spans, receiver_vectors, receiver_spans,
                               *, source_id: str, source_sha256: str, method: str,
                               source_span_unit: str, source_length: int | None = None,
                               min_coverage: float = _TOKEN_ALIGNMENT_MIN_COVERAGE) -> list[dict]:
    if type(source_id) is not str or not source_id or len(source_id) > 128:
        raise LatentAdapterError("token alignment source_id is invalid")
    source_sha256 = _sha256_text(source_sha256, "source_sha256")
    if method not in _TOKEN_ALIGNMENT_METHODS:
        raise LatentAdapterError("unsupported token alignment method")
    expected_unit = "UTF8_BYTE" if method == _TOKEN_ALIGNMENT_BYTE_METHOD else "CHARACTER"
    if source_span_unit != expected_unit:
        raise LatentAdapterError("token alignment source-span unit does not match its method")
    if (type(min_coverage) not in (int, float) or not math.isfinite(float(min_coverage))
            or not _TOKEN_ALIGNMENT_MIN_COVERAGE <= float(min_coverage) <= 1.0):
        raise LatentAdapterError("token alignment minimum coverage must be in [0.80, 1]")
    if not isinstance(sender_vectors, (list, tuple)) or len(sender_vectors) < 2 or len(sender_vectors) > 64:
        raise LatentAdapterError("sender token rows must contain 2..64 vectors")
    if not isinstance(receiver_vectors, (list, tuple)) or len(receiver_vectors) < 2 or len(receiver_vectors) > 64:
        raise LatentAdapterError("receiver token rows must contain 2..64 vectors")
    clean_sender_spans = _validate_span_sequence(sender_spans, "sender_spans")
    clean_receiver_spans = _validate_span_sequence(receiver_spans, "receiver_spans")
    if len(sender_vectors) != len(clean_sender_spans) or len(receiver_vectors) != len(clean_receiver_spans):
        raise LatentAdapterError("token span count differs from activation row count")
    if method == _TOKEN_ALIGNMENT_BYTE_METHOD:
        _require_exact_span_partition(clean_sender_spans, source_length, "sender")
        _require_exact_span_partition(clean_receiver_spans, source_length, "receiver")
    elif source_length is not None:
        raise LatentAdapterError("character-span alignment cannot declare a UTF-8 byte source length")

    sender_rows = [_finite_vector(row, "sender token row") for row in sender_vectors]
    receiver_rows = [_finite_vector(row, "receiver token row") for row in receiver_vectors]
    sender_dim = len(sender_rows[0])
    receiver_dim = len(receiver_rows[0])
    if any(len(row) != sender_dim for row in sender_rows):
        raise LatentAdapterError("sender token row dimensions differ")
    if any(len(row) != receiver_dim for row in receiver_rows):
        raise LatentAdapterError("receiver token row dimensions differ")

    alignment_id = _alignment_manifest_sha256(
        method=method, source_id=source_id, source_sha256=source_sha256,
        sender_spans=clean_sender_spans, receiver_spans=clean_receiver_spans,
        source_span_unit=source_span_unit, source_length=source_length,
    )
    aligned = []
    for position, (start, end) in enumerate(clean_receiver_spans):
        weighted = [0.0] * sender_dim
        covered = 0
        for row, (sender_start, sender_end) in zip(sender_rows, clean_sender_spans):
            overlap = max(0, min(end, sender_end) - max(start, sender_start))
            if overlap:
                covered += overlap
                for index, value in enumerate(row):
                    weighted[index] += float(value) * overlap
        coverage = covered / (end - start)
        if covered <= 0 or coverage + 1e-12 < float(min_coverage):
            raise LatentAdapterError("sender token spans do not sufficiently cover a receiver token span")
        sender_aligned = [value / covered for value in weighted]
        receiver_vector = receiver_rows[position]
        sender_vector_sha256 = _activation_vector_sha256(sender_aligned)
        receiver_vector_sha256 = _activation_vector_sha256(receiver_vector)
        pair_id = _token_pair_id(
            source_id=source_id,
            source_sha256=source_sha256,
            token_position=position,
            source_span=(start, end),
            alignment_id=alignment_id,
            alignment_coverage=coverage,
            sender_vector_sha256=sender_vector_sha256,
            receiver_vector_sha256=receiver_vector_sha256,
        )
        aligned.append({
            "pair_id": pair_id,
            "source_id": source_id,
            "source_sha256": source_sha256,
            "source_span_unit": source_span_unit,
            "source_length": source_length,
            "sender_spans": [list(span) for span in clean_sender_spans],
            "sender_vector": sender_aligned,
            "receiver_vector": receiver_vector,
            "sender_vector_sha256": sender_vector_sha256,
            "receiver_vector_sha256": receiver_vector_sha256,
            "token_position": position,
            "source_span": [start, end],
            "alignment_method": method,
            "alignment_id": alignment_id,
            "alignment_coverage": coverage,
        })
    return aligned


def align_token_rows_by_char_span(sender_vectors, sender_spans, receiver_vectors, receiver_spans,
                                  *, source_id: str, source_sha256: str,
                                  min_coverage: float = _TOKEN_ALIGNMENT_MIN_COVERAGE) -> list[dict]:
    """Align tokenizer rows by exact source-character overlap, not token index.

    This remains a geometric diagnostic. It cannot establish semantic transfer.
    """
    return _align_token_rows_by_spans(
        sender_vectors, sender_spans, receiver_vectors, receiver_spans,
        source_id=source_id, source_sha256=source_sha256,
        method=_TOKEN_ALIGNMENT_METHOD, source_span_unit="CHARACTER",
        min_coverage=min_coverage,
    )


def align_token_rows_by_byte_pieces(sender_vectors, sender_token_pieces,
                                    receiver_vectors, receiver_token_pieces, *,
                                    source_id: str, source_text: str,
                                    min_coverage: float = _TOKEN_ALIGNMENT_MIN_COVERAGE) -> list[dict]:
    """Align rows using exact UTF-8 byte pieces from native tokenizer responses.

    The sender and receiver token-piece streams must each reconstruct the same
    source bytes exactly. This handles byte-fallback tokens that split a single
    Unicode code point, which character offsets cannot represent.
    """
    sender_meta = token_piece_byte_spans(sender_token_pieces, source_text)
    receiver_meta = token_piece_byte_spans(receiver_token_pieces, source_text)
    if (sender_meta["source_sha256"] != receiver_meta["source_sha256"]
            or sender_meta["source_length"] != receiver_meta["source_length"]):
        raise LatentAdapterError("sender/receiver token pieces refer to different source bytes")
    return _align_token_rows_by_spans(
        sender_vectors, sender_meta["token_spans"], receiver_vectors, receiver_meta["token_spans"],
        source_id=source_id, source_sha256=sender_meta["source_sha256"],
        method=_TOKEN_ALIGNMENT_BYTE_METHOD, source_span_unit="UTF8_BYTE",
        source_length=sender_meta["source_length"], min_coverage=min_coverage,
    )


def _validate_tokenwise_pairs(pairs: Sequence[Mapping], name: str) -> str:
    """Verify the full source-span manifest, not merely caller-supplied hashes."""
    by_source: dict[str, list[Mapping]] = {}
    for pair in pairs:
        source_id = pair["source_id"]
        position = pair.get("token_position")
        if type(position) is not int or not 0 <= position < 64:
            raise LatentAdapterError(name + " tokenwise pairs require bounded token_position metadata")
        span = pair.get("source_span")
        if (not isinstance(span, (list, tuple)) or len(span) != 2
                or type(span[0]) is not int or type(span[1]) is not int
                or span[0] < 0 or span[1] <= span[0]):
            raise LatentAdapterError(name + " tokenwise pairs require source_span alignment metadata")
        method = pair.get("alignment_method")
        if method not in _TOKEN_ALIGNMENT_METHODS:
            raise LatentAdapterError(name + " tokenwise pairs require a supported source-span alignment")
        expected_unit = "UTF8_BYTE" if method == _TOKEN_ALIGNMENT_BYTE_METHOD else "CHARACTER"
        if pair.get("source_span_unit") != expected_unit:
            raise LatentAdapterError(name + " tokenwise pairs have a mismatched source-span unit")
        source_sha256 = pair.get("source_sha256")
        try:
            _sha256_text(source_sha256, name + " source_sha256")
        except LatentAdapterError as exc:
            raise LatentAdapterError(name + " tokenwise pairs require a valid source_sha256") from exc
        alignment_id = pair.get("alignment_id")
        if (type(alignment_id) is not str or len(alignment_id) != 64
                or any(ch not in "0123456789abcdef" for ch in alignment_id)):
            raise LatentAdapterError(name + " tokenwise pairs require a valid alignment_id")
        sender_spans = pair.get("sender_spans")
        try:
            _validate_span_sequence(sender_spans, name + " sender_spans")
        except LatentAdapterError as exc:
            raise LatentAdapterError(name + " tokenwise pairs require a complete sender-span manifest") from exc
        source_length = pair.get("source_length")
        if method == _TOKEN_ALIGNMENT_BYTE_METHOD:
            if type(source_length) is not int or not 1 <= source_length <= 1_048_576:
                raise LatentAdapterError(name + " byte-span pairs require a bounded source_length")
        elif source_length is not None:
            raise LatentAdapterError(name + " character-span pairs cannot declare source_length")
        coverage = pair.get("alignment_coverage")
        if (type(coverage) not in (int, float) or not math.isfinite(float(coverage))
                or not _TOKEN_ALIGNMENT_MIN_COVERAGE <= float(coverage) <= 1.0):
            raise LatentAdapterError(name + " tokenwise alignment coverage is below the acceptance floor")
        by_source.setdefault(source_id, []).append(pair)

    methods = set()
    for source_id, source_pairs in by_source.items():
        ordered = sorted(source_pairs, key=lambda item: item["token_position"])
        positions = [item["token_position"] for item in ordered]
        if len(set(positions)) != len(positions):
            raise LatentAdapterError(name + " contains a duplicate token position for one source")
        if len(positions) < 2 or positions != list(range(len(positions))):
            raise LatentAdapterError(name + " token positions must contain at least two contiguous rows from zero")
        first = ordered[0]
        method = first["alignment_method"]
        source_sha256 = first["source_sha256"]
        sender_spans = _validate_span_sequence(first["sender_spans"], name + " sender_spans")
        receiver_spans = _validate_span_sequence(
            [item["source_span"] for item in ordered], name + " receiver_spans",
        )
        source_length = first.get("source_length")
        source_span_unit = first["source_span_unit"]
        for item in ordered:
            if (item["alignment_method"] != method or item["source_sha256"] != source_sha256
                    or item.get("alignment_id") != first["alignment_id"]
                    or item.get("sender_spans") != first["sender_spans"]
                    or item.get("source_length") != source_length
                    or item.get("source_span_unit") != source_span_unit):
                raise LatentAdapterError(name + " tokenwise alignment manifest differs within source")
        if method == _TOKEN_ALIGNMENT_BYTE_METHOD:
            _require_exact_span_partition(sender_spans, source_length, "sender")
            _require_exact_span_partition(receiver_spans, source_length, "receiver")
        expected_alignment_id = _alignment_manifest_sha256(
            method=method, source_id=source_id, source_sha256=source_sha256,
            sender_spans=sender_spans, receiver_spans=receiver_spans,
            source_span_unit=source_span_unit, source_length=source_length,
        )
        if first["alignment_id"] != expected_alignment_id:
            raise LatentAdapterError(name + " tokenwise alignment manifest digest mismatch")
        for item in ordered:
            expected_coverage = _span_coverage(sender_spans, item["source_span"])
            if abs(expected_coverage - float(item["alignment_coverage"])) > 1e-12:
                raise LatentAdapterError(name + " tokenwise alignment coverage mismatch")
            methods.add(item["alignment_method"])

    # Structural and manifest failures are reported before activation digests.
    for source_pairs in by_source.values():
        for item in source_pairs:
            sender_digest = _activation_vector_sha256(item["sender_vector"])
            receiver_digest = _activation_vector_sha256(item["receiver_vector"])
            if (item.get("sender_vector_sha256") != sender_digest
                    or item.get("receiver_vector_sha256") != receiver_digest):
                raise LatentAdapterError(name + " activation vector digest mismatch")
            expected_pair_id = _token_pair_id(
                source_id=item["source_id"],
                source_sha256=item["source_sha256"],
                token_position=item["token_position"],
                source_span=item["source_span"],
                alignment_id=item["alignment_id"],
                alignment_coverage=item["alignment_coverage"],
                sender_vector_sha256=sender_digest,
                receiver_vector_sha256=receiver_digest,
            )
            if item.get("pair_id") != expected_pair_id:
                raise LatentAdapterError(name + " pair ID does not bind activation rows and source span")
    if len(methods) != 1:
        raise LatentAdapterError(name + " tokenwise alignment methods are inconsistent")
    return next(iter(methods))


def _token_alignment_digest(pairs: Sequence[Mapping], *, method: str,
                            sender_tokenizer_revision: str, receiver_tokenizer_revision: str) -> str:
    rows = sorted((
        pair["pair_id"], pair["source_id"], pair["source_sha256"], pair["token_position"],
        list(pair["source_span"]), pair["source_span_unit"], pair.get("source_length"),
        [list(span) for span in pair["sender_spans"]], pair["alignment_id"],
        float(pair["alignment_coverage"]), pair["sender_vector_sha256"],
        pair["receiver_vector_sha256"],
    ) for pair in pairs)
    material = json.dumps({
        "method": method,
        "sender_tokenizer_revision": sender_tokenizer_revision,
        "receiver_tokenizer_revision": receiver_tokenizer_revision,
        "rows": rows,
    }, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _weight_values(adapter: Mapping) -> list[float]:
    values = list(adapter["sender_mean"]) + list(adapter["receiver_mean"])
    values.extend(value for row in adapter["sender_factor"] for value in row)
    values.extend(value for row in adapter["receiver_factor"] for value in row)
    return values


def _serialize(adapter: Mapping) -> bytes:
    values = _weight_values(adapter)
    if not values or any(type(v) not in (int, float) or not math.isfinite(float(v)) for v in values):
        raise LatentAdapterError("adapter weights are malformed")
    packed = array("f", (float(v) for v in values))
    if sys.byteorder != "little":
        packed.byteswap()
    weight_bytes = packed.tobytes()
    header = {key: adapter[key] for key in (
        "schema", "status", "sender_role", "receiver_role", "sender_tap_id", "receiver_tap_id",
        "sender_model_revision", "receiver_model_revision", "sender_model_sha256",
        "receiver_model_sha256", "sender_dim", "receiver_dim", "rank", "metrics",
        "train_pairs", "holdout_pairs", "train_source_count", "holdout_source_count",
        "training_method", "holdout_policy", "projection_scope",
        "production_route", "semantic_use_proven", "training_authority", "native_receiver_authority",
    )}
    if adapter.get("schema") == TOKENWISE_SCHEMA:
        header.update({
            "alignment_method": adapter["alignment_method"],
            "alignment_sha256": adapter["alignment_sha256"],
            "sender_tokenizer_revision": adapter["sender_tokenizer_revision"],
            "receiver_tokenizer_revision": adapter["receiver_tokenizer_revision"],
        })
    header["weight_count"] = len(values)
    header["weights_sha256"] = hashlib.sha256(weight_bytes).hexdigest()
    header_bytes = json.dumps(header, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return _MAGIC + struct.pack("<I", len(header_bytes)) + header_bytes + weight_bytes


def _validate_adapter(adapter: Mapping, *, require_candidate: bool = True) -> None:
    if not isinstance(adapter, Mapping) or adapter.get("schema") not in {SCHEMA, TOKENWISE_SCHEMA}:
        raise LatentAdapterError("unsupported latent adapter schema")
    if adapter.get("status") not in {"ALIGNMENT_CANDIDATE", "REJECTED"}:
        raise LatentAdapterError("invalid adapter status")
    if require_candidate and adapter.get("status") != "ALIGNMENT_CANDIDATE":
        raise LatentAdapterError("adapter did not pass its source-disjoint alignment gate")
    if adapter.get("sender_role") not in _ROLES or adapter.get("receiver_role") not in _RECEIVERS or adapter.get("sender_role") == adapter.get("receiver_role"):
        raise LatentAdapterError("invalid sender/receiver role binding")
    if adapter.get("projection_scope") not in _PROJECTION_SCOPES:
        raise LatentAdapterError("invalid projection scope")
    if adapter.get("projection_scope") == "TOKENWISE":
        if adapter.get("schema") != TOKENWISE_SCHEMA or adapter.get("alignment_method") not in _TOKEN_ALIGNMENT_METHODS:
            raise LatentAdapterError("tokenwise adapter requires the v3 source-span alignment contract")
        _sha256_text(adapter.get("alignment_sha256"), "alignment_sha256")
        for key in ("sender_tokenizer_revision", "receiver_tokenizer_revision"):
            if type(adapter.get(key)) is not str or not adapter[key] or len(adapter[key]) > 160:
                raise LatentAdapterError("tokenwise adapter requires " + key)
    elif adapter.get("schema") == TOKENWISE_SCHEMA:
        raise LatentAdapterError("v3 adapter must declare TOKENWISE projection scope")
    _sha256_text(adapter.get("sender_model_sha256"), "sender_model_sha256")
    _sha256_text(adapter.get("receiver_model_sha256"), "receiver_model_sha256")
    for key in ("sender_tap_id", "receiver_tap_id", "sender_model_revision", "receiver_model_revision"):
        if type(adapter.get(key)) is not str or not adapter[key] or len(adapter[key]) > 160:
            raise LatentAdapterError("invalid adapter binding: " + key)
    source_dim, receiver_dim, rank = adapter.get("sender_dim"), adapter.get("receiver_dim"), adapter.get("rank")
    if type(source_dim) is not int or type(receiver_dim) is not int or type(rank) is not int:
        raise LatentAdapterError("adapter dimensions must be integers")
    if not (1 <= source_dim <= _MAX_DIM and 1 <= receiver_dim <= _MAX_DIM and 1 <= rank <= min(_MAX_RANK, source_dim, receiver_dim)):
        raise LatentAdapterError("adapter dimensions are outside bounds")
    if len(adapter.get("sender_mean", ())) != source_dim or len(adapter.get("receiver_mean", ())) != receiver_dim:
        raise LatentAdapterError("adapter mean dimensions do not match metadata")
    if len(adapter.get("sender_factor", ())) != source_dim or any(len(row) != rank for row in adapter["sender_factor"]):
        raise LatentAdapterError("sender factor dimensions do not match metadata")
    if len(adapter.get("receiver_factor", ())) != rank or any(len(row) != receiver_dim for row in adapter["receiver_factor"]):
        raise LatentAdapterError("receiver factor dimensions do not match metadata")
    if (adapter.get("production_route") is not False or adapter.get("semantic_use_proven") is not False
            or adapter.get("training_authority") != 0 or adapter.get("native_receiver_authority") != 0):
        raise LatentAdapterError("latent adapter cannot grant production or learning authority")
    digest = hashlib.sha256(_serialize(adapter)).hexdigest()
    if adapter.get("adapter_sha256") is not None and adapter["adapter_sha256"] != digest:
        raise LatentAdapterError("adapter checkpoint digest mismatch")


def fit_adapter(train_pairs: Sequence[Mapping], holdout_pairs: Sequence[Mapping], *,
                sender_role: str, receiver_role: str, sender_tap_id: str, receiver_tap_id: str,
                sender_model_revision: str, receiver_model_revision: str,
                sender_model_sha256: str, receiver_model_sha256: str,
                rank: int = 16, ridge: float = 1e-4,
                min_relative_improvement: float = 0.02, seed: int = 7,
                projection_scope: str = "PAIRED_VECTOR",
                sender_tokenizer_revision: str | None = None,
                receiver_tokenizer_revision: str | None = None) -> dict:
    """Fit a low-rank affine map on paired activations with source-disjoint holdout.

    This is an alignment candidate only. The held-out MSE and shuffled control
    are necessary diagnostics, not semantic/task-utility evidence.
    """
    if sender_role not in _ROLES or receiver_role not in _RECEIVERS or sender_role == receiver_role:
        raise LatentAdapterError("unsupported or identical sender/receiver roles")
    for key, value in (("sender_tap_id", sender_tap_id), ("receiver_tap_id", receiver_tap_id),
                       ("sender_model_revision", sender_model_revision), ("receiver_model_revision", receiver_model_revision)):
        if type(value) is not str or not value or len(value) > 160:
            raise LatentAdapterError("invalid adapter binding: " + key)
    sender_model_sha256 = _sha256_text(sender_model_sha256, "sender_model_sha256")
    receiver_model_sha256 = _sha256_text(receiver_model_sha256, "receiver_model_sha256")
    if type(rank) is not int or not 1 <= rank <= _MAX_RANK:
        raise LatentAdapterError("rank must be between 1 and 64")
    if type(ridge) not in (int, float) or not math.isfinite(float(ridge)) or not 0.0 < float(ridge) <= 1.0:
        raise LatentAdapterError("ridge must be finite and in (0, 1]")
    if type(min_relative_improvement) not in (int, float) or not math.isfinite(float(min_relative_improvement)) or not 0.0 <= float(min_relative_improvement) < 1.0:
        raise LatentAdapterError("invalid minimum holdout improvement")
    if type(seed) is not int:
        raise LatentAdapterError("seed must be an integer")
    if projection_scope not in _PROJECTION_SCOPES:
        raise LatentAdapterError("unsupported projection scope")
    train_ids, train_sources, x_train, y_train = _validate_pairs(train_pairs, "train_pairs")
    holdout_ids, holdout_sources, x_holdout, y_holdout = _validate_pairs(holdout_pairs, "holdout_pairs")
    if train_ids & holdout_ids:
        raise LatentAdapterError("paired activation IDs cross train/holdout")
    if train_sources & holdout_sources:
        raise LatentAdapterError("source leakage: a source appears in train and holdout")
    alignment_method = "NONE"
    alignment_sha256 = None
    if projection_scope == "TOKENWISE":
        train_method = _validate_tokenwise_pairs(train_pairs, "train_pairs")
        holdout_method = _validate_tokenwise_pairs(holdout_pairs, "holdout_pairs")
        if train_method != holdout_method:
            raise LatentAdapterError("train/holdout token alignment methods differ")
        train_source_hashes = {pair["source_sha256"] for pair in train_pairs}
        holdout_source_hashes = {pair["source_sha256"] for pair in holdout_pairs}
        if train_source_hashes & holdout_source_hashes:
            raise LatentAdapterError("source hash leakage: token alignment source appears in train and holdout")
        for key, value in (
            ("sender_tokenizer_revision", sender_tokenizer_revision),
            ("receiver_tokenizer_revision", receiver_tokenizer_revision),
        ):
            if type(value) is not str or not value or len(value) > 160:
                raise LatentAdapterError("tokenwise adapter requires " + key)
        alignment_method = train_method
        alignment_sha256 = _token_alignment_digest(
            list(train_pairs) + list(holdout_pairs),
            method=alignment_method,
            sender_tokenizer_revision=sender_tokenizer_revision,
            receiver_tokenizer_revision=receiver_tokenizer_revision,
        )
    elif sender_tokenizer_revision is not None or receiver_tokenizer_revision is not None:
        raise LatentAdapterError("tokenizer revisions are only valid for TOKENWISE adapters")
    if len(train_pairs) < 8 or len(holdout_pairs) < 4 or len(train_sources) < 4 or len(holdout_sources) < 2:
        raise LatentAdapterError("insufficient independent source groups for alignment holdout")
    sender_dim, receiver_dim = len(x_train[0]), len(y_train[0])
    if len(x_holdout[0]) != sender_dim or len(y_holdout[0]) != receiver_dim:
        raise LatentAdapterError("train/holdout activation dimensions differ")
    if rank > min(_MAX_RANK, sender_dim, receiver_dim, len(train_pairs) - 1):
        raise LatentAdapterError("rank exceeds available geometry or training rows")
    try:
        import numpy as np
    except ImportError as exc:
        raise LatentAdapterUnavailable("NumPy is required only for offline adapter fitting") from exc

    x = np.asarray(x_train, dtype=np.float64)
    y = np.asarray(y_train, dtype=np.float64)
    xh = np.asarray(x_holdout, dtype=np.float64)
    yh = np.asarray(y_holdout, dtype=np.float64)
    x_mean = x.mean(axis=0)
    y_mean = y.mean(axis=0)
    xc = x - x_mean
    yc = y - y_mean
    _, singular, vt = np.linalg.svd(xc, full_matrices=False)
    tolerance = max(xc.shape) * (singular[0] if singular.size else 0.0) * np.finfo(np.float64).eps
    effective_rank = min(rank, int(np.count_nonzero(singular > tolerance)))
    if effective_rank < 1:
        raise LatentAdapterError("sender activations have no trainable variance")
    sender_factor = vt[:effective_rank].T.copy()
    z = xc @ sender_factor
    gram = z.T @ z + float(ridge) * np.eye(effective_rank, dtype=np.float64)
    receiver_factor = np.linalg.solve(gram, z.T @ yc)

    holdout_z = (xh - x_mean) @ sender_factor
    prediction = holdout_z @ receiver_factor + y_mean
    holdout_mse = float(np.mean((prediction - yh) ** 2))
    baseline_mse = float(np.mean((yh - y_mean) ** 2))

    rng = np.random.default_rng(seed)
    shuffled_y = yc[rng.permutation(len(yc))]
    shuffled_factor = np.linalg.solve(gram, z.T @ shuffled_y)
    shuffled_prediction = holdout_z @ shuffled_factor + y_mean
    shuffled_mse = float(np.mean((shuffled_prediction - yh) ** 2))
    relative_improvement = 0.0 if baseline_mse <= 1e-12 else (baseline_mse - holdout_mse) / baseline_mse
    shuffle_advantage = 0.0 if shuffled_mse <= 1e-12 else (shuffled_mse - holdout_mse) / shuffled_mse
    candidate = (
        relative_improvement >= float(min_relative_improvement)
        and holdout_mse + 1e-12 < baseline_mse
        and holdout_mse + 1e-12 < shuffled_mse
    )
    linear_map = sender_factor @ receiver_factor
    affine_bias = y_mean - x_mean @ linear_map
    linear_map_frobenius = float(np.linalg.norm(linear_map))
    affine_bias_l2 = float(np.linalg.norm(affine_bias))
    parameter_count = int(sender_dim + receiver_dim + sender_dim * effective_rank + effective_rank * receiver_dim)
    adapter = {
        "schema": TOKENWISE_SCHEMA if projection_scope == "TOKENWISE" else SCHEMA,
        "status": "ALIGNMENT_CANDIDATE" if candidate else "REJECTED",
        "sender_role": sender_role,
        "receiver_role": receiver_role,
        "sender_tap_id": sender_tap_id,
        "receiver_tap_id": receiver_tap_id,
        "projection_scope": projection_scope,
        **({
            "alignment_method": alignment_method,
            "alignment_sha256": alignment_sha256,
            "sender_tokenizer_revision": sender_tokenizer_revision,
            "receiver_tokenizer_revision": receiver_tokenizer_revision,
        } if projection_scope == "TOKENWISE" else {}),
        "sender_model_revision": sender_model_revision,
        "receiver_model_revision": receiver_model_revision,
        "sender_model_sha256": sender_model_sha256,
        "receiver_model_sha256": receiver_model_sha256,
        "sender_dim": sender_dim,
        "receiver_dim": receiver_dim,
        "rank": effective_rank,
        "sender_mean": x_mean.tolist(),
        "receiver_mean": y_mean.tolist(),
        "sender_factor": sender_factor.tolist(),
        "receiver_factor": receiver_factor.tolist(),
        "metrics": {
            "holdout_mse": holdout_mse,
            "mean_baseline_mse": baseline_mse,
            "shuffled_train_mse": shuffled_mse,
            "relative_improvement": relative_improvement,
            "shuffle_advantage": shuffle_advantage,
            "min_relative_improvement": float(min_relative_improvement),
            "linear_map_frobenius": linear_map_frobenius,
            "affine_bias_l2": affine_bias_l2,
            "parameter_count": parameter_count,
            "gradient_norm": None,
            "gradient_based_training": False,
            "old_task_retention_measured": False,
        },
        "train_pairs": len(train_pairs),
        "holdout_pairs": len(holdout_pairs),
        "train_source_count": len(train_sources),
        "holdout_source_count": len(holdout_sources),
        "training_method": "SOURCE_PCA_RIDGE_LOW_RANK_AFFINE",
        "holdout_policy": "SOURCE_ID_DISJOINT",
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }
    adapter["adapter_sha256"] = hashlib.sha256(_serialize(adapter)).hexdigest()
    _validate_adapter(adapter, require_candidate=False)
    return adapter


def _project_vector_validated(adapter: Mapping, sender_vector, *, sender_model_sha256: str,
                              receiver_model_sha256: str, sender_tap_id: str,
                              receiver_tap_id: str) -> list[float]:
    if (_sha256_text(sender_model_sha256, "sender_model_sha256") != adapter["sender_model_sha256"]
            or _sha256_text(receiver_model_sha256, "receiver_model_sha256") != adapter["receiver_model_sha256"]
            or sender_tap_id != adapter["sender_tap_id"] or receiver_tap_id != adapter["receiver_tap_id"]):
        raise LatentAdapterError("adapter model revision/hash or tap binding mismatch")
    vector = _finite_vector(sender_vector, "sender_vector", adapter["sender_dim"])
    centered = [value - mean for value, mean in zip(vector, adapter["sender_mean"])]
    latent = [sum(centered[i] * adapter["sender_factor"][i][j] for i in range(adapter["sender_dim"]))
              for j in range(adapter["rank"])]
    projected = [adapter["receiver_mean"][j] + sum(latent[k] * adapter["receiver_factor"][k][j]
                 for k in range(adapter["rank"])) for j in range(adapter["receiver_dim"])]
    if any(not math.isfinite(value) for value in projected):
        raise LatentAdapterError("projected activation is non-finite")
    return projected


def project_vector(adapter: Mapping, sender_vector, *, sender_model_sha256: str,
                   receiver_model_sha256: str, sender_tap_id: str, receiver_tap_id: str) -> list[float]:
    """Apply the trained adapter without NumPy or other runtime dependencies."""
    _validate_adapter(adapter)
    return _project_vector_validated(
        adapter, sender_vector, sender_model_sha256=sender_model_sha256,
        receiver_model_sha256=receiver_model_sha256, sender_tap_id=sender_tap_id,
        receiver_tap_id=receiver_tap_id,
    )


def project_event(adapter: Mapping, sender_vector, **bindings) -> list[float]:
    """Project one source-bound event vector with an event-level adapter.

    Pooled tap fitting produces one vector per source/event. It must not be
    broadcast over token rows: the native receiver has a separate token-position
    contract and currently has no latent-prefix position mode.
    """
    _validate_adapter(adapter)
    if adapter["projection_scope"] not in {"PAIRED_VECTOR", "EVENT_POOLED_NONZERO_MEAN"}:
        raise LatentAdapterError("tokenwise adapter cannot be projected as one event vector")
    return _project_vector_validated(adapter, sender_vector, **bindings)


def project_rows(adapter: Mapping, sender_vectors, **bindings) -> list[list[float]]:
    """Project token rows only when the adapter was fitted tokenwise."""
    _validate_adapter(adapter)
    if adapter["projection_scope"] != "TOKENWISE":
        raise LatentAdapterError("event-level adapter requires project_event; token-aligned fit is required for rows")
    if not isinstance(sender_vectors, (list, tuple)) or not sender_vectors or len(sender_vectors) > 64:
        raise LatentAdapterError("sender tap must contain 1..64 activation rows")
    return [_project_vector_validated(adapter, row, **bindings) for row in sender_vectors]


def build_native_receiver_input(adapter: Mapping, sender_vectors, *, token_ids,
                                tokenizer_revision: str, **bindings) -> dict:
    """Build the exact token-row input contract accepted by native receiver v3.

    This requires a TOKENWISE adapter trained against the receiver's actual
    input-embedding tap. Event-pooled adapters are refused: the current receiver
    has no LATENT_PREFIX position mode for a single pooled event vector.
    Token IDs are used only to verify row count and are not returned.
    """
    _validate_adapter(adapter)
    if adapter["projection_scope"] != "TOKENWISE":
        raise LatentAdapterError("native receiver requires a tokenwise adapter; pooled event vectors need a latent-prefix contract")
    expected_tap = _NATIVE_INPUT_TAP_IDS.get(adapter["receiver_role"])
    if expected_tap is None or adapter["receiver_tap_id"] != expected_tap or bindings.get("receiver_tap_id") != expected_tap:
        raise LatentAdapterError("native receiver adapter is not bound to the receiver input-embedding tap")
    if not isinstance(sender_vectors, (list, tuple)) or not sender_vectors or len(sender_vectors) > 64:
        raise LatentAdapterError("sender tap must contain 1..64 token rows")
    if not isinstance(token_ids, (list, tuple)) or len(token_ids) != len(sender_vectors):
        raise LatentAdapterError("token ID count differs from token-aligned activation rows")
    if any(type(token_id) is not int or token_id < 0 for token_id in token_ids):
        raise LatentAdapterError("token IDs must be non-negative integers")
    if type(tokenizer_revision) is not str or not tokenizer_revision or len(tokenizer_revision) > 160:
        raise LatentAdapterError("tokenizer revision is required for native input alignment")
    if tokenizer_revision != adapter.get("receiver_tokenizer_revision"):
        raise LatentAdapterError("receiver tokenizer revision mismatch")

    projected = project_rows(adapter, sender_vectors, **bindings)
    from . import native_latent_receiver
    rows, input_dim, _payload, input_sha256 = native_latent_receiver._vector_payload(projected)
    positions = native_latent_receiver._validate_positions(
        list(range(rows)), rows, native_latent_receiver.POSITION_MODE,
    )
    return {
        "vectors": projected,
        "position_ids": positions,
        "position_mode": native_latent_receiver.POSITION_MODE,
        "input_rows": rows,
        "input_dim": input_dim,
        "input_sha256": input_sha256,
        "tokenizer_revision": tokenizer_revision,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }


def save_adapter(adapter: Mapping, path: str | os.PathLike) -> str:
    """Atomically persist adapter parameters; returns the exact checkpoint SHA-256."""
    _validate_adapter(adapter, require_candidate=False)
    data = _serialize(adapter)
    target = Path(path)
    if target.exists() and target.is_symlink():
        raise LatentAdapterError("adapter checkpoint symlink refused")
    parent = target.parent.resolve(strict=True)
    if target.parent.is_symlink() or not parent.is_dir():
        raise LatentAdapterError("adapter checkpoint parent must be a real directory")
    fd, temporary = tempfile.mkstemp(prefix="." + target.name + ".", dir=str(parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return hashlib.sha256(data).hexdigest()


def load_adapter(path: str | os.PathLike) -> dict:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise LatentAdapterError("adapter checkpoint must be a regular non-symlink file")
    if target.stat().st_size > _MAX_FILE_BYTES:
        raise LatentAdapterError("adapter checkpoint exceeds size limit")
    data = target.read_bytes()
    if len(data) < len(_MAGIC) + 4 or data[:len(_MAGIC)] != _MAGIC:
        raise LatentAdapterError("adapter checkpoint magic mismatch")
    header_size = struct.unpack("<I", data[len(_MAGIC):len(_MAGIC) + 4])[0]
    header_start = len(_MAGIC) + 4
    header_end = header_start + header_size
    if header_size > 65536 or header_end > len(data):
        raise LatentAdapterError("adapter checkpoint header is invalid")
    try:
        header = json.loads(data[header_start:header_end].decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise LatentAdapterError("adapter checkpoint header cannot be decoded") from exc
    payload = data[header_end:]
    if hashlib.sha256(payload).hexdigest() != header.get("weights_sha256"):
        raise LatentAdapterError("adapter checkpoint weight digest mismatch")
    count = header.get("weight_count")
    if type(count) is not int or count < 1 or count * 4 != len(payload):
        raise LatentAdapterError("adapter checkpoint weight count mismatch")
    weights = array("f")
    weights.frombytes(payload)
    if sys.byteorder != "little":
        weights.byteswap()
    if any(not math.isfinite(value) for value in weights):
        raise LatentAdapterError("adapter checkpoint contains non-finite weights")
    source_dim, receiver_dim, rank = header.get("sender_dim"), header.get("receiver_dim"), header.get("rank")
    if (type(source_dim) is not int or type(receiver_dim) is not int or type(rank) is not int
            or not 1 <= source_dim <= _MAX_DIM or not 1 <= receiver_dim <= _MAX_DIM
            or not 1 <= rank <= min(_MAX_RANK, source_dim, receiver_dim)):
        raise LatentAdapterError("adapter checkpoint dimensions are invalid")
    expected_count = source_dim + receiver_dim + source_dim * rank + rank * receiver_dim
    if expected_count != count:
        raise LatentAdapterError("adapter checkpoint tensor geometry mismatch")
    cursor = 0
    sender_mean = list(weights[cursor:cursor + source_dim]); cursor += source_dim
    receiver_mean = list(weights[cursor:cursor + receiver_dim]); cursor += receiver_dim
    sender_flat = list(weights[cursor:cursor + source_dim * rank]); cursor += source_dim * rank
    receiver_flat = list(weights[cursor:cursor + rank * receiver_dim])
    header.pop("weight_count", None)
    header.pop("weights_sha256", None)
    adapter = dict(header)
    adapter.update({
        "sender_mean": sender_mean,
        "receiver_mean": receiver_mean,
        "sender_factor": [sender_flat[i * rank:(i + 1) * rank] for i in range(source_dim)],
        "receiver_factor": [receiver_flat[i * receiver_dim:(i + 1) * receiver_dim] for i in range(rank)],
        "adapter_sha256": hashlib.sha256(data).hexdigest(),
    })
    _validate_adapter(adapter, require_candidate=False)
    return adapter

def fit_from_tap_records(
    home,
    *,
    sender_role: str,
    receiver_role: str,
    sender_model_revision: str,
    receiver_model_revision: str,
    sender_tap_id: str,
    receiver_tap_id: str,
    sender_model_sha256: str,
    receiver_model_sha256: str,
    min_pairs: int = 20,
    max_pairs: int = 32,
    holdout_fraction: float = 0.25,
    split_seed: int = 17,
    rank: int = 16,
    ridge: float = 1e-4,
    min_relative_improvement: float = 0.02,
    fit_seed: int = 7,
) -> dict:
    """Fit from persisted, exact-paired B1/B2 tap packets without reading source text.

    Pairing requires the same full SourceRef, event and generation. At most one
    pair is retained per opaque source_id, so source groups cannot cross the
    deterministic train/holdout split. Model hashes must be supplied by a
    caller that has independently read the installed model manifest; tap
    packets store revisions and tap IDs but not model-file hashes.

    The returned adapter is a closed-form PCA+ridge alignment candidate. It is
    not gradient-based JEPA learning, semantic transfer, or a production B3
    route. The caller may persist an accepted adapter separately with
    save_adapter(); this function never writes to Runtime or SQLite.
    """
    from .latent_alignment_audit import (
        MAX_SAMPLES, _packet_order, _pool_without_position0, _read_tap_blob,
        _validate_packet, load_tap_records,
    )

    if sender_role not in _ROLES or receiver_role not in _ROLES or sender_role == receiver_role:
        raise LatentAdapterError("persisted tap fitting supports distinct B1/B2 roles only")
    if type(min_pairs) is not int or min_pairs < 20:
        raise LatentAdapterError("latent adapter fitting requires at least 20 source-disjoint pairs")
    if type(max_pairs) is not int or not min_pairs <= max_pairs <= MAX_SAMPLES:
        raise LatentAdapterError("max_pairs must cover min_pairs and stay within the audit bound")
    if (type(holdout_fraction) not in (int, float)
            or not math.isfinite(float(holdout_fraction))
            or not 0.15 <= float(holdout_fraction) <= 0.40):
        raise LatentAdapterError("holdout_fraction must be between 0.15 and 0.40")
    if type(split_seed) is not int:
        raise LatentAdapterError("split_seed must be an integer")
    for key, value in (
        ("sender_model_revision", sender_model_revision),
        ("receiver_model_revision", receiver_model_revision),
        ("sender_tap_id", sender_tap_id),
        ("receiver_tap_id", receiver_tap_id),
    ):
        if type(value) is not str or not value or len(value) > 160:
            raise LatentAdapterError("invalid tap/model binding: " + key)
    sender_model_sha256 = _sha256_text(sender_model_sha256, "sender_model_sha256")
    receiver_model_sha256 = _sha256_text(receiver_model_sha256, "receiver_model_sha256")

    latest = {}
    invalid_metadata = 0
    for record in load_tap_records(Path(home)):
        packet = record.get("payload") if isinstance(record, dict) else None
        try:
            source_key, role, revision, event_id, generation_id = _validate_packet(packet)
            if role not in {sender_role, receiver_role}:
                continue
            order = _packet_order(record.get("created"))
            key = (source_key, role, revision, event_id, generation_id)
            if key not in latest or order > latest[key][0]:
                latest[key] = (order, packet)
        except (TypeError, KeyError, ValueError):
            invalid_metadata += 1

    by_event_source = {}
    for (source_key, role, revision, event_id, generation_id), value in latest.items():
        group = (source_key, event_id, generation_id)
        by_event_source.setdefault(group, {}).setdefault(role, {})[revision] = value

    # Source IDs, not spans, define the split unit. If a source has multiple
    # spans/events/generations, only its newest exact-paired observation wins.
    by_source = {}
    for (source_key, event_id, generation_id), roles in by_event_source.items():
        sender_value = roles.get(sender_role, {}).get(sender_model_revision)
        receiver_value = roles.get(receiver_role, {}).get(receiver_model_revision)
        if sender_value is None or receiver_value is None:
            continue
        pair_order = max(sender_value[0], receiver_value[0])
        source_id = source_key[0]
        existing = by_source.get(source_id)
        if existing is None or pair_order > existing[0]:
            by_source[source_id] = (
                pair_order, source_key, event_id, generation_id,
                sender_value[1], receiver_value[1],
            )

    if not by_source:
        raise LatentAdapterError("no exact paired taps for the requested model revisions")

    candidate_pairs = []
    invalid_blobs = 0
    for source_id, (_order, source_key, event_id, generation_id, sender_packet, receiver_packet) in by_source.items():
        if sender_packet.get("tap_id") != sender_tap_id or receiver_packet.get("tap_id") != receiver_tap_id:
            invalid_metadata += 1
            continue
        try:
            sender_vectors, _ = _read_tap_blob(Path(home), sender_packet)
            receiver_vectors, _ = _read_tap_blob(Path(home), receiver_packet)
            sender_vector, _, _ = _pool_without_position0(sender_vectors)
            receiver_vector, _, _ = _pool_without_position0(receiver_vectors)
        except (OSError, TypeError, ValueError):
            invalid_blobs += 1
            continue
        source_group = hashlib.sha256(source_id.encode("utf-8")).hexdigest()
        pair_material = json.dumps(
            [source_key, event_id, generation_id], separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")
        pair_id = hashlib.sha256(pair_material).hexdigest()
        candidate_pairs.append({
            "pair_id": pair_id,
            "source_id": source_group,
            "sender_vector": sender_vector,
            "receiver_vector": receiver_vector,
        })

    if len(candidate_pairs) < min_pairs:
        raise LatentAdapterError(
            "insufficient valid source-disjoint pairs: "
            + str(len(candidate_pairs)) + "/" + str(min_pairs)
            + "; invalid_metadata=" + str(invalid_metadata)
            + "; invalid_blobs=" + str(invalid_blobs)
        )

    rng = __import__("random").Random(split_seed)
    candidate_pairs.sort(key=lambda item: item["pair_id"])
    rng.shuffle(candidate_pairs)
    selected = candidate_pairs[:max_pairs]
    holdout_count = max(4, int(math.ceil(len(selected) * float(holdout_fraction))))
    if len(selected) - holdout_count < 8:
        raise LatentAdapterError("source-disjoint split leaves fewer than eight training pairs")
    train_pairs = selected[:-holdout_count]
    holdout_pairs = selected[-holdout_count:]

    adapter = fit_adapter(
        train_pairs, holdout_pairs,
        sender_role=sender_role,
        receiver_role=receiver_role,
        sender_tap_id=sender_tap_id,
        receiver_tap_id=receiver_tap_id,
        sender_model_revision=sender_model_revision,
        receiver_model_revision=receiver_model_revision,
        sender_model_sha256=sender_model_sha256,
        receiver_model_sha256=receiver_model_sha256,
        rank=rank,
        ridge=ridge,
        min_relative_improvement=min_relative_improvement,
        seed=fit_seed,
        projection_scope="EVENT_POOLED_NONZERO_MEAN",
    )
    return {
        "schema": "v14.latent-tap-adapter-fit/1",
        "status": adapter["status"],
        "adapter": adapter,
        "paired_source_count": len(candidate_pairs),
        "selected_pair_count": len(selected),
        "train_source_count": len(train_pairs),
        "holdout_source_count": len(holdout_pairs),
        "split_seed": split_seed,
        "split_policy": "ONE_PAIR_PER_SOURCE_ID;DETERMINISTIC_SOURCE_DISJOINT_HOLDOUT",
        "invalid_metadata_or_tap_bindings": invalid_metadata,
        "invalid_or_unreadable_blobs": invalid_blobs,
        "model_hashes_supplied_by_caller": True,
        "model_manifest_verified_here": False,
        "model_weight_license_verified_by_this_tool": False,
        "adapter_code_license": "project-owned; no third-party implementation imported",
        "source_text_read": False,
        "raw_activation_vectors_exported": False,
        "sqlite_written": False,
        "model_loaded": False,
        "gradient_based_training": False,
        "old_task_retention_measured": False,
        "adapter_parameters_fitted": True,
        "adapter_persisted": False,
        "body_weights_modified": False,
        "semantic_use_proven": False,
        "production_route": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }
