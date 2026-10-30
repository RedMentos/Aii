"""Conservative source-exact stored FINAL arithmetic discrepancy diagnostic.

Read-only lexical SHADOW; no model, authority, learning or native execution proof.
"""
from __future__ import annotations
import re

MAX_OUTPUT_CHARS = 8192
_OPTION = re.compile(r"\bOption\s+([AB])\b", re.IGNORECASE | re.ASCII)
_NUM = r"(?<![\d.,])(-?(?:0|[1-9][0-9]{0,8}))(?![\d.,])"


def _claims(segment, unit):
    unit_pat = re.escape(unit)
    marker_before = re.compile(
        r"\b(?:leaves?|remaining(?:\s+budget)?|balance)\b[^0-9-]{0,32}"
        + _NUM + r"\s*" + unit_pat + r"\b", re.I | re.ASCII)
    marker_after = re.compile(
        _NUM + r"\s*" + unit_pat + r"\s*(?:left|remaining)\b",
        re.I | re.ASCII)
    values = set()
    for clause in re.split(r"[.;\n]", segment):
        values.update(int(m.group(1)) for m in marker_before.finditer(clause))
        values.update(int(m.group(1)) for m in marker_after.finditer(clause))
    return sorted(values)


def diagnose(arithmetic, text):
    """Audit only explicit option/unit-bound remainder claims, not semantics.

    Does not infer facts from costs, bare arithmetic, or unscoped numbers.
    An ambiguous shared unit is unsupported rather than guessed.
    """
    if type(text) is not str or len(text) > MAX_OUTPUT_CHARS:
        raise ValueError("FINAL_OUTPUT_SHAPE_RED")
    if (type(arithmetic) is not dict
            or type(arithmetic.get("fields")) is not list
            or len(arithmetic["fields"]) != 2
            or type(arithmetic.get("options")) is not dict
            or set(arithmetic["options"]) != {"A", "B"}):
        raise ValueError("SOURCE_ARITHMETIC_SHAPE_RED")
    fields = arithmetic["fields"]
    units = []
    for field in fields:
        if (type(field) is not dict or type(field.get("unit")) is not str
                or re.fullmatch(r"[A-Za-z]{1,20}", field["unit"]) is None):
            raise ValueError("SOURCE_UNIT_SHAPE_RED")
        units.append(field["unit"])
    ambiguous = units[0].casefold() == units[1].casefold()
    for name in "AB":
        option = arithmetic["options"][name]
        if (type(option) is not dict
                or type(option.get("remaining")) is not list
                or len(option["remaining"]) != 2
                or any(type(v) is not int for v in option["remaining"])):
            raise ValueError("SOURCE_REMAINDER_SHAPE_RED")
    segments = {"A": [], "B": []}
    matches = list(_OPTION.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        segments[m.group(1).upper()].append(text[m.end():end])
    result = {}
    for name in "AB":
        rows = []
        for i, unit in enumerate(units):
            expected = arithmetic["options"][name]["remaining"][i]
            claims = ([] if ambiguous else sorted(set(
                claim for segment in segments[name]
                for claim in _claims(segment, unit))))
            status = ("UNSUPPORTED" if ambiguous else
                      "MISSING" if not claims else
                      "CONTRADICTORY" if len(claims) > 1 else
                      "MATCH" if claims[0] == expected else "WRONG")
            rows.append({"field": fields[i].get("name"), "unit": unit,
                         "expected": expected, "claims": claims, "status": status})
        result[name] = rows
    statuses = [x["status"] for rows in result.values() for x in rows]
    overall = ("DISCREPANCY" if any(x in ("WRONG", "CONTRADICTORY") for x in statuses)
               else "MATCH" if all(x == "MATCH" for x in statuses)
               else "INCOMPLETE")
    return {"status": overall, "options": result,
            "scope": "LEXICAL_STORED_FINAL_SHADOW_ONLY",
            "no_live_answer": True, "native_execution_proven": False,
            "learning_authority": 0}
