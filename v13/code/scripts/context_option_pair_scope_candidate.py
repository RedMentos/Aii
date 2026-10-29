"""Independent default-off Run141 review: reject unscoped typed A/B pair clauses.

A shared typed clause cannot prove that its values belong to either option.
Upstream must authenticate exact source/history. Frozen runtime is untouched.
"""
from __future__ import annotations

import re

from scripts import context_option_reference_candidate as parent
from v13.agi import eligibility as original


# Both orders; explicit conjunction or punctuation; second "Option" optional.
JOINT = re.compile(
    r"\boption\s+([AB])\s*(?:and|or|,|&|/)\s*(?:option\s+)?([AB])\b[^.]*",
    re.I,
)


def ambiguous_typed_pair(text):
    """True if a joint A/B clause contains option-typed values, not a pure reference."""
    if type(text) is not str:
        raise ValueError("OPTION_SOURCE_INPUT_INVALID")
    for match in JOINT.finditer(text):
        if match.group(1).upper() != match.group(2).upper() and parent.OPTION_WORDS.search(match.group(0)):
            return True
    return False


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
