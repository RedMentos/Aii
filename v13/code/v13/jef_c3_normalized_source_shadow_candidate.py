"""Run117DE default-OFF C3 normalized human-source presentation, SHADOW only.

Converts exact source *data* into a worksheet, never computes or reveals the
JEF action/eligibility, never calls a model, dispatches, delivers or learns.
"""
from __future__ import annotations

import hashlib
import json
import re

from .common import dumps
from . import jef_c3_source_only_shadow_candidate as source

READY = "RUN117DE_NORMALIZED_SOURCE_ONLY_SHADOW_NO_MODEL_CALL"
SYSTEM = (source.SYSTEM + " The user JSON also includes a normalized source-data "
          "worksheet. Compare the threshold directions and both options yourself. "
          "The worksheet does not contain eligibility or a computed action. "
          "Use only human source values; return exactly the requested JSON action.")
MAX_PAYLOAD_BYTES = 16384


def _sha(value):
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()


def _result(status, **fields):
    return {
        "schema": "v13.run117de.c3_normalized_source_only_shadow.v1",
        "status": status, "authority": 0,
        "delivery_authority": 0, "learning_authority": 0,
        "tool_dispatches": 0, "model_called": False, "native_calls": 0,
        "output_committed": False, "real_tty_approved": False,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "native_proof": False, "redmi_measured": False,
        "whole_system_complete": False,
        "oracle_action_visible": False, "typed_jef_action_visible": False,
        "independent_reasoning_proven": False,
        **fields,
    }


def _epoch(store):
    return (store.db.total_changes,
            store.db.execute("PRAGMA data_version").fetchone()[0],
            store.one("SELECT COUNT(*) AS n FROM actions")["n"],
            store.one("SELECT COUNT(*) AS n FROM messages")["n"])


def _number(raw):
    n = int(raw)
    if n < 0 or n > 10000 or str(n) != raw:
        raise ValueError("RUN117DE_NONCANONICAL_NUMBER_RED")
    return n


def normalize(current, policy, sheet):
    """Strict full-span source parser. No eligibility, score or action field."""
    if any(type(s) is not str or not 0 < len(s.encode("utf-8")) <= 4096
           for s in (current, policy, sheet)):
        raise ValueError("RUN117DE_SOURCE_TYPE_OR_LENGTH_RED")
    c = re.fullmatch(
        r"Project ([A-Z0-9]{2,32})\. Choose Option A or Option B using the "
        r"archived ([a-z ]{2,80}) policy and latest option sheet\. "
        r"If neither qualifies, choose NONE\.", current)
    if c is None:
        raise ValueError("RUN117DE_CURRENT_GRAMMAR_RED")
    project, domain = c.groups()
    p = re.fullmatch(
        rf"Project {re.escape(project)} archived {re.escape(domain)} policy\. "
        r"(Minimum|Maximum) battery quota: ([0-9]{1,5}) units\. "
        r"(Minimum|Maximum) start window: ([0-9]{1,5}) ticks\. "
        r"Required sealed: (true|false)\.", policy)
    s = re.fullmatch(
        rf"Project {re.escape(project)} latest {re.escape(domain)} option sheet\. "
        r"Option A: battery quota ([0-9]{1,5}) units; "
        r"start window ([0-9]{1,5}) ticks; sealed (true|false)\. "
        r"Option B: battery quota ([0-9]{1,5}) units; "
        r"start window ([0-9]{1,5}) ticks; sealed (true|false)\.", sheet)
    if p is None or s is None:
        raise ValueError("RUN117DE_POLICY_OR_SHEET_GRAMMAR_RED")
    op1, threshold1, op2, threshold2, sealed = p.groups()
    a1, a2, ab, b1, b2, bb = s.groups()
    return {
        "project": project, "domain": domain,
        "policy": {
            "battery_quota": {"direction": op1, "threshold": _number(threshold1)},
            "start_window": {"direction": op2, "threshold": _number(threshold2)},
            "required_sealed": sealed == "true",
        },
        "options": {
            "A": {"battery_quota": _number(a1), "start_window": _number(a2),
                  "sealed": ab == "true"},
            "B": {"battery_quota": _number(b1), "start_window": _number(b2),
                  "sealed": bb == "true"},
        },
    }


def build(memory, session, event_id, current_ref, memory_ids, *,
          operator_opt_in=False, approval_receipt=None):
    if operator_opt_in is not True:
        return _result("OFF")
    if approval_receipt is not None:
        return _result("REAL_TTY_APPROVAL_UNSUPPORTED")
    try:
        before = source.build(memory, session, event_id, current_ref, memory_ids,
                              operator_opt_in=True)
        if (before.get("status") != source.STATUS
                or before.get("oracle_action_visible") is not False
                or before.get("model_called") is not False
                or before.get("delivery_authority") != 0
                or before.get("learning_authority") != 0):
            return _result("SOURCE_ADMISSION_RED", admission_status=before.get("status"))
        original = before["messages"]
        if ([m.get("role") for m in original] != ["system", "user"]
                or _sha(original) != before["messages_sha256"]):
            return _result("SOURCE_PROMPT_INTEGRITY_RED")
        payload = json.loads(original[1]["content"])
        if (type(payload) is not dict
                or payload.get("typed_jef_action_visible") is not False
                or any(k in payload for k in ("oracle", "expected_action", "suggested_action",
                                               "typed_jef_action", "eligibility", "ranked_action"))):
            return _result("ORACLE_LEAK_RED")
        epoch = _epoch(memory.s)
        worksheet = normalize(payload["current"]["text"], payload["policy"]["text"],
                              payload["sheet"]["text"])
        prepared = {
            "task": "SOURCE_ONLY_NORMALIZED_DATA_PROBE",
            "typed_jef_action_visible": False,
            "human_source_lineage_verified": True,
            "source": payload,
            "worksheet_without_eligibility_or_action": worksheet,
        }
        encoded = dumps(prepared)
        if len(encoded.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            return _result("NORMALIZED_PAYLOAD_TOO_LARGE_RED")
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": encoded}]
        after = source.build(memory, session, event_id, current_ref, memory_ids,
                             operator_opt_in=True)
        if (after.get("status") != source.STATUS
                or after.get("messages_sha256") != before["messages_sha256"]
                or after.get("source_ref_sha256") != before.get("source_ref_sha256")
                or after.get("current_source_ref_sha256") != before.get("current_source_ref_sha256")
                or _epoch(memory.s) != epoch):
            return _result("SOURCE_CHANGED_DURING_NORMALIZATION_RED")
        return _result(
            READY, messages=messages, messages_sha256=_sha(messages),
            original_messages_sha256=before["messages_sha256"],
            source_ref_sha256=before["source_ref_sha256"],
            current_source_ref_sha256=before["current_source_ref_sha256"],
            human_source_lineage_verified=True, source_only=True,
            prompt_only=True, normalized_data_only=True,
        )
    except (ValueError, TypeError, KeyError, AttributeError, OSError,
            UnicodeError, OverflowError, json.JSONDecodeError):
        return _result("SOURCE_NORMALIZATION_INTEGRITY_RED")
