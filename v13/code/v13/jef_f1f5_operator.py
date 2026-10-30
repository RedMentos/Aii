"""Explicit local operator read-only JEF F1/F5 SHADOW diagnostic; no live answer."""
import json
import re

from .common import dumps
from . import jef_f1f5_source_admission as admission

EVENT = re.compile(r"evt_[a-f0-9]{28,32}\Z", re.ASCII)
MEMORY = re.compile(r"mem_[a-f0-9]{28,32}\Z", re.ASCII)


def _admitted(result):
    arithmetic = result.get("source_exact_arithmetic")
    return (
        result.get("status") == "SHADOW_NO_AUTHORITY"
        and result.get("admission_status") == "F1F5_SESSION_VERIFIED_SHADOW"
        and result.get("human_source_lineage_verified") is True
        and result.get("authority") == 0
        and result.get("user_approved") is False
        and type(arithmetic) is dict
        and arithmetic.get("evidence_level") == "STORE_INTEGRITY_ONLY"
        and arithmetic.get("mode") == "SHADOW_NO_AUTHORITY"
        and type(result.get("source_ref_sha256")) is list
        and len(result["source_ref_sha256"]) == 2
    )


def _render_explanation(arithmetic, action):
    """Human-readable exact-source arithmetic; never invoke a language model."""
    parts = [f'Project {arithmetic["project"]} ({arithmetic["domain"]}).']
    for name in ("A", "B"):
        option = arithmetic["options"][name]
        fields = []
        for i, field in enumerate(arithmetic["fields"]):
            unit = field["unit"]
            fields.append(
                f'{field["name"]}: {field["limit"]} {unit} - '
                f'{option["used"][i]} {unit} = '
                f'{option["remaining"][i]} {unit} remaining')
        parts.append(
            f'Option {name}: ' + "; ".join(fields)
            + f'; flag {str(option["flag"]).lower()}'
            + f'; eligible {str(option["eligible"]).lower()}.')
    parts.append("Suggested action: " + action + ".")
    return " ".join(parts)


def operator_command(r, args):
    explain = len(args) == 4 and args[0] == "explain"
    audit = len(args) == 4 and args[0] == "audit"
    ids = args[1:] if (explain or audit) else args
    if (len(ids) != 3 or EVENT.fullmatch(ids[0]) is None
            or any(MEMORY.fullmatch(mid) is None for mid in ids[1:])):
        raise ValueError(
            ":jefsource [explain|audit] <Event-ID> <PolicyMemory-ID> "
            "<SheetMemory-ID> (SHADOW only)")
    cfg = r.cfg
    if (cfg.get("system_stage") != 0
            or cfg.get("learning_mode") != "RECORD_ONLY"
            or cfg.get("latents_enabled") is not False
            or cfg.get("jepa_weight", 0) != 0):
        raise ValueError("AGE0_RECORD_ONLY_REQUIRED")
    r.require_idle()
    event_id, policy_id, sheet_id = ids
    row = r.store.one(
        "SELECT packet FROM events WHERE id=? AND session_id=?",
        (event_id, r.session))
    if row is None:
        raise ValueError("CURRENT_SESSION_EVENT_REQUIRED")
    try:
        envelope = json.loads(row["packet"])
        current_ref = envelope["source_ref"]
    except (ValueError, TypeError, KeyError):
        raise ValueError("AUTHORITATIVE_CURRENT_EVENT_REF_REQUIRED") from None
    result = admission.decide(r.memory, r.session, event_id,
                              current_ref, [policy_id, sheet_id])
    explanation = None
    explanation_status = "SOURCE_NOT_ADMITTED"
    if explain and _admitted(result):
        # A second full human F1/F5 lineage check narrows the revocation
        # window. It is not an atomic authorization or a live answer.
        first = result
        result = admission.decide(r.memory, r.session, event_id,
                                  current_ref, [policy_id, sheet_id])
        if (_admitted(result)
                and result["source_ref_sha256"] == first["source_ref_sha256"]
                and result["suggested_action"] == first["suggested_action"]
                and result["source_exact_arithmetic"]
                    == first["source_exact_arithmetic"]):
            explanation = _render_explanation(
                result["source_exact_arithmetic"], result["suggested_action"])
            explanation_status = "F1F5_SOURCE_EXACT_SHADOW_ONLY"
        else:
            result = {
                **result, "suggested_action": "UNKNOWN",
                "source_exact_arithmetic": None,
            }
    audit_result = None
    audit_status = "SOURCE_NOT_ADMITTED"
    if audit and _admitted(result):
        # A stored assistant FINAL is evidence of delivery, not a native
        # model proof. Require exactly one FINAL from the same event/session.
        query = (
            "SELECT id,text FROM messages WHERE session_id=? AND event_id=? "
            "AND role='assistant' AND status='FINAL' ORDER BY id DESC LIMIT 2"
        )
        first_rows = r.store.rows(query, (r.session, event_id))
        if len(first_rows) != 1:
            audit_status = "NO_SINGLE_CURRENT_FINAL"
        else:
            first = result
            snapshot = [(row["id"], row["text"]) for row in first_rows]
            result = admission.decide(r.memory, r.session, event_id,
                                      current_ref, [policy_id, sheet_id])
            if (_admitted(result)
                    and result["source_ref_sha256"] == first["source_ref_sha256"]
                    and result["suggested_action"] == first["suggested_action"]
                    and result["source_exact_arithmetic"]
                        == first["source_exact_arithmetic"]):
                again = r.store.rows(query, (r.session, event_id))
                if [(row["id"], row["text"]) for row in again] != snapshot:
                    audit_status = "FINAL_CHANGED"
                else:
                    from . import jef_f1f5_output_audit as final_audit
                    try:
                        audit_result = final_audit.diagnose(
                            result["source_exact_arithmetic"], snapshot[0][1])
                        audit_status = "F1F5_STORED_FINAL_SHADOW_ONLY"
                    except (ValueError, TypeError, KeyError, OverflowError):
                        audit_status = "UNSUPPORTED_FINAL"
            else:
                result = {
                    **result, "suggested_action": "UNKNOWN",
                    "source_exact_arithmetic": None,
                }
                audit_status = "SOURCE_NOT_ADMITTED"
    payload = {
        **result, "operator_diagnostic": True,
        "no_live_answer": True, "age0_record_only": True,
        "model_called": False, "native_calls": 0,
        "weight_updates": False, "jepa_weight": 0,
        "ag6_approved": False, "whole_system_complete": False,
    }
    if explain:
        payload["source_exact_explanation"] = explanation
        payload["explanation_status"] = explanation_status
    if audit:
        payload["stored_final_audit"] = audit_result
        payload["audit_status"] = audit_status
        payload["native_execution_proven_here"] = False
    return dumps(payload)
