"""Run73: deterministic mixed Minimum/Maximum JEF SourceRef reader (SHADOW).

Strictly additive fixed grammar. It is not F1/F5 human authorization, a
native model, an output path or a learning/age permission. No Store writes.
"""
from __future__ import annotations

import re

from . import jef_typed_source_shadow as fixed

REVISION = "jef-mixed-range-policy-shadow-run73-v1"
POLICY = re.compile(
    rf"Project (?P<id>{fixed.ID}) archived (?P<domain>{fixed.LABEL}) policy\\. "
    rf"(?P<op1>Minimum|Maximum) (?P<f1>{fixed.LABEL}): (?P<m1>{fixed.NUM}) (?P<u1>{fixed.UNIT})\\. "
    rf"(?P<op2>Minimum|Maximum) (?P<f2>{fixed.LABEL}): (?P<m2>{fixed.NUM}) (?P<u2>{fixed.UNIT})\\. "
    rf"Required (?P<flag>{fixed.LABEL}): (?P<required>true|false)\\.",
    re.ASCII,
)


def _result(action, reason, refs=()):
    return {
        **fixed._result(action, reason, refs),
        "revision": REVISION,
        "fixed_range_parser": True,
        "human_source_lineage_verified": False,
        "delivery_authority": 0,
        "learning_authority": 0,
        "native_proof": False,
        "output_committed": False,
        "real_tty_approved": False,
    }


def _qualifies(option, policy):
    for i in (1, 2):
        bound = int(policy["m" + str(i)])
        value = option[i - 1]
        if policy["op" + str(i)] == "Minimum":
            if value < bound:
                return False
        elif policy["op" + str(i)] == "Maximum":
            if value > bound:
                return False
        else:
            raise ValueError("UNKNOWN_RANGE_OPERATOR")
    return policy["required"] == "false" or option[2]


def decide(store, current_ref, source_refs, *, operator_opt_in=False):
    """Return source-verified deterministic SHADOW proposal, never permission.

    A successful source hash proves the bytes, not that the operator approved
    them. A later F1/F5 consumer must independently verify human lineage.
    """
    if operator_opt_in is not True:
        return _result("UNKNOWN", "OFF")
    try:
        current = fixed._read_full(store, current_ref)
        request = fixed.CURRENT.fullmatch(current)
        if request is None:
            return _result("UNKNOWN", "CURRENT_GRAMMAR_RED")
        if (type(source_refs) not in (tuple, list) or len(source_refs) != 2
                or fixed._canonical(source_refs[0]) == fixed._canonical(source_refs[1])):
            return _result("UNKNOWN", "EXACT_DISTINCT_TWO_SOURCES_REQUIRED")
        texts = [fixed._read_full(store, ref) for ref in source_refs]
        policies = [POLICY.fullmatch(text) for text in texts]
        sheets = [fixed.SHEET.fullmatch(text) for text in texts]
        if (sum(match is not None for match in policies) != 1
                or sum(match is not None for match in sheets) != 1):
            return _result("UNKNOWN", "POLICY_SHEET_GRAMMAR_RED")
        policy = next(match.groupdict() for match in policies if match is not None)
        sheet = next(match.groupdict() for match in sheets if match is not None)
        if (policy["id"] != request["id"] or sheet["id"] != request["id"]
                or policy["domain"] != request["domain"]
                or sheet["domain"] != request["domain"]):
            return _result("UNKNOWN", "PROJECT_DOMAIN_MISMATCH_RED")
        if (policy["f1"] == policy["f2"]
                or policy["flag"] in (policy["f1"], policy["f2"])):
            return _result("UNKNOWN", "AMBIGUOUS_FIELD_RED")
        options = [fixed._option(sheet[name], policy) for name in ("a", "b")]
        eligible = [(option[0], option[1], name)
                    for option, name in zip(options, ("A", "B"))
                    if _qualifies(option, policy)]
        action = min(eligible)[2] if eligible else "NONE"
        return _result(action, "FULL_SOURCE_FIXED_RANGE_DECISION", source_refs)
    except (KeyError, ValueError, TypeError, OSError, UnicodeError,
            AttributeError, OverflowError):
        return _result("UNKNOWN", "SOURCE_INTEGRITY_OR_GRAMMAR_RED")
