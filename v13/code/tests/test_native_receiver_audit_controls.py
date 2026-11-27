import hashlib
import math
import pytest

from v13.native_receiver_audit_controls import (
    AuditControlError, build_private_omission_proof, moment_matched_random_rows,
)


def _record(source_id, text):
    return {"source_ref": {"source_id": source_id,
        "sha256": hashlib.sha256(text.encode()).hexdigest(), "char_end": len(text)}}


def test_moment_matched_random_preserves_mean_and_full_second_moment():
    rows = [[0.1, 0.2, 0.4], [0.3, 0.7, 0.2], [0.9, 0.1, 0.6], [0.4, 0.8, 0.5]]
    mixed = moment_matched_random_rows(rows, "task-17")
    assert mixed != rows
    for j in range(3):
        assert math.isclose(sum(r[j] for r in rows), sum(r[j] for r in mixed), abs_tol=1e-8)
        for k in range(3):
            old = sum(r[j] * r[k] for r in rows)
            new = sum(r[j] * r[k] for r in mixed)
            assert math.isclose(old, new, rel_tol=1e-8, abs_tol=1e-8)
    assert moment_matched_random_rows(rows, "task-17") == mixed


def test_moment_matched_random_rejects_degenerate_or_short_inputs():
    with pytest.raises(AuditControlError):
        moment_matched_random_rows([[1.0, 2.0], [1.0, 2.0]], "seed")
    with pytest.raises(AuditControlError):
        moment_matched_random_rows([[1.0], [1.0], [1.0]], "seed")


def test_private_omission_proof_accepts_exact_annotated_removal():
    original, public = "The cat sat.", "The cat"
    proof = build_private_omission_proof(original, public, _record("a", original), _record("b", public),
        [{"start": 7, "end": 12, "label": "PRIVATE"}])
    assert proof["removed_byte_count"] == 5
    assert proof["semantic_privacy_classification_proven"] is False
    assert proof["proof_kind"] == "BYTE_EXACT_ANNOTATED_PRIVATE_SPAN_REMOVAL_V1"


@pytest.mark.parametrize("span", [
    {"start": 7, "end": 12, "label": "PUBLIC"},
    {"start": 6, "end": 12, "label": "PRIVATE"},
    {"start": 7, "end": 13, "label": "PRIVATE"},
])
def test_private_omission_proof_rejects_unmarked_or_wrong_span(span):
    original = "The cat sat."
    with pytest.raises(AuditControlError):
        build_private_omission_proof(original, "The cat", _record("a", original), _record("b", "The cat"), [span])


def test_private_omission_proof_rejects_non_exact_public_source():
    original = "The cat sat."
    with pytest.raises(AuditControlError):
        build_private_omission_proof(original, "The cat!", _record("a", original), _record("b", "The cat!"),
            [{"start": 7, "end": 12, "label": "PRIVATE"}])
