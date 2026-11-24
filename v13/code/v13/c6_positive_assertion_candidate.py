"""Default-OFF C6 positive budget assertion guard (SHADOW, no delivery).

The existing C6 preflight only checks project/number *presence*. This adapter
requires a complete, affirmative, source-bound budget sentence. It is a
conservative lexical gate, NOT a semantic truth checker or TTY approval.
"""
from __future__ import annotations

import hashlib
import re

from .c6_temporal_draft_preflight_candidate import preflight_temporal_draft
from .f1f5_event_finalizer_candidate import _event_snapshot
from .f1f5_c5c6_atomic_draft_candidate import _locked_verified
from .source_consumer import BUDGET_VALUE, entities


def _result(status, **extra):
    return {"schema": "v13.c6_positive_assertion_shadow.v1",
            "status": status, "delivery_authority": 0,
            "output_committed": False, "tool_dispatches": 0,
            "learning_authority": 0, "native_proof": False, **extra}


def exact_positive_budget_assertion(candidate, source):
    """Only one supported affirmative assertion, with no appended claims.

    A rejection is not proof that a candidate is false. Other natural
    phrasings remain unsupported pending a separately measured grammar.
    """
    if type(candidate) is not str or type(source) is not dict:
        return False
    topic, value = source.get("topic"), source.get("value")
    if type(topic) is not str or type(value) is not str:
        return False
    names = entities(topic)
    if len(names) != 1 or BUDGET_VALUE.fullmatch(value) is None:
        return False
    project = re.escape(next(iter(names)))
    amount = re.escape(value.split(" ", 1)[0])
    currency = r"(?:Euro|EUR|€)"
    patterns = (
        rf"(?:Project|Projekt)\s+{project}\s+(?:budget|finanzrahmen|etat)\s+"
        rf"(?:is|ist|beträgt)\s+{amount}\s+{currency}\.",
        rf"The\s+budget\s+for\s+Project\s+{project}\s+is\s+"
        rf"{amount}\s+{currency}\.",
    )
    return any(re.fullmatch(p, candidate.strip(), re.IGNORECASE)
               is not None for p in patterns)


def preflight_positive_budget_assertion(cfg, memory, session, event_id, staged, *,
                                        operator_opt_in=False,
                                        approval_receipt=None):
    """Double-check read-only C6 and the bound DRAFT, never deliver.

    The two C6 checks bracket the extra lexical check. This is NOT an
    atomic output commit: a future C6 writer must repeat all checks within
    its own commit transaction and verify genuine human TTY consent.
    """
    if operator_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED")
    first = preflight_temporal_draft(
        cfg, memory, session, event_id, staged, operator_opt_in=True)
    if first.get("status") != "NEEDS_REAL_TTY_APPROVAL":
        return _result("BASE_PREFLIGHT_RED", base_status=first.get("status"))
    try:
        snapshot = _event_snapshot(memory, event_id, session)
        admitted = _locked_verified(memory, cfg, session, snapshot)
        if (admitted is None or type(staged) is not dict
                or admitted["source"]["memory_id"] != staged.get("source_memory_id")):
            return _result("SOURCE_CHANGED")
        row = memory.s.one(
            "SELECT text FROM messages WHERE id=? AND event_id=? "
            "AND session_id=? AND role='assistant' AND status='DRAFT'",
            (staged["draft_message_id"], event_id, session))
        if (row is None or hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
                != first.get("candidate_sha256")):
            return _result("DRAFT_CHANGED")
        if not exact_positive_budget_assertion(row["text"], admitted["source"]):
            return _result("POSITIVE_ASSERTION_RED", base_status=first["status"])
        second = preflight_temporal_draft(
            cfg, memory, session, event_id, staged, operator_opt_in=True)
        if (second.get("status") != "NEEDS_REAL_TTY_APPROVAL"
                or second.get("fingerprint_sha256") != first.get("fingerprint_sha256")
                or second.get("candidate_sha256") != first.get("candidate_sha256")):
            return _result("RECHECK_CHANGED")
        return _result("NEEDS_REAL_TTY_APPROVAL",
                       fingerprint_sha256=second["fingerprint_sha256"],
                       candidate_sha256=second["candidate_sha256"],
                       candidate_bytes=second["candidate_bytes"],
                       strict_positive_lexical_only=True,
                       preflight_only=True)
    except Exception:
        return _result("STRICT_PREFLIGHT_INTEGRITY_RED")
