"""Run140: source-verified B1/B2 deterministic eligibility control, no C3 calls.

Read-only, default-off and post-observation. This is a *control*, not a
claim that B1/B2 learned complementary representations or that C3 is optional.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts import step2_exact_rule_native_replay_preflight as frozen
from scripts import step2_option_quote_consistency_candidate as quotes
from v13.agi import eligibility as fixed
from v13.common import digest, dumps, file_hash
from v13.utility import score_decision


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def verified_source_quotes(source_row, fixture):
    """Use only hash-bound original source spans, never model hypotheses."""
    b1 = quotes.verified_b1_quotes(source_row, fixture)
    user = json.loads(source_row["consumer_messages"][1]["content"],
                      object_pairs_hook=quotes.unique)
    need(type(user) is dict and user.get("current_source") == fixture["current"],
         "CURRENT_SOURCE_DRIFT")
    analysts = user.get("analysts")
    need(type(analysts) is list, "ANALYST_SCHEMA_INVALID")
    b2_analysts = [a for a in analysts if a.get("role") == "B2_GIST"]
    need(len(b2_analysts) <= 1, "DUPLICATE_B2_ANALYST")
    spans = [e["text"] for e in source_row["source_evidence"]]
    b2 = []
    for analyst in b2_analysts:
        qlist = analyst.get("verified_quotes")
        need(type(qlist) is list, "B2_QUOTE_LIST_INVALID")
        for q in qlist:
            need(type(q) is str and bool(q) and any(q in s for s in spans),
                 "UNVERIFIED_B2_QUOTE")
            b2.append(q)
    return b1, b2


def decide_source_only(source_row, fixture):
    """Decision uses only verified source text, not the fixture oracle or C3."""
    b1, b2 = verified_source_quotes(source_row, fixture)
    exact = quotes.exact_options(b1)
    if exact is None:
        return {"status": "ABSTAIN_NO_UNAMBIGUOUS_B1_OPTIONS", "action": "UNKNOWN",
                "options": None, "b1_quotes": len(b1), "b2_quotes": len(b2),
                "rejected": ["options:unavailable"]}
    verified = [*b1, *b2]
    # The current task prompt names "Option A and Option B" but contains no
    # option values. fixed_read would select that incomplete first clause.
    # Read typed option/rule values from *verified source quotes*, then overlay
    # unambiguous current-source rules (newer than quotes). Never fabricate.
    values = fixed.fixed_read("", quotes=verified)
    need(values["options"] == [exact["A"], exact["B"]],
         "FIXED_READER_OPTION_DRIFT")
    rules = {k: values[k] for k in ("budget", "deadline", "local_only")}
    for key in rules:
        current = fixed.stated_values(key, fixture["current"])
        if current:
            rules[key] = next(iter(current)) if len(current) == 1 else None
    result = fixed.decide(rules, values["options"], fixture["current"], verified)
    return {
        "status": "SOURCE_ONLY_DECISION" if result["action"] != "UNKNOWN"
                  else "ABSTAIN_RULES_UNAVAILABLE",
        "action": result["action"], "options": result["options"],
        "b1_quotes": len(b1), "b2_quotes": len(b2),
        "rejected": result["rejected"],
    }


def replay(source, tool_raw):
    need(source.get("fixture_sha256") == frozen.ORIGINAL_FIXTURE_SHA256
         and source.get("canonical_gate_pass") is False
         and source.get("all_structural_checks_passed") is True
         and source.get("phone_measured") is False,
         "FROZEN_SOURCE_SCOPE_DRIFT")
    need(tool_raw.get("canonical_gate_pass") is False
         and tool_raw.get("phone_measured") is False
         and len(tool_raw.get("rows", [])) == 42,
         "FROZEN_TOOL_SCOPE_DRIFT")
    fixtures = {f["id"]: f for f in source["fixtures"]}
    need(tuple(fixtures) == frozen.PROJECTS, "FROZEN_FIXTURE_COVERAGE")
    rows = []
    for row in source["rows"]:
        key = row["fixture"] + ":" + row["variant"]
        need(source["row_sha256"].get(key) == digest(dumps(row)),
             "FROZEN_SOURCE_ROW_DRIFT:" + key)
        need(row.get("checks", {}).get("every_source_read_validated") is True,
             "UNVERIFIED_NATIVE_SOURCE:" + key)
        fixture = fixtures[row["fixture"]]
        # No oracle passed into the source-only decision path.
        result = decide_source_only(row, {k: fixture[k] for k in ("id", "current", "history")})
        action = result["action"]
        oracle = fixture["oracle"]  # evaluation ONLY, after decision is fixed
        wrong = action in ("A", "B", "NONE") and action != oracle["action"]
        exact = False
        utility = None
        if result["options"] is not None:
            answer = dumps({"project": fixture["id"], "action": action,
                            "options": result["options"]})
            score = score_decision(answer, oracle)
            exact, utility = score["exact"], score["utility"]
        rows.append({
            "fixture": row["fixture"], "variant": row["variant"],
            "status": result["status"], "action": action,
            "b1_quotes": result["b1_quotes"], "b2_quotes": result["b2_quotes"],
            "wrong_committed": wrong, "action_exact": action == oracle["action"],
            "trusted_identity_score_exact": exact,
            "trusted_identity_score_utility": utility,
        })
    need(len(rows) == 42 and len({(r["fixture"], r["variant"]) for r in rows}) == 42,
         "SOURCE_ONLY_COVERAGE_RED")
    per_variant = {}
    for variant in frozen.VARIANTS:
        sub = [r for r in rows if r["variant"] == variant]
        need(len(sub) == len(frozen.PROJECTS), "SOURCE_ONLY_VARIANT_MISSING")
        per_variant[variant] = {
            "rows": len(sub),
            "committed": sum(r["action"] in ("A", "B", "NONE") for r in sub),
            "action_exact": sum(r["action_exact"] for r in sub),
            "trusted_identity_score_exact": sum(r["trusted_identity_score_exact"] for r in sub),
            "abstained": sum(r["action"] == "UNKNOWN" for r in sub),
            "wrong_committed": sum(r["wrong_committed"] for r in sub),
        }
    return {
        "schema": "v13.step2.source_only_fusion_control.v1",
        "status": "POSTHOC_SOURCE_ONLY_CONTROL_NO_GATE",
        "rows": 42, "native_calls": 0, "new_model_inference": False,
        "original_source_sha256": frozen.ORIGINAL_SOURCE_SHA256,
        "original_tool_sha256": quotes.TOOL_SHA256,
        "per_variant": per_variant, "rows_detail": rows,
        "treatment_wrong_committed": sum(r["wrong_committed"] for r in rows),
        "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
        "jepa_weight": 0, "redmi_measured": False, "whole_system_complete": False,
        "scope": "POST_OBSERVATION_SOURCE_ONLY_CONTROL_NOT_FRESH_NATIVE",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-report", type=Path, required=True)
    p.add_argument("--tool-report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    need(not args.out.exists(), "FRESH_OUTPUT_REQUIRED")
    source = frozen.load_original(args.source_report)
    need(file_hash(args.tool_report) == quotes.TOOL_SHA256,
         "ORIGINAL_TOOL_BYTES_DRIFT")
    tool = json.loads(args.tool_report.read_text(encoding="utf-8"))
    report = replay(source, tool)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": report["rows"],
                      "per_variant": report["per_variant"],
                      "wrong_committed": report["treatment_wrong_committed"]},
                     sort_keys=True))
    return 0 if report["treatment_wrong_committed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
