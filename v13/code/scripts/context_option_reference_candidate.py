"""Run141 default-off Context OS candidate: pure option-reference fallback.

Source-only deterministic reader. A bare "Option A and Option B" task
reference may fall through to older exact source; partial/ambiguous updates
must not. The upstream Store is responsible for source authentication.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts import step2_exact_rule_native_replay_preflight as frozen
from v13.agi import eligibility as original


OPTION_WORDS = re.compile(r"\b(?:cost|duration|days?|local)\b|\d", re.I)
PAIR = re.compile(r"\bOption\s+A\s+(?:and|or)\s+Option\s+B\b", re.I)


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def _clauses(entity, text):
    return re.finditer(r"\boption\s+" + re.escape(entity) + r"\b[^.]*", text, re.I)


def _parse(entity, clause):
    fields = [re.findall(pattern, clause, re.I) for pattern in original._OPT_VALUES]
    if all(len(set(values)) == 1 and values for values in fields):
        return {"entity": entity, "cost": int(fields[0][0]),
                "days": int(fields[1][0]),
                "local": fields[2][0].lower() == "true"}
    return None


def _from_text(entity, text):
    clauses = list(_clauses(entity, text))
    if not clauses:
        return "ABSENT", None
    complete = []
    for match in clauses:
        clause = match.group(0)
        parsed = _parse(entity, clause)
        if parsed is not None:
            complete.append(parsed)
            continue
        # A reference without any typed field is only skippable when it
        # explicitly names the A/B pair. Numeric/partial updates block.
        if OPTION_WORDS.search(clause) or not any(
            p.start() <= match.start() < p.end() for p in PAIR.finditer(text)
        ):
            return "BLOCKED_PARTIAL", None
    if complete:
        keys = {(x["cost"], x["days"], x["local"]) for x in complete}
        if len(keys) != 1:
            return "BLOCKED_CONFLICT", None
        return "COMPLETE", complete[0]
    return "PURE_PAIR_REFERENCE", None


def option_with_reference_fallback(entity, current, earlier=()):
    """Newest exact source wins; only pure pair references may be skipped."""
    if entity not in ("A", "B") or type(current) is not str or type(earlier) not in (list, tuple) or any(
        type(x) is not str for x in earlier
    ):
        raise ValueError("OPTION_SOURCE_INPUT_INVALID")
    for text in (current, *reversed(earlier)):
        status, value = _from_text(entity, text)
        if status == "COMPLETE":
            return value
        if status in ("BLOCKED_PARTIAL", "BLOCKED_CONFLICT"):
            return None
    return None


def read_fixed_reference(current, earlier=()):
    """Same READ_SCHEMA shape as read_fixed; no model, no oracle."""
    if type(current) is not str or type(earlier) not in (list, tuple) or any(
        type(x) is not str for x in earlier
    ):
        raise ValueError("OPTION_SOURCE_INPUT_INVALID")
    out = {key: original.fixed_rule(key, current, earlier)
           for key in ("budget", "deadline", "local_only")}
    options = [option_with_reference_fallback(entity, current, earlier)
               for entity in ("A", "B")]
    out["options"] = options if all(o is not None for o in options) else None
    return out


def replay_upper_bound(source):
    """Full-history deterministic upper bound; not a B2-limited native control."""
    need(source.get("fixture_sha256") == frozen.ORIGINAL_FIXTURE_SHA256
         and source.get("all_structural_checks_passed") is True
         and source.get("canonical_gate_pass") is False,
         "FROZEN_SOURCE_SCOPE_DRIFT")
    rows = []
    for fixture in source["fixtures"]:
        values = read_fixed_reference(fixture["current"], fixture["history"])
        if values["options"] is None:
            action = "UNKNOWN"
        else:
            action = original.decide(
                {k: values[k] for k in ("budget", "deadline", "local_only")},
                values["options"], fixture["current"], fixture["history"]
            )["action"]
        # Oracle is accessed only after the deterministic prediction.
        oracle_action = fixture["oracle"]["action"]
        rows.append({"fixture": fixture["id"], "action": action,
                     "action_exact": action == oracle_action,
                     "wrong_committed": action in ("A", "B", "NONE")
                     and action != oracle_action,
                     "options_available": values["options"] is not None,
                     "rules_complete": all(values[k] is not None for k in
                                           ("budget", "deadline", "local_only"))})
    need(len(rows) == 6 and tuple(x["fixture"] for x in rows) == frozen.PROJECTS,
         "UPPER_BOUND_FIXTURE_COVERAGE_RED")
    return {
        "schema": "v13.context_option_reference_upper_bound.v1",
        "status": "POSTHOC_FULL_HISTORY_DETERMINISTIC_UPPER_BOUND_NO_GATE",
        "rows": 6, "native_calls": 0,
        "action_exact": sum(r["action_exact"] for r in rows),
        "wrong_committed": sum(r["wrong_committed"] for r in rows),
        "rows_detail": rows,
        "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False,
        "scope": "FULL_SOURCE_HISTORY_UPPER_BOUND_NOT_B2_LIMITED_NOT_NATIVE",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    need(not a.out.exists(), "FRESH_OUTPUT_REQUIRED")
    source = frozen.load_original(a.source_report)
    report = replay_upper_bound(source)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "rows", "action_exact",
                                            "wrong_committed", "canonical_gate_pass")},
                     sort_keys=True))
    return 0 if report["wrong_committed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
