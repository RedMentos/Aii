"""Run125 conditional STEP2 source-exact rule transport replay preflight.

This module prepares matched C3 messages from the frozen Run116 source report.
It NEVER executes native inference, trains, alters runtime, or promotes gates.
A separate preregistered serial native executor is required after raw audit.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from scripts import run111_step2_fresh_native_preflight as pre
from scripts import run117_step2_rule_source_candidate as span
from scripts import run118_step2_rule_pointer_choice_candidate as pointer
from scripts import step2_rule_revision_ambiguity_candidate as guard
from v13.common import digest, dumps, file_hash

ORIGINAL_SOURCE_SHA256 = "c0cd539ec28f9583abe25c93f48871597df6758c442782eb6fedd56ad612105f"
ORIGINAL_FIXTURE_SHA256 = pre.FIXTURE_SHA256
VARIANTS = pre.VARIANTS
PROJECTS = pre.EXPECTED_PROJECTS
EXPECTED_PAIRS = {(p, v) for p in PROJECTS for v in VARIANTS}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def select_rule(fixture):
    """Source-only: never pass oracle, desired action or scoring to selector."""
    project = fixture["id"]
    history = [pointer.make_record(text, project + "-h" + str(i))
               for i, text in enumerate(fixture["history"])]
    current = pointer.make_record(fixture["current"], project + "-current")
    choice = guard.build(current, history, project)
    selected = span.select(fixture["history"], project)
    original = fixture["history"][selected["source_index"]]
    ref = dict(history[selected["source_index"]]["source_ref"])
    ref["char_start"] = selected["char_start"]
    ref["char_end"] = selected["char_end"]
    require(selected["span_sha256"] == choice["selected_prior_span_sha256"]
            and selected["text"] == original[ref["char_start"]:ref["char_end"]]
            and selected["source_sha256"] == ref["sha256"]
            and len(selected["text"]) <= 200
            and choice["candidate_covered"]
            and choice["semantic_authority"] is False,
            "SOURCE_EXACT_RULE_BINDING_RED")
    return {"text": selected["text"], "source_ref": ref,
            "verification": "FIXTURE_SOURCE_SHA_BOUND_NOT_RUNTIME_STORE_REF",
            "semantic_authority": False}


def pair_messages(messages, fixture, rule):
    """Only B2 verified quotes can receive the exact historical rule span."""
    require(isinstance(messages, list) and len(messages) == 2
            and all(isinstance(m, dict) and set(m) == {"role", "content"}
                    and isinstance(m["content"], str) for m in messages)
            and messages[0]["role"] == "system"
            and messages[1]["role"] == "user", "INVALID_CONSUMER_MESSAGES")
    control = deepcopy(messages)
    try:
        user = json.loads(control[1]["content"])
    except (TypeError, ValueError):
        raise ValueError("INVALID_CONSUMER_JSON") from None
    require(isinstance(user, dict)
            and user.get("current_source") == fixture["current"]
            and isinstance(user.get("analysts"), list)
            and all(isinstance(a, dict) and isinstance(a.get("role"), str)
                    and isinstance(a.get("verified_quotes"), list)
                    and all(isinstance(q, str) for q in a["verified_quotes"])
                    for a in user["analysts"]), "CONSUMER_SOURCE_OR_ANALYST_BINDING_RED")
    treatment = deepcopy(control)
    body = deepcopy(user)
    b2 = [a for a in body["analysts"] if a["role"] == "B2_GIST"]
    require(len(b2) <= 1, "AMBIGUOUS_B2_ANALYST")
    inserted = bool(b2 and rule["text"] not in b2[0]["verified_quotes"])
    if inserted:
        b2[0]["verified_quotes"].append(rule["text"])
    treatment[1]["content"] = dumps(body)
    # If no quote was inserted, preserve the control bytes exactly.
    if not inserted:
        treatment = deepcopy(control)
    require(control[0] == treatment[0], "SYSTEM_PROMPT_MUTATION")
    require(len(treatment) == len(control), "CONSUMER_SHAPE_MUTATION")
    return {"control_messages": control, "treatment_messages": treatment,
            "control_sha256": digest(dumps(control)),
            "treatment_sha256": digest(dumps(treatment)),
            "injected": inserted, "rule_source_ref": rule["source_ref"],
            "rule_text_sha256": hashlib.sha256(rule["text"].encode()).hexdigest(),
            "oracle_visible_to_native": False, "native_calls": 0}


def transform(source):
    """Verify original 42-row source report, then prepare 42 matched pairs."""
    require(isinstance(source, dict)
            and source.get("fixture_sha256") == ORIGINAL_FIXTURE_SHA256
            and source.get("status") in ("UTILITY_FAIL", "UTILITY_PASS_SCOPED")
            and source.get("all_structural_checks_passed") is True
            and source.get("canonical_gate_pass") is False
            and source.get("phone_measured") is False
            and source.get("source_unchanged") is True
            and source.get("installed_artifacts_unchanged") is True
            and source.get("distinct_bodies") is True
            and source.get("same_weight_file") is False,
            "FROZEN_SOURCE_REPORT_STRUCTURE_RED")
    fixtures = source.get("fixtures", [])
    require(isinstance(fixtures, list)
            and tuple(f.get("id") for f in fixtures) == PROJECTS
            and pre._canonical_sha(fixtures) == ORIGINAL_FIXTURE_SHA256,
            "FROZEN_FIXTURE_DRIFT")
    rows = source.get("rows", [])
    require(isinstance(rows, list) and len(rows) == 42
            and {(r.get("fixture"), r.get("variant")) for r in rows} == EXPECTED_PAIRS
            and len({(r["fixture"], r["variant"]) for r in rows}) == 42,
            "FROZEN_ROW_PAIRS_RED")
    rules = {f["id"]: select_rule(f) for f in fixtures}
    by_project = {f["id"]: f for f in fixtures}
    out = []
    for row in rows:
        key = row["fixture"] + ":" + row["variant"]
        require(source.get("row_sha256", {}).get(key) == digest(dumps(row))
                and row.get("status") == "RECORDED"
                and row.get("oracle_visible_to_native") is False
                and row.get("native_consumer_metrics", {}).get("status") == "FINAL"
                and row.get("checks", {}).get("real_C3_final") is True,
                "FROZEN_NATIVE_ROW_BINDING_RED:" + key)
        prepared = pair_messages(row["consumer_messages"],
                                 by_project[row["fixture"]], rules[row["fixture"]])
        prepared.update({"fixture": row["fixture"], "variant": row["variant"],
                         "source_row_sha256": source["row_sha256"][key]})
        out.append(prepared)
    require(len(out) == 42 and
            all((r["control_sha256"] == r["treatment_sha256"]) ==
                (not r["injected"]) for r in out), "PAIR_MUTATION_RED")
    return {
        "schema": "v13.step2.exact_rule_native_replay_preflight.v1",
        "status": "SOFTWARE_PREPARED_NATIVE_NOT_LAUNCHED",
        "original_source_sha256": ORIGINAL_SOURCE_SHA256,
        "fixture_sha256": ORIGINAL_FIXTURE_SHA256,
        "rows": out, "pair_count": 42,
        "injected_count": sum(r["injected"] for r in out),
        "native_calls": 0, "models_loaded": False,
        "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
        "age_authority": 0, "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False,
    }


def load_original(path):
    path = Path(path).resolve()
    require(path.is_file() and file_hash(path) == ORIGINAL_SOURCE_SHA256,
            "ORIGINAL_SOURCE_BYTES_DRIFT")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    out = args.out.expanduser().resolve()
    if out.exists():
        raise FileExistsError("FRESH_REPORT_PATH_REQUIRED")
    report = transform(load_original(args.source_report))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "pairs": report["pair_count"],
                      "injected": report["injected_count"], "native_calls": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
