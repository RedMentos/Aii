"""Run117CM default-OFF JEF/F1/F5 -> C3 source-only research envelope.

Unlike typed-JEF formatter controls, this candidate gives C3 the exact
source-verified policy, option sheet and current request, but NEVER the
fixed reader's computed action. It is prompt construction only: no native
call, no output/tool/learning authority, no claim of independent reasoning.
"""
from __future__ import annotations

import hashlib
import json

from .common import dumps
from .jef_f1f5_range_admission_shadow import decide as admit, READY
from .jef_typed_source_shadow import _read_full

STATUS = "JEF_C3_SOURCE_ONLY_SHADOW_NO_MODEL_CALL"
MAX_PAYLOAD_BYTES = 16384
SYSTEM = (
    "Experimental C3_LANGUAGE source-only rule decision. Read the human "
    "policy, option sheet and current request; apply every Minimum/Maximum "
    "bound and required boolean exactly. Of eligible options choose the "
    "lowest first numeric value, then lowest second numeric value, then A "
    "before B. If none qualifies choose NONE. Return only one JSON object "
    "with sole key action and value A, B or NONE. There is no precomputed "
    "typed JEF action in this prompt. Do not dispatch tools or invent facts."
)


def _sha(value):
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()


def _result(status, **extra):
    return {
        "schema": "v13.jef_c3_source_only_shadow.v1",
        "status": status,
        "authority": 0, "delivery_authority": 0,
        "learning_authority": 0, "tool_dispatches": 0,
        "model_called": False, "native_calls": 0,
        "output_committed": False, "real_tty_approved": False,
        "jepa_weight": 0, "whole_system_complete": False,
        "independent_reasoning_proven": False,
        "oracle_action_visible": False,
        **extra,
    }


def build(memory, session, event_id, current_ref, memory_ids, *,
          operator_opt_in=False, approval_receipt=None):
    if operator_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED")
    if (type(session) is not str or type(event_id) is not str
            or type(current_ref) is not dict
            or type(memory_ids) not in (list, tuple)
            or len(memory_ids) != 2
            or any(type(x) is not str or not x for x in memory_ids)
            or memory_ids[0] == memory_ids[1]):
        return _result("INVALID_SOURCE_INPUT")
    try:
        first = admit(memory, session, event_id, current_ref, memory_ids,
                      operator_opt_in=True)
        if (first.get("admission_status") != READY
                or first.get("human_source_lineage_verified") is not True
                or first.get("suggested_action") not in ("A", "B", "NONE")
                or first.get("authority") != 0
                or first.get("model_called") is not False):
            return _result("HUMAN_SOURCE_ADMISSION_RED",
                           admission_status=first.get("admission_status"))
        store = memory.s
        sources = {}
        refs = {}
        for mid in memory_ids:
            row = memory.candidate(mid, session)
            key = row["key_text"]
            kind = ("policy" if key.endswith(" policy") else
                    "sheet" if key.endswith(" option sheet") else None)
            if kind is None or kind in sources:
                return _result("SOURCE_ROLE_BINDING_RED")
            ref = row["source_ref"]
            sources[kind] = _read_full(store, ref)
            refs[kind] = ref
        if set(sources) != {"policy", "sheet"}:
            return _result("MISSING_SOURCE_ROLE_RED")
        ref_hashes = [_sha(refs["policy"]), _sha(refs["sheet"])]
        if first.get("source_ref_sha256") != ref_hashes:
            return _result("SOURCE_HASH_BINDING_RED")
        current = _read_full(store, current_ref)
        payload = {
            "task": "SOURCE_ONLY_INDEPENDENT_RULE_PROBE",
            "human_source_lineage_verified": True,
            "typed_jef_action_visible": False,
            "body_hypotheses_are_facts": False,
            "current": {"text": current, "source_ref_sha256": _sha(current_ref)},
            "policy": {"text": sources["policy"], "source_ref_sha256": ref_hashes[0]},
            "sheet": {"text": sources["sheet"], "source_ref_sha256": ref_hashes[1]},
        }
        encoded = dumps(payload)
        if len(encoded.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            return _result("SOURCE_ONLY_PAYLOAD_TOO_LARGE_RED")
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": encoded}]
        # Close the source window after construction. A changed/revoked
        # source must not yield a usable envelope, even for SHADOW use.
        second = admit(memory, session, event_id, current_ref, memory_ids,
                       operator_opt_in=True)
        if (second.get("admission_status") != READY
                or second.get("source_ref_sha256") != ref_hashes
                or second.get("suggested_action") != first["suggested_action"]
                or _read_full(store, current_ref) != current
                or _read_full(store, refs["policy"]) != sources["policy"]
                or _read_full(store, refs["sheet"]) != sources["sheet"]):
            return _result("SOURCE_CHANGED_DURING_COMPOSITION")
        return _result(
            STATUS, messages=messages, messages_sha256=_sha(messages),
            source_ref_sha256=ref_hashes,
            current_source_ref_sha256=_sha(current_ref),
            human_source_lineage_verified=True,
            source_only=True, prompt_only=True,
            formatter_only=False)
    except (ValueError, TypeError, KeyError, AttributeError,
            OSError, UnicodeError, OverflowError, json.JSONDecodeError):
        return _result("SOURCE_ONLY_INTEGRITY_RED")
