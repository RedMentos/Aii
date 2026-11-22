"""Independent default-off Run141 review: reject unscoped typed A/B pair clauses.

A shared typed clause cannot prove that its values belong to either option.
Upstream must authenticate exact source/history. Frozen runtime is untouched.
"""
from __future__ import annotations

import re

from scripts import context_option_reference_candidate as parent
from v13.agi import eligibility as original


# The frozen Run141 clause reader is period-delimited. Two option labels
# sharing that clause cannot each own its typed values, regardless of whether
# they are joined by "and", "versus", a semicolon, or other punctuation.
A_TAG = re.compile(r"\boption\s+A\b", re.I)
B_TAG = re.compile(r"\boption\s+B\b", re.I)


def ambiguous_typed_pair(text):
    """Refuse two different option labels in one typed period-delimited clause."""
    if type(text) is not str:
        raise ValueError("OPTION_SOURCE_INPUT_INVALID")
    return any(
        A_TAG.search(clause) and B_TAG.search(clause) and parent.OPTION_WORDS.search(clause)
        for clause in text.split(".")
    )


def option_with_pair_scope(entity, current, earlier=()):
    """Same newest-first precedence as Run141; refuse ambiguous selected source."""
    if entity not in ("A", "B") or type(current) is not str or type(earlier) not in (tuple, list) or any(
        type(x) is not str for x in earlier
    ):
        raise ValueError("OPTION_SOURCE_INPUT_INVALID")
    for source in (current, *reversed(earlier)):
        status, value = parent._from_text(entity, source)
        # An unscoped pair with typed values is never evidence for either option.
        # It may be ignored only if this option was fully established by a
        # newer, unambiguous source (in which case we returned already).
        if ambiguous_typed_pair(source):
            return None
        if status == "COMPLETE":
            return value
        if status in ("BLOCKED_PARTIAL", "BLOCKED_CONFLICT"):
            return None
    return None


def read_fixed_pair_scope(current, earlier=()):
    """Run141 READ_SCHEMA shape; no native/model calls and no authority change."""
    if type(current) is not str or type(earlier) not in (tuple, list) or any(
        type(x) is not str for x in earlier
    ):
        raise ValueError("OPTION_SOURCE_INPUT_INVALID")
    result = {key: original.fixed_rule(key, current, earlier)
              for key in ("budget", "deadline", "local_only")}
    options = [option_with_pair_scope(entity, current, earlier)
               for entity in ("A", "B")]
    result["options"] = options if all(o is not None for o in options) else None
    return result
