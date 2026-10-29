"""Run130 source-exact B1 quote repair of C3 typed option fields, offline only.

No oracle in repair(), no inference, no runtime integration or gate promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

from scripts import step2_exact_rule_native_replay_preflight as frozen
from scripts import step2_tool_replay as tool
from v13.common import digest, dumps, file_hash
from v13.utility import score_decision

TOOL_SHA256 = "e90c23fd909dc0e138312f6802a05a3377f451f6675a496c1d4b1f1b19847ac0"
PROJECTS = frozen.PROJECTS
VARIANTS = frozen.VARIANTS
CLAUSE = re.compile(
    r"\bOption\s+([AB]):\s*cost\s+(\d+)\s+euros,\s*duration\s+(\d+)\s+days,\s*local\s+(true|false)\.",
    re.I,
)


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def unique(pairs):
    out = {}
    for k, v in pairs:
        need(k not in out, "DUPLICATE_JSON_KEY")
        out[k] = v
    return out


def verified_b1_quotes(source_row, fixture):
    """Every evidence span must be original source bytes; B1 quotes must occur in it."""
    need(source_row.get("checks", {}).get("every_source_read_validated") is True,
         "SOURCE_READ_NOT_VALIDATED")
    sources = [fixture["current"], *fixture["history"]]
    spans = []
    for entry in source_row.get("source_evidence", []):
        ref = entry["source_ref"]
        start, end = ref["char_start"], ref["char_end"]
        need(type(start) is int and type(end) is int and 0 <= start < end,
             "INVALID_SOURCE_OFFSETS")
        need(any(hashlib.sha256(s.encode("utf-8")).hexdigest() == ref["sha256"]
                 and end <= len(s) and s[start:end] == entry["text"]
                 for s in sources), "SOURCE_REF_BYTES_DRIFT")
        spans.append(entry["text"])
    need(spans, "SOURCE_EVIDENCE_MISSING")
    user = json.loads(source_row["consumer_messages"][1]["content"], object_pairs_hook=unique)
    analysts = [a for a in user["analysts"] if a.get("role") == "B1_DETAIL"]
    need(len(analysts) <= 1, "DUPLICATE_B1_ANALYST")
    quotes = []
    for analyst in analysts:
        for q in analyst["verified_quotes"]:
            need(isinstance(q, str) and any(q in span for span in spans),
                 "UNVERIFIED_B1_QUOTE")
            quotes.append(q)
    return quotes


def exact_options(quotes):
    """Return two unambiguous typed source values or None; never guess."""
    found = {"A": set(), "B": set()}
    for quote in quotes:
        for entity, cost, days, local in CLAUSE.findall(quote):
            found[entity.upper()].add((int(cost), int(days), local.lower() == "true"))
    if len(found["A"]) != 1 or len(found["B"]) != 1:
        return None
    return {entity: {"entity": entity, "cost": values[0], "days": values[1], "local": values[2]}
            for entity, values in ((e, next(iter(found[e]))) for e in ("A", "B"))}


def repair(raw_extract, source_row, fixture):
    """No oracle or target action available. Returns (new raw, status, changed_fields)."""
    quotes = verified_b1_quotes(source_row, fixture)
    exact = exact_options(quotes)
    if exact is None:
        return raw_extract, "NO_UNAMBIGUOUS_SOURCE_OPTIONS", 0
    try:
        x = json.loads(raw_extract, object_pairs_hook=unique)
    except (ValueError, TypeError) as exc:
        raise ValueError("INVALID_C3_EXTRACTION_JSON") from exc
    need(isinstance(x, dict)
         and set(x) == {"project", "options", "budget", "deadline", "local_only"}
         and isinstance(x["options"], list) and len(x["options"]) == 2,
         "INVALID_C3_EXTRACTION_SCHEMA")
    changed = 0
    entities = []
    for option in x["options"]:
        need(isinstance(option, dict)
             and set(option) == {"entity", "cost", "days", "local"}
             and option["entity"] in ("A", "B"), "INVALID_OPTION_SCHEMA")
        entities.append(option["entity"])
        for field in ("cost", "days", "local"):
            need(type(option[field]) is type(exact[option["entity"]][field]),
                 "INVALID_TYPED_OPTION_FIELD")
            if option[field] != exact[option["entity"]][field]:
                option[field] = exact[option["entity"]][field]
                changed += 1
    need(set(entities) == {"A", "B"}, "DUPLICATE_OPTION_ENTITY")
    if changed == 0:
        return raw_extract, "EXACT_OPTIONS_ALREADY_MATCH", 0
    return dumps(x), "SOURCE_EXACT_OPTIONS_REPAIRED", changed


def action(answer):
    try:
        obj = json.loads(answer)
    except (ValueError, TypeError):
        return "INVALID"
    a = obj.get("action") if isinstance(obj, dict) else None
    return a if a in ("A", "B", "NONE", "UNKNOWN") else "INVALID"


def replay(source, tool_raw):
    need(source.get("fixture_sha256") == frozen.ORIGINAL_FIXTURE_SHA256
         and source.get("all_structural_checks_passed") is True
         and source.get("canonical_gate_pass") is False
         and source.get("phone_measured") is False, "SOURCE_SCOPE_DRIFT")
    fixtures = source.get("fixtures")
    need(isinstance(fixtures, list)
         and tuple(f["id"] for f in fixtures) == PROJECTS, "FIXTURE_COVERAGE_RED")
    fixture_by_id = {f["id"]: f for f in fixtures}
    src_rows = {(r["fixture"], r["variant"]): r for r in source["rows"]}
    rows = tool_raw.get("rows")
    need(isinstance(rows, list) and len(rows) == 42
         and {(r.get("fixture"), r.get("variant")) for r in rows}
         == {(p, v) for p in PROJECTS for v in VARIANTS}
         and tool_raw.get("canonical_gate_pass") is False
         and tool_raw.get("phone_measured") is False, "TOOL_SCOPE_DRIFT")
    out = []
    for row in rows:
        key = (row["fixture"], row["variant"])
        src = src_rows[key]
        text_key = key[0] + ":" + key[1]
        need(source["row_sha256"][text_key] == digest(dumps(src))
             and tool_raw["row_sha256"][text_key] == digest(dumps(row))
             and src["checks"]["every_source_read_validated"] is True
             and row["status"] == "RECORDED"
             and row["consumer_metrics"]["status"] == "FINAL"
             and row["oracle_visible_to_native"] is False, "FROZEN_ROW_DRIFT")
        fixture = fixture_by_id[row["fixture"]]
        need(row["score"] == score_decision(row["answer"], fixture["oracle"]),
             "ORIGINAL_SCORE_DRIFT")
        raw, tag, changed = repair(row["raw_answer"], src, fixture)
        answer, trace = tool.tool_answer(raw, src["consumer_messages"])
        new_answer = answer or raw
        score = score_decision(new_answer, fixture["oracle"])
        original_action = action(row["answer"])
        new_action = action(new_answer)
        out.append({
            "fixture": row["fixture"], "variant": row["variant"],
            "repair_status": tag, "changed_fields": changed,
            "before_action": original_action, "after_action": new_action,
            "before_utility": row["score"]["utility"], "after_utility": score["utility"],
            "before_full_exact": row["score"]["exact"], "after_full_exact": score["exact"],
            "wrong_committed": new_action in ("A", "B", "NONE")
                               and new_action != fixture["oracle"]["action"],
        })
    summary = {}
    for variant in VARIANTS:
        subset = [r for r in out if r["variant"] == variant]
        need(len(subset) == len(PROJECTS), "VARIANT_INCOMPLETE")
        summary[variant] = {
            "rows": 6, "repaired_rows": sum(r["changed_fields"] > 0 for r in subset),
            "repaired_fields": sum(r["changed_fields"] for r in subset),
            "before_mean_utility": sum(r["before_utility"] for r in subset) / 6,
            "after_mean_utility": sum(r["after_utility"] for r in subset) / 6,
            "before_action_exact": sum(r["before_action"] == fixture_by_id[r["fixture"]]["oracle"]["action"] for r in subset),
            "after_action_exact": sum(r["after_action"] == fixture_by_id[r["fixture"]]["oracle"]["action"] for r in subset),
            "after_wrong_committed": sum(r["wrong_committed"] for r in subset),
            "before_full_exact": sum(r["before_full_exact"] for r in subset),
            "after_full_exact": sum(r["after_full_exact"] for r in subset),
        }
    wrong = sum(r["wrong_committed"] for r in out)
    return {
        "schema": "v13.step2.option_quote_consistency_candidate.v1",
        "status": "SOFTWARE_QUOTE_REPAIR_WRONG_COMMITTED_RED" if wrong else "SOFTWARE_QUOTE_REPAIR_DIAGNOSTIC_NO_GATE",
        "original_source_sha256": frozen.ORIGINAL_SOURCE_SHA256,
        "original_tool_sha256": TOOL_SHA256,
        "rows": 42, "native_calls": 0,
        "repaired_rows": sum(r["changed_fields"] > 0 for r in out),
        "repaired_fields": sum(r["changed_fields"] for r in out),
        "treatment_wrong_committed": wrong,
        "per_variant": summary,
        "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
        "jepa_weight": 0, "redmi_measured": False, "whole_system_complete": False,
        "scope": "ORIGINAL_NATIVE_OUTPUTS_OFFLINE_REPLAY_ONLY_NOT_NEW_NATIVE",
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
    report = replay(source, json.loads(a.tool_report.read_text(encoding="utf-8")))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "rows", "repaired_rows",
                                             "repaired_fields", "treatment_wrong_committed",
                                             "canonical_gate_pass")}, sort_keys=True))
    return 0 if report["treatment_wrong_committed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
