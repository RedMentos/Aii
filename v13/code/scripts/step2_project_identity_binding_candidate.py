"""Run129 strict source-bound project alias diagnostic, never native or runtime.

Read-only historical replay: normalize ONLY literal 'Project <trusted ID>' to
the exact hash-bound source fixture ID. No action/options/eligibility changes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from v13.common import digest, dumps, file_hash
from v13.utility import score_decision
from scripts import step2_exact_rule_native_replay_preflight as frozen

TOOL_SHA256 = "e90c23fd909dc0e138312f6802a05a3377f451f6675a496c1d4b1f1b19847ac0"
PROJECTS = frozen.PROJECTS
VARIANTS = frozen.VARIANTS


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def unique(pairs):
    obj = {}
    for k, v in pairs:
        need(k not in obj, "DUPLICATE_JSON_KEY")
        obj[k] = v
    return obj


def bind(raw_answer, trusted_project):
    """Return (new answer, tag), refusing foreign or ambiguous identities."""
    need(type(trusted_project) is str and trusted_project in PROJECTS,
         "UNTRUSTED_SOURCE_PROJECT")
    need(isinstance(raw_answer, str), "INVALID_ANSWER_TYPE")
    try:
        obj = json.loads(raw_answer, object_pairs_hook=unique)
    except (ValueError, TypeError) as exc:
        raise ValueError("INVALID_ANSWER_JSON") from exc
    need(isinstance(obj, dict) and set(obj) == {"project", "action", "options"}
         and type(obj["project"]) is str and type(obj["action"]) is str
         and isinstance(obj["options"], list), "INVALID_ANSWER_SCHEMA")
    if obj["project"] == trusted_project:
        return raw_answer, "SOURCE_ID_EXACT_UNCHANGED"
    need(obj["project"] == "Project " + trusted_project, "IDENTITY_CONFLICT")
    obj["project"] = trusted_project
    return dumps(obj), "SOURCE_ID_LITERAL_PREFIX_BOUND"


def replay(source, tool_raw):
    need(source.get("fixture_sha256") == frozen.ORIGINAL_FIXTURE_SHA256
         and source.get("installed_artifacts", {}).get("model_sha256") == {
             "B1_DETAIL": "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1",
             "B2_GIST": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
             "C3_LANGUAGE": "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d",
         }, "SOURCE_MODEL_OR_FIXTURE_DRIFT")
    fixtures = source.get("fixtures")
    need(isinstance(fixtures, list)
         and tuple(f["id"] for f in fixtures) == PROJECTS, "SOURCE_FIXTURE_COVERAGE_RED")
    oracles = {f["id"]: f["oracle"] for f in fixtures}
    rows = tool_raw.get("rows")
    need(isinstance(rows, list) and len(rows) == 42
         and {(r.get("fixture"), r.get("variant")) for r in rows}
         == {(p, v) for p in PROJECTS for v in VARIANTS}
         and tool_raw.get("canonical_gate_pass") is False
         and tool_raw.get("phone_measured") is False, "FROZEN_TOOL_COVERAGE_RED")
    need(isinstance(tool_raw.get("row_sha256"), dict)
         and len(tool_raw["row_sha256"]) == 42, "TOOL_HASH_COUNT_RED")
    out = []
    for row in rows:
        key = row["fixture"] + ":" + row["variant"]
        need(tool_raw["row_sha256"].get(key) == digest(dumps(row))
             and row.get("status") == "RECORDED"
             and row.get("oracle_visible_to_native") is False
             and row.get("consumer_metrics", {}).get("status") == "FINAL",
             "FROZEN_NATIVE_ROW_DRIFT:" + key)
        before = score_decision(row["answer"], oracles[row["fixture"]])
        need(before == row["score"], "ORIGINAL_SCORE_DRIFT:" + key)
        changed, tag = bind(row["answer"], row["fixture"])
        after = score_decision(changed, oracles[row["fixture"]])
        old = json.loads(row["answer"], object_pairs_hook=unique)
        new = json.loads(changed, object_pairs_hook=unique)
        need(old["action"] == new["action"] and old["options"] == new["options"]
             and after["utility"] >= before["utility"], "NON_PROJECT_FIELD_MUTATION")
        out.append({"fixture": row["fixture"], "variant": row["variant"],
                    "binding": tag, "before_utility": before["utility"],
                    "after_utility": after["utility"],
                    "before_exact": before["exact"], "after_exact": after["exact"],
                    "action_unchanged": True, "options_unchanged": True})
    summary = {}
    for variant in VARIANTS:
        subset = [r for r in out if r["variant"] == variant]
        need(len(subset) == len(PROJECTS), "INCOMPLETE_VARIANT")
        summary[variant] = {
            "rows": 6,
            "before_mean_utility": sum(r["before_utility"] for r in subset) / 6,
            "after_mean_utility": sum(r["after_utility"] for r in subset) / 6,
            "before_full_exact": sum(r["before_exact"] for r in subset),
            "after_full_exact": sum(r["after_exact"] for r in subset),
            "aliases_bound": sum(r["binding"] == "SOURCE_ID_LITERAL_PREFIX_BOUND" for r in subset),
        }
    return {
        "schema": "v13.step2.project_identity_source_binding_candidate.v1",
        "status": "SOFTWARE_FORMAT_DIAGNOSTIC_NO_GATE",
        "original_source_sha256": frozen.ORIGINAL_SOURCE_SHA256,
        "original_tool_sha256": TOOL_SHA256,
        "rows": 42, "native_calls": 0,
        "literal_aliases_bound": sum(r["binding"] == "SOURCE_ID_LITERAL_PREFIX_BOUND" for r in out),
        "full_exact_gained": sum(r["after_exact"] and not r["before_exact"] for r in out),
        "per_variant": summary, "canonical_gate_pass": False,
        "step2_status": "UTILITY_FAIL", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "scope": "OFFLINE_RESCORING_OF_ORIGINAL_NATIVE_OUTPUTS_NOT_NEW_NATIVE",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-report", type=Path, required=True)
    p.add_argument("--tool-report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    need(not a.out.exists(), "FRESH_OUTPUT_REQUIRED")
    source = frozen.load_original(a.source_report)
    need(file_hash(a.tool_report) == TOOL_SHA256, "ORIGINAL_TOOL_BYTES_DRIFT")
    tool_raw = json.loads(a.tool_report.read_text(encoding="utf-8"))
    report = replay(source, tool_raw)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": report["rows"],
                      "aliases_bound": report["literal_aliases_bound"],
                      "full_exact_gained": report["full_exact_gained"],
                      "canonical_gate_pass": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
