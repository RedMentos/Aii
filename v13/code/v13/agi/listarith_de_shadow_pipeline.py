"""Unwired German typed-list arithmetic candidate (SHADOW_ONLY).

Consumes caller-supplied C3 JSON; never invokes a model, ToolStep, C5 or
external action. Native provenance must be verified by the caller separately.
"""
from __future__ import annotations

import hashlib
import json
import re
from . import listarith
from . import listarith_de_shadow_v2_candidate as german

AUTHORITY = "SHADOW_ONLY"
REVISION = "de-typed-list-shadow-pipeline-20261030-v1"
MAX_RAW_BYTES = 8192


class UnsafeRead(ValueError):
    """An untrusted read cannot safely be turned into an arithmetic result."""


def _no_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise UnsafeRead("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _reject_constant(value):
    raise UnsafeRead("NONFINITE_JSON_NUMBER")


def parse_typed(raw):
    """Strict JSON reader: no duplicate keys, floats, bools or extra fields."""
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_RAW_BYTES:
        raise UnsafeRead("RAW_INVALID_OR_TOO_LARGE")
    try:
        obj = json.loads(raw, object_pairs_hook=_no_duplicate_keys,
                         parse_constant=_reject_constant)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise UnsafeRead("INVALID_JSON") from exc
    if not isinstance(obj, dict) or set(obj) != {"values"} or not isinstance(obj["values"], list):
        raise UnsafeRead("INVALID_VALUES_SCHEMA")
    values = obj["values"]
    if not 2 <= len(values) <= 8:
        raise UnsafeRead("INVALID_VALUE_COUNT")
    normalized = []
    for item in values:
        if (not isinstance(item, dict) or set(item) != {"name", "number"}
                or not isinstance(item["name"], str)
                or not item["name"].strip()
                or len(item["name"]) > 40
                or type(item["number"]) is not int):
            raise UnsafeRead("INVALID_ITEM_SCHEMA")
        name = item["name"].strip()
        if listarith.AGGREGATE.fullmatch(name):
            raise UnsafeRead("AGGREGATE_AS_INPUT")
        normalized.append({"name": name, "number": item["number"]})
    return normalized


def _pair_spans(text, item):
    """Find exact adjacent name/number evidence; never infer missing pairs.

    This intentionally supports a small, conservative syntax family only.
    An intervening unrelated label (e.g. 'Temperaturen: Morgen -3' read as
    'Temperaturen=-3') does not count as a source-bound item.
    """
    name = re.escape(item["name"])
    n = str(item["number"])
    sign = r"(?:-|\u2212)" if n.startswith("-") else r"\+?"
    digits = re.escape(n.lstrip("-"))
    pattern = (r"(?<![\w-])" + name + r"(?![\w-])"
               + r"[ \t\r\n]*[:=]?[ \t\r\n]*"
               + r"(?:kostet[ \t]+)?\(?[ \t]*"
               + sign + digits + r"(?![\d.,])")
    return [(m.start(), m.end()) for m in re.finditer(pattern, text, re.IGNORECASE)]


def verify_name_number_bindings(text, values):
    """Require a distinct exact text span for every extracted name/number."""
    if not isinstance(text, str) or not text.strip() or len(text) > listarith.MAX_TEXT:
        raise UnsafeRead("SOURCE_INVALID_OR_TOO_LARGE")
    candidates = [_pair_spans(text, item) for item in values]
    if any(not spans for spans in candidates):
        raise UnsafeRead("NAME_NUMBER_NOT_ADJACENT")
    # Small maximum (8 items): exact bipartite matching, no span reuse.
    order = sorted(range(len(values)), key=lambda i: len(candidates[i]))

    def assign(pos, used):
        if pos == len(order):
            return True
        for span in candidates[order[pos]]:
            if span not in used and assign(pos + 1, used | {span}):
                return True
        return False

    if not assign(0, set()):
        raise UnsafeRead("SOURCE_SPAN_REUSED")
    return True


def evaluate(text, raw_json):
    """Non-authoritative deterministic proposal, or a fail-closed abstention."""
    result = {"status": "SHADOW_ABSTAIN", "authority": AUTHORITY,
              "revision": REVISION, "operation": None, "value": None,
              "live_tool_execution": False, "external_action_authority": False,
              "native_provenance": "CALLER_MUST_VERIFY",
              "step2_gate_promoted": False, "b3_promoted": False,
              "body_jepa_available": False, "jepa_weight": 0,
              "redmi_measured": False, "whole_system_complete": False}
    if not isinstance(text, str):
        result["reason"] = "SOURCE_INVALID_OR_TOO_LARGE"
        return result
    result["source_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    try:
        proposal = german.propose(text)
        if proposal.get("authority") != AUTHORITY or proposal.get("proposal") not in (
                "total", "difference_max_min"):
            raise UnsafeRead("OPERATION_" + str(proposal.get("reason", "UNSUPPORTED")))
        values = parse_typed(raw_json)
        verify_name_number_bindings(text, values)
        value, recipe = listarith.compute(proposal["proposal"], values, text)
    except (UnsafeRead, ValueError, TypeError, KeyError, OverflowError) as exc:
        result["reason"] = str(exc)[:120]
        return result
    result.update(status="SHADOW_RESULT", reason="SOURCE_BOUND_DETERMINISTIC",
                  operation=proposal["proposal"], value=value, recipe=recipe,
                  input_count=len(values),
                  raw_sha256=hashlib.sha256(raw_json.encode("utf-8")).hexdigest())
    return result
