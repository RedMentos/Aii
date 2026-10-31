"""Default-OFF source-bound C6 budget-language v2; read-only SHADOW.

Narrow lexical expansion over v1. Never grants output/TTY/tool/learning authority.
The C6 temporal source, action, DRAFT and egress preflight remains mandatory.
"""
from __future__ import annotations

import hashlib
import re

from .c6_temporal_draft_preflight_candidate import preflight_temporal_draft
from .f1f5_event_finalizer_candidate import _event_snapshot
from .f1f5_c5c6_atomic_draft_candidate import _locked_verified
from .source_consumer import BUDGET_VALUE, entities


def _result(status, **extra):
    return {"schema": "v13.c6_budget_lexical_v2_shadow.v1",
            "status": status, "delivery_authority": 0,
            "output_committed": False, "tool_dispatches": 0,
            "learning_authority": 0, "native_proof": False, **extra}


def exact_positive_budget_v2(candidate, source):
    """Accept only one complete, positive source-bound budget sentence.

    This is a deliberately bounded lexical grammar, not a truth model. An
    unsupported paraphrase is rejected, not assumed false. Neither model
    hypotheses nor the candidate itself may supply the expected fact.
    """
    if (type(candidate) is not str or type(source) is not dict
            or not 0 < len(candidate) <= 240
            or any(c in candidate for c in "\r\n\t\x00")):
        return False
    topic, value = source.get("topic"), source.get("value")
    if type(topic) is not str or type(value) is not str:
        return False
    names = entities(topic)
    if len(names) != 1 or BUDGET_VALUE.fullmatch(value) is None:
        return False
    name = re.escape(next(iter(names)))
    amount = re.escape(value.split(" ", 1)[0])
    currency = r"(?:Euros|Euro|EUR|€)"
    patterns = (
        rf"Project {name} budget is {amount} {currency}\.",
        rf"The budget for Project {name} is {amount} {currency}\.",
        rf"The project budget for Project {name} is {amount} {currency}\.",
        rf"Project {name}'s budget is €{amount}\.",
        rf"The budget for Project {name} is €{amount}\.",
        rf"Projekt {name} Budget beträgt {amount} (?:Euro|EUR|€)\.",
    )
    return any(re.fullmatch(p, candidate.strip(), re.IGNORECASE) is not None
               for p in patterns)


def preflight_budget_lexical_v2(cfg, memory, session, event_id, staged, *,
                                operator_opt_in=False, approval_receipt=None):
    """Read-only C6 recheck of exact staged source and candidate, no approval.

    This is not an atomic output writer. A future delivery transaction must
    revalidate all source, consent and age gates independently under its lock.
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
        with memory.s.tx():
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
            if not exact_positive_budget_v2(row["text"], admitted["source"]):
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
                       bounded_lexical_v2_only=True,
                       preflight_only=True)
    except Exception:
        return _result("STRICT_PREFLIGHT_INTEGRITY_RED")
