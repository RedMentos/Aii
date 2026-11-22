"""Run137: opt-in evidence-id type guard before any AgeControl write.

Not wired into production AgeControl or operator. This preserves the exact
Run131 finite-evidence validator and Run132 read-only state diagnostic.
"""
from __future__ import annotations

from scripts import age_evidence_finite_candidate as finite


def record(controller, subject, metrics, evidence_id=None):
    """Reject explicit non-string/empty IDs before the existing finite guard."""
    if evidence_id is not None and (type(evidence_id) is not str or not evidence_id):
        raise ValueError("AGE_EVIDENCE_ID_INVALID")
    return finite.record(controller, subject, metrics, evidence_id=evidence_id)
