"""Run184: conservative source arithmetic SHADOW candidate; not a live correction.

Independent of Run183's scorer. All inputs are untrusted and ambiguous text abstains.
Only an exact single-budget, two-option English fixture grammar is supported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

BUDGET = re.compile(r"\bbudget\s+(\d+)\s+euros\b", re.I)
COST = re.compile(r"\bOption\s+([AB]):\s+cost\s+(\d+)\s+euros\b", re.I)
EUROS = re.compile(r"\b\d+\s+euros\b", re.I)
OPTION = re.compile(r"\bOption\s+[AB]\b", re.I)
UNTRUSTED_CONTEXT = re.compile(r"\b(?:outdated|ignore|example|quoted|superseded|obsolete|invalid|instead|actually|fictional)\b", re.I)
OVERRIDE = "Updated rules, overriding the earlier rules:"


def _reject_duplicates(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError("duplicate JSON key")
        result[k] = v
    return result


def _reject_constant(value):
    raise ValueError(f"non-JSON numeric constant {value}")


def _ref(text, field, match):
    return {"field": field, "char_start": match.start(), "char_end": match.end(),
            "quote": text[match.start():match.end()],
            "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def _evidence(fixture):
    if not isinstance(fixture, dict):
        return None
    prior, current = fixture.get("prior"), fixture.get("current")
    if not isinstance(prior, str) or not isinstance(current, str):
        return None
    if len(prior) > 20000 or len(current) > 20000:
        return None
    if UNTRUSTED_CONTEXT.search(prior) or UNTRUSTED_CONTEXT.search(current):
        return None
    old, new = list(BUDGET.finditer(prior)), list(BUDGET.finditer(current))
    if len(new) == 1 and current.count(OVERRIDE) == 1 and not re.search(r"\bbudget\b", prior.replace(old[0].group(), "", 1) if len(old) == 1 else prior):
        selected, field, text = new[0], "current", current
    elif len(old) == 1 and not new and OVERRIDE not in current:
        selected, field, text = old[0], "prior", prior
    else:
        return None
    if len(list(EUROS.finditer(prior))) != len(old):
        return None
    costs = list(COST.finditer(current))
    if len(costs) != 2 or {m.group(1).upper() for m in costs} != {"A", "B"}:
        return None
    if len(list(OPTION.finditer(current))) != 2:
        return None
    if len(list(EUROS.finditer(current))) != len(costs) + len(new):
        return None
    # Every mention of "budget" must be the one exact supported declaration.
    for s, ms in ((prior, old), (current, new)):
        if len(re.findall(r"\bbudget\b", s, re.I)) != len(ms):
            return None
    budget = int(selected.group(1))
    options = {m.group(1).upper(): int(m.group(2)) for m in costs}
    refs = {"budget": _ref(text, field, selected),
            "options": {m.group(1).upper(): _ref(current, "current", m) for m in costs}}
    return budget, options, refs


def _answer(raw):
    if not isinstance(raw, str) or len(raw) > 20000:
        return None
    try:
        j = json.loads(raw, object_pairs_hook=_reject_duplicates, parse_constant=_reject_constant)
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    if not isinstance(j, dict) or set(j) != {"options"}:
        return None
    rows = j["options"]
    if not isinstance(rows, list) or len(rows) != 2:
        return None
    if any(not isinstance(x, dict) or set(x) != {"entity", "remaining"} for x in rows):
        return None
    if {x["entity"] for x in rows if isinstance(x["entity"], str)} != {"A", "B"}:
        return None
    if any(type(x["remaining"]) is not int for x in rows):
        return None
    return {x["entity"]: x["remaining"] for x in rows}


def check(fixture, raw):
    base = {"status": "ABSTAIN", "reason": "UNSUPPORTED_OR_AMBIGUOUS",
            "shadow_only": True, "delivery_authorized": False,
            "learning_authorized": False, "age_reopen_authorized": False}
    evidence, answer = _evidence(fixture), _answer(raw)
    if evidence is None or answer is None:
        return base
    budget, costs, refs = evidence
    mismatches = {key: {"expected": budget - costs[key], "actual": answer[key]}
                  for key in ("A", "B") if answer[key] != budget - costs[key]}
    return base | {"status": "SHADOW_ARITHMETIC_MISMATCH" if mismatches else "SHADOW_AGREES",
                   "reason": "SOURCE_BOUND_ARITHMETIC" if mismatches else "SOURCE_ARITHMETIC_AGREES",
                   "mismatches": mismatches, "source_refs": refs}


def cohort():
    """Deterministic software-only stress corpus, never native C3 evidence."""
    rows = []
    for i in range(40):
        budget, a, b = 200 + i * 3, 20 + i, 60 + i
        f = {"prior": f"Project P{i}. Budget {budget} euros.",
             "current": f"Option A: cost {a} euros. Option B: cost {b} euros."}
        good = {"options": [{"entity": "A", "remaining": budget - a},
                             {"entity": "B", "remaining": budget - b}]}
        bad = {"options": [{"entity": "A", "remaining": budget - a - 7},
                            {"entity": "B", "remaining": budget - b}]}
        rows.append({"kind": "correct", "fixture": f, "raw": json.dumps(good), "expected": "SHADOW_AGREES"})
        rows.append({"kind": "wrong", "fixture": f, "raw": json.dumps(bad), "expected": "SHADOW_ARITHMETIC_MISMATCH"})
    for i in range(20):
        f = {"prior": "Project P. Budget 100 euros.",
             "current": "Outdated example: Option A: cost 40 euros. Option B: cost 70 euros. "
                        "Correct costs are A=30 euros and B=60 euros."}
        raw = json.dumps({"options": [{"entity": "A", "remaining": 70},
                                        {"entity": "B", "remaining": 40}]})
        rows.append({"kind": "decoy", "fixture": f, "raw": raw, "expected": "ABSTAIN"})
        duplicate = '{"options":[{"entity":"A","remaining":60,"remaining":1},' \
                    '{"entity":"B","remaining":30}]}'
        clean = {"prior": "Project P. Budget 100 euros.",
                 "current": "Option A: cost 40 euros. Option B: cost 70 euros."}
        rows.append({"kind": "duplicate_json", "fixture": clean,
                     "raw": duplicate, "expected": "ABSTAIN"})
    return rows


def audit(rows):
    outcomes = []
    for i, item in enumerate(rows):
        result = check(item["fixture"], item["raw"])
        outcomes.append({"index": i, "kind": item["kind"], "expected": item["expected"],
                         "observed": result["status"], "ok": result["status"] == item["expected"],
                         "shadow_only": result["shadow_only"],
                         "delivery_authorized": result["delivery_authorized"]})
    counts = {k: sum(x["kind"] == k for x in outcomes) for k in
              ("correct", "wrong", "decoy", "duplicate_json")}
    failures = [x for x in outcomes if not x["ok"] or not x["shadow_only"] or x["delivery_authorized"]]
    return {"schema": "V13_RUN184_AGE0D_BALANCED_SOFTWARE_STRESS_V1",
            "evidence_class": "SYNTHETIC_SOFTWARE_ONLY", "rows": len(outcomes),
            "counts": counts, "failures": failures, "cases": outcomes,
            "verdict": "SOFTWARE_GUARD_PASS" if not failures else "SOFTWARE_GUARD_FAIL",
            "delivery_authorized": False, "step2_promoted": False, "b3_promoted": False,
            "body_jepa_available": False, "jepa_weight": 0, "v13_complete": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit(cohort())
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, sort_keys=True))
    return 0 if result["verdict"] == "SOFTWARE_GUARD_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
