"""Small, dependency-free controls for the V14 native receiver causal audit."""
from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Mapping


class AuditControlError(ValueError):
    pass


def moment_matched_random_rows(rows, seed: str):
    """Randomly mix token rows while preserving mean and full second moments.

    Three seeded Householder reflections act in the zero-sum row subspace.
    They preserve the column mean and X.T@X in exact arithmetic while
    changing token-row identity. Float32 serialization adds only rounding.
    This is not a Gaussian sample or independent-noise guarantee.
    """
    if type(seed) is not str or not seed:
        raise AuditControlError("moment-matched seed is required")
    if not isinstance(rows, (list, tuple)) or len(rows) < 3:
        raise AuditControlError("moment-matched control needs at least three token rows")
    if not isinstance(rows[0], (list, tuple)) or not rows[0]:
        raise AuditControlError("moment-matched rows must be non-empty vectors")
    dim = len(rows[0])
    matrix = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != dim:
            raise AuditControlError("moment-matched rows are ragged")
        clean = []
        for value in row:
            if type(value) not in (int, float) or not math.isfinite(float(value)) or abs(float(value)) > 1.0e6:
                raise AuditControlError("moment-matched rows contain non-finite/unbounded values")
            clean.append(float(value))
        matrix.append(clean)

    count = len(matrix)
    rng_seed = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(rng_seed)
    original = [row[:] for row in matrix]
    applied = 0
    for _ in range(max(24, count * 8)):
        vector = [rng.gauss(0.0, 1.0) for _ in range(count)]
        mean = sum(vector) / count
        vector = [value - mean for value in vector]
        norm = math.sqrt(sum(value * value for value in vector))
        if norm <= 1.0e-12:
            continue
        vector = [value / norm for value in vector]
        projection = [sum(vector[i] * matrix[i][j] for i in range(count)) for j in range(dim)]
        mixed = [
            [matrix[i][j] - 2.0 * vector[i] * projection[j] for j in range(dim)]
            for i in range(count)
        ]
        if any(not math.isfinite(value) or abs(value) > 1.0e6 for row in mixed for value in row):
            raise AuditControlError("moment-matched transform produced unbounded values")
        difference = max(abs(mixed[i][j] - matrix[i][j]) for i in range(count) for j in range(dim))
        if difference > 1.0e-9:
            matrix = mixed
            applied += 1
        if applied >= 3:
            break
    if applied == 0 or max(abs(matrix[i][j] - original[i][j]) for i in range(count) for j in range(dim)) <= 1.0e-7:
        raise AuditControlError("no non-trivial moment-matched randomization is possible")

    tolerance = 2.0e-6
    for j in range(dim):
        old_mean = sum(original[i][j] for i in range(count)) / count
        new_mean = sum(matrix[i][j] for i in range(count)) / count
        if abs(old_mean - new_mean) > tolerance * max(1.0, abs(old_mean)):
            raise AuditControlError("moment-matched transform changed a column mean")
        for k in range(dim):
            old_second = sum(original[i][j] * original[i][k] for i in range(count))
            new_second = sum(matrix[i][j] * matrix[i][k] for i in range(count))
            if abs(old_second - new_second) > tolerance * max(1.0, abs(old_second)):
                raise AuditControlError("moment-matched transform changed the second moment")
    return matrix


def build_private_omission_proof(original_text, public_text, original_record, public_record, private_byte_spans):
    """Prove exact byte-span deletion; this does not classify whether spans are private."""
    if type(original_text) is not str or type(public_text) is not str:
        raise AuditControlError("private-omission texts must be strings")
    if not isinstance(original_record, Mapping) or not isinstance(public_record, Mapping):
        raise AuditControlError("private-omission source records are required")
    original = original_text.encode("utf-8")
    public = public_text.encode("utf-8")

    def checked_ref(record, label, text_value):
        ref = record.get("source_ref")
        if not isinstance(ref, Mapping):
            raise AuditControlError(label + " source reference is missing")
        source_id, digest = ref.get("source_id"), ref.get("sha256")
        if type(source_id) is not str or not source_id or type(digest) is not str or len(digest) != 64:
            raise AuditControlError(label + " source reference is invalid")
        if any(ch not in "0123456789abcdef" for ch in digest):
            raise AuditControlError(label + " source digest is invalid")
        if digest != hashlib.sha256(text_value).hexdigest() or ref.get("char_end") != len(text_value.decode("utf-8")):
            raise AuditControlError(label + " source text differs from its source reference")
        return {"source_id": source_id, "sha256": digest}

    original_ref = checked_ref(original_record, "original", original)
    public_ref = checked_ref(public_record, "public", public)
    if original_ref == public_ref:
        raise AuditControlError("private-omission source must be distinct")
    if not isinstance(private_byte_spans, (list, tuple)) or not private_byte_spans:
        raise AuditControlError("annotated private byte spans are required")

    previous = 0
    reconstructed = bytearray()
    normalized = []
    removed = 0
    for span in private_byte_spans:
        if not isinstance(span, Mapping) or span.get("label") != "PRIVATE":
            raise AuditControlError("each removed span must carry a PRIVATE dataset annotation")
        start, end = span.get("start"), span.get("end")
        if type(start) is not int or type(end) is not int or not previous <= start < end <= len(original):
            raise AuditControlError("private byte spans are invalid or overlapping")
        reconstructed.extend(original[previous:start])
        normalized.append({"start": start, "end": end, "label": "PRIVATE"})
        removed += end - start
        previous = end
    reconstructed.extend(original[previous:])
    if not removed or bytes(reconstructed) != public:
        raise AuditControlError("public text is not the exact original with annotated spans removed")
    if len(public) >= len(original):
        raise AuditControlError("private omission did not remove any source bytes")

    span_material = repr([(item["start"], item["end"], item["label"]) for item in normalized]).encode()
    return {
        "schema": "v14.private-omission-proof/1",
        "original_source_ref": original_ref,
        "public_source_ref": public_ref,
        "removed_byte_count": removed,
        "private_span_manifest_sha256": hashlib.sha256(span_material).hexdigest(),
        "proof_kind": "BYTE_EXACT_ANNOTATED_PRIVATE_SPAN_REMOVAL_V1",
        "semantic_privacy_classification_proven": False,
    }
