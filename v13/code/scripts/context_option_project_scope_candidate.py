"""Default-off Context OS review: prevent cross-project history leakage.

Only exact explicit single-token 'Project NAME.' or 'Project NAME:' labels
scope historical source. Missing/ambiguous identity never authorizes fallback.
This does not authenticate source; the upstream Store must do so.
"""
from __future__ import annotations

import re

from scripts import context_option_reference_candidate as parent


# Canonical exact source uses both "Project Atlas." and bounded headers
# such as "Project Atlas supplier data sheet". Do not guess arbitrary
# multiword project names; unsupported header continuations abstain.
TAIL = r"(?:\s*[.:;]|\s+(?:kickoff|supplier|status|revision|rules|notes|brief|policy|update)\b)"
LABEL = re.compile(r"\bproject\s+([A-Za-z][A-Za-z0-9_-]{0,63})(?=" + TAIL + r")", re.I)
HEADER = re.compile(r"^\s*project\s+([A-Za-z][A-Za-z0-9_-]{0,63})(?=" + TAIL + r")", re.I)
AMBIGUOUS = object()


def project_key(source):
    if type(source) is not str:
        raise ValueError("PROJECT_SCOPE_SOURCE_INVALID")
    names = {m.group(1).casefold() for m in LABEL.finditer(source)}
    if len(names) > 1:
        return AMBIGUOUS
    # A later mention may be a quotation about a different project. Only
    # the explicit leading project header establishes historical scope.
    header = HEADER.match(source)
    return header.group(1).casefold() if header else None


def read_project_scoped(current, earlier=()):
    """Return Run141 READ_SCHEMA shape, but only from same-project exact history."""
    if type(current) is not str or type(earlier) not in (tuple, list) or any(
        type(x) is not str for x in earlier
    ):
        raise ValueError("PROJECT_SCOPE_SOURCE_INVALID")
    key = project_key(current)
    if key is AMBIGUOUS:
        return {"budget": None, "deadline": None, "local_only": None, "options": None}
    # No current identity: local complete values are allowed; borrowing any
    # historical values is not, because they cannot be attributed to this task.
    matched = [] if key is None else [
        source for source in earlier if project_key(source) == key
    ]
    return parent.read_fixed_reference(current, matched)
