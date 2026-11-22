"""Run134 post-observation software-only composition of Run129 and Run133.

Never new native inference, runtime integration or canonical STEP2 promotion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import step2_exact_rule_native_replay_preflight as frozen
from scripts import step2_option_quote_consistency_candidate as quotes
from scripts import step2_project_identity_binding_candidate as projects
from scripts import step2_tool_replay as tool
from v13.common import digest, dumps, file_hash
from v13.utility import score_decision


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def replay(source, tool_raw):
    """Compose independently registered software candidates on frozen raw."""
    alias_original = projects.replay(source, tool_raw)
    quote_original = quotes.replay(source, tool_raw)
    need(alias_original["rows"] == 42
         and alias_original["canonical_gate_pass"] is False
         and quote_original["rows"] == 42
         and quote_original["treatment_wrong_committed"] == 0
         and quote_original["canonical_gate_pass"] is False,
         "PARENT_CANDIDATE_RED")
    fixtures = {f["id"]: f for f in source["fixtures"]}
    source_rows = {(r["fixture"], r["variant"]): r for r in source["rows"]}
    out = []
    for row in tool_raw["rows"]:
        key = (row["fixture"], row["variant"])
        src = source_rows[key]
        fixture = fixtures[row["fixture"]]
        need(source["row_sha256"][key[0] + ":" + key[1]] == digest(dumps(src))
             and tool_raw["row_sha256"][key[0] + ":" + key[1]] == digest(dumps(row))
             and row["oracle_visible_to_native"] is False
             and row["consumer_metrics"]["status"] == "FINAL"
             and row["status"] == "RECORDED", "ORIGINAL_ROW_DRIFT")
        need(score_decision(row["answer"], fixture["oracle"]) == row["score"],
             "ORIGINAL_SCORE_DRIFT")
        corrected_raw, quote_status, fields = quotes.repair(
            row["raw_answer"], src, fixture)
        answer, _trace = tool.tool_answer(corrected_raw, src["consumer_messages"])
        need(answer is not None, "COMPOSED_TOOL_ABSTAIN")
        bound, alias_status = projects.bind(answer, fixture["id"])
        before_binding = json.loads(answer, object_pairs_hook=projects.unique)
        after_binding = json.loads(bound, object_pairs_hook=projects.unique)
        need(before_binding["action"] == after_binding["action"]
             and before_binding["options"] == after_binding["options"],
             "PROJECT_BINDING_CHANGED_DECISION")
        action = after_binding["action"]
        wrong = action in ("A", "B", "NONE") and action != fixture["oracle"]["action"]
        score = score_decision(bound, fixture["oracle"])
        out.append({
            "fixture": key[0], "variant": key[1],
            "quote_status": quote_status, "quote_changed_fields": fields,
            "alias_status": alias_status, "action": action,
            "wrong_committed": wrong,
            "before_utility": row["score"]["utility"],
            "after_utility": score["utility"],
            "before_exact": row["score"]["exact"],
            "after_exact": score["exact"],
            "original_raw_unchanged": True,
        })
    need(len(out) == 42 and len({(r["fixture"], r["variant"]) for r in out}) == 42,
         "COMPOSED_COVERAGE_RED")
    per_variant = {}
    for variant in quotes.VARIANTS:
        subset = [r for r in out if r["variant"] == variant]
        need(len(subset) == len(quotes.PROJECTS), "VARIANT_INCOMPLETE")
        per_variant[variant] = {
            "rows": len(subset),
            "before_mean_utility": sum(r["before_utility"] for r in subset) / len(subset),
            "after_mean_utility": sum(r["after_utility"] for r in subset) / len(subset),
            "before_full_exact": sum(r["before_exact"] for r in subset),
            "after_full_exact": sum(r["after_exact"] for r in subset),
            "quote_changed_fields": sum(r["quote_changed_fields"] for r in subset),
            "alias_bound": sum(r["alias_status"] == "SOURCE_ID_LITERAL_PREFIX_BOUND" for r in subset),
            "wrong_committed": sum(r["wrong_committed"] for r in subset),
        }
    wrong = sum(r["wrong_committed"] for r in out)
    return {
        "schema": "v13.step2.composed_source_repairs_candidate.v1",
        "status": ("SOFTWARE_COMPOSED_WRONG_COMMITTED_RED" if wrong
                   else "SOFTWARE_COMPOSED_POST_OBSERVATION_NO_GATE"),
        "rows": len(out), "native_calls": 0,
        "original_source_sha256": frozen.ORIGINAL_SOURCE_SHA256,
        "original_tool_sha256": quotes.TOOL_SHA256,
        "quote_repaired_rows": sum(r["quote_changed_fields"] > 0 for r in out),
        "quote_repaired_fields": sum(r["quote_changed_fields"] for r in out),
        "project_aliases_bound": sum(r["alias_status"] == "SOURCE_ID_LITERAL_PREFIX_BOUND" for r in out),
        "full_exact_gained": sum(r["after_exact"] and not r["before_exact"] for r in out),
        "treatment_wrong_committed": wrong,
        "per_variant": per_variant, "rows_detail": out,
        "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False,
        "scope": "POST_OBSERVATION_OFFLINE_COMPOSITION_NOT_FRESH_NATIVE",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-report", type=Path, required=True)
    p.add_argument("--tool-report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    need(not args.out.exists(), "FRESH_OUTPUT_REQUIRED")
    source = frozen.load_original(args.source_report)
    need(file_hash(args.tool_report) == quotes.TOOL_SHA256, "ORIGINAL_TOOL_BYTES_DRIFT")
    report = replay(source, json.loads(args.tool_report.read_text(encoding="utf-8")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "status", "rows", "quote_repaired_rows", "quote_repaired_fields",
        "project_aliases_bound", "full_exact_gained", "treatment_wrong_committed",
        "canonical_gate_pass")}, sort_keys=True))
    return 0 if report["treatment_wrong_committed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
