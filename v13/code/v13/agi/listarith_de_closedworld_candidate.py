"""Unwired, fail-closed German typed-list completeness candidate (seed101).

A positive exact name/number source binding is not a completeness proof:
omitting one real source item can silently change the result. This wrapper
requires each integer occurrence in the *pre-question data* to be claimed
exactly once by the C3 typed read. The intentionally narrow domain abstains
on dates, metadata numbers, stated aggregates, decimals, and ambiguous
question boundaries rather than inventing which numbers are irrelevant.

No native calls, live tool consumer, learning, approvals or age promotion.
Frozen seed79/83 native scorers and the existing pipeline are unchanged.
"""
from __future__ import annotations

from collections import Counter
import re

from . import listarith
from . import listarith_de_shadow_pipeline as baseline

AUTHORITY = "SHADOW_ONLY"
REVISION = "de-closedworld-seed101-v1"
# Disallow partial integer extraction from a decimal; no locale guessing.
_DECIMAL = re.compile(r"(?<!\d)\d+[.,]\d+")
# Standalone signed integer, not an embedded identifier or decimal fragment.
_INTEGER = re.compile(r"(?<![\w.,+\-\u2212])[+\-\u2212]?\d+(?![\w]|[.,]\d)")


def _abstain(result, reason):
    result.update(status="SHADOW_ABSTAIN", reason=reason, operation=None,
                  value=None, closed_world_checked=False)
    for key in ("recipe", "input_count"):
        result.pop(key, None)
    return result


def evaluate(text, raw_json):
    """Conservative subset of the original SHADOW pipeline's results.

    A baseline abstention is never upgraded. Native provenance remains the
    caller's responsibility; this does not validate a native/model claim.
    """
    original = baseline.evaluate(text, raw_json)
    result = dict(original)
    result["revision"] = REVISION
    result["closed_world_checked"] = False
    result["closed_world_domain"] = "ALL_PREQUESTION_INTEGERS"
    if original.get("status") != "SHADOW_RESULT":
        return result
    if not isinstance(text, str):
        return _abstain(result, "SOURCE_INVALID")
    question = listarith.question_part(text)
    trimmed = text.rstrip()
    if not question or not trimmed.endswith(question) or question == trimmed:
        return _abstain(result, "QUESTION_BOUNDARY_AMBIGUOUS")
    data = trimmed[:-len(question)].rstrip()
    if not data or not data.endswith((".", "!", "?")):
        return _abstain(result, "QUESTION_BOUNDARY_AMBIGUOUS")
    if _DECIMAL.search(data):
        return _abstain(result, "DECIMAL_OR_NONINTEGER_SOURCE")
    try:
        values = baseline.parse_typed(raw_json)
        # Baseline binds to the full text. Require all pairs in the data
        # segment so numbers appearing only in a question cannot be used.
        baseline.verify_name_number_bindings(data, values)
    except (baseline.UnsafeRead, ValueError, TypeError):
        return _abstain(result, "PAIR_NOT_IN_DATA_SEGMENT")
    numbers = Counter(int(m.group().replace("\u2212", "-"))
                      for m in _INTEGER.finditer(data))
    extracted = Counter(v["number"] for v in values)
    if numbers != extracted:
        return _abstain(result, "SOURCE_NUMBER_COVERAGE_MISMATCH")
    result["closed_world_checked"] = True
    result["source_integer_occurrences"] = sum(numbers.values())
    return result
