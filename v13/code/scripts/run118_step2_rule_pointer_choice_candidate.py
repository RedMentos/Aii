"""Run118: exact prior-rule pointer-choice bridge candidate (SOFTWARE ONLY).

No production cognition mutation, model calls, oracle, training or authority.
All choices are re-bound to immutable full-source SHA256 and character offsets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts import run109_step2_fresh_fixtures as corpus
from scripts import run117_step2_rule_source_candidate as span
from v13.cognition import quote_choices

CAP = 24
FIXTURE_SHA256 = span.FIXTURE_SHA256


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def make_record(text, source_id):
    return {
        "text": text,
        "source_ref": {
            "source_id": source_id,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "modality": "text", "char_start": 0, "char_end": len(text),
        },
    }


def checked_record(record):
    require(isinstance(record, dict) and isinstance(record.get("text"), str)
            and isinstance(record.get("source_ref"), dict), "INVALID_SOURCE_RECORD")
    text = record["text"]
    ref = record["source_ref"]
    require(isinstance(ref.get("source_id"), str) and bool(ref["source_id"])
            and ref.get("modality") == "text"
            and type(ref.get("char_start")) is int and ref["char_start"] == 0
            and type(ref.get("char_end")) is int and ref["char_end"] == len(text)
            and ref.get("sha256") == hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "SOURCE_REF_BINDING_RED")
    return record


def build(current, history, project, cap=CAP):
    require(type(cap) is int and 3 <= cap <= CAP, "INVALID_OR_INSUFFICIENT_CAP")
    require(isinstance(history, (list, tuple)) and history, "INVALID_HISTORY")
    current = checked_record(current)
    history = [checked_record(r) for r in history]
    ids = [r["source_ref"]["source_id"] for r in history] + [
        current["source_ref"]["source_id"]]
    require(len(ids) == len(set(ids)), "DUPLICATE_SOURCE_ID")
    require(current["text"].startswith("Project " + project)
            and (len(current["text"]) == len("Project " + project)
                 or current["text"][len("Project " + project)] in ". :"),
            "CURRENT_PROJECT_MISMATCH")
    selected = span.select([r["text"] for r in history], project)
    prior = history[selected["source_index"]]
    require(selected["source_sha256"] == prior["source_ref"]["sha256"]
            and prior["text"][selected["char_start"]:selected["char_end"]]
                == selected["text"], "SELECTED_SOURCE_BINDING_RED")

    # Unlike current-first legacy cap24, the verified prior rule is selectable.
    source_texts = [selected["text"], current["text"]]
    raw_choices = quote_choices(source_texts, cap=cap)
    choices = []
    for n, (si, a, b) in enumerate(raw_choices, 1):
        record = prior if si == 0 else current
        base = selected["char_start"] if si == 0 else 0
        ref = dict(record["source_ref"])
        ref["char_start"] = base + a
        ref["char_end"] = base + b
        text = source_texts[si][a:b]
        require(record["text"][ref["char_start"]:ref["char_end"]] == text,
                "CHOICE_EXACT_SOURCE_MISMATCH")
        choices.append({
            "id": n, "text": text, "source_ref": ref,
            "kind": "PRIOR_RULE_SOURCE" if si == 0 else "CURRENT_SOURCE",
            "verification": "EXACT_SOURCE_SUBSTRING_ONLY",
            "semantic_authority": False,
        })
    prior_choices = [x["text"] for x in choices if x["kind"] == "PRIOR_RULE_SOURCE"]
    covered = all(any(key in q for q in prior_choices)
                  for key in ("Budget ", "Deadline ", "Local-only requirement:"))
    require(covered, "RULE_CHOICES_MISSING_UNDER_CAP")

    # Frozen first240/current-first comparator; no oracle enters either path.
    legacy_sources = [current["text"]] + [
        r["text"][:span.LEGACY_EXCERPT] for r in history]
    legacy = quote_choices(legacy_sources, cap=cap)
    legacy_prior = [legacy_sources[si][a:b] for si, a, b in legacy if si > 0]
    legacy_covered = all(any(key in q for q in legacy_prior)
                         for key in ("Budget ", "Deadline ", "Local-only requirement:"))
    return {
        "status": "EXACT_PRIOR_RULE_CHOICES_SOFTWARE_ONLY",
        "project": project, "choices": choices,
        "selected_prior_source_index": selected["source_index"],
        "selected_prior_span_sha256": selected["span_sha256"],
        "candidate_covered": covered, "legacy_covered": legacy_covered,
        "cap": cap, "native_calls": 0, "semantic_authority": False,
        "canonical_gate_pass": False,
    }


def evaluate():
    report = corpus.inspect()
    require(report["fixture_sha256"] == FIXTURE_SHA256
            and all(report["checks"].values()), "FROZEN_FIXTURE_DRIFT")
    rows = []
    for f in report["fixtures"]:
        history = [make_record(text, f["id"] + "-h" + str(i))
                   for i, text in enumerate(f["history"])]
        current = make_record(f["current"], f["id"] + "-current")
        result = build(current, history, f["id"])
        rows.append({
            "fixture": f["id"], "kind": f["fixture_kind"],
            "candidate_covered": result["candidate_covered"],
            "legacy_covered": result["legacy_covered"],
            "prior_choice_count": sum(
                c["kind"] == "PRIOR_RULE_SOURCE" for c in result["choices"]),
            "selected_prior_source_index": result["selected_prior_source_index"],
            "choices": result["choices"], "native_calls": 0,
        })
    covered = sum(x["candidate_covered"] for x in rows)
    baseline = sum(x["legacy_covered"] for x in rows)
    return {
        "schema": "v13.run118.rule_pointer_choice_candidate.v1",
        "status": ("SOFTWARE_EXACT_RULE_CHOICES_PASS_NO_AUTHORITY"
                   if covered == 6 and baseline < 6 else "SOFTWARE_RULE_CHOICES_FAIL"),
        "fixture_sha256": FIXTURE_SHA256,
        "candidate_covered": covered, "legacy_covered": baseline,
        "rows": rows, "models_loaded": False, "native_calls": 0,
        "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
        "age_authority": 0, "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    out = args.out.expanduser().resolve()
    if out.exists():
        raise FileExistsError("FRESH_REPORT_PATH_REQUIRED")
    out.parent.mkdir(parents=True, exist_ok=True)
    report = evaluate()
    out.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True,
                              indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"], "candidate_covered": report["candidate_covered"],
        "legacy_covered": report["legacy_covered"],
        "native_calls": 0, "canonical_gate_pass": False}, sort_keys=True))
    return 0 if report["status"].startswith("SOFTWARE_EXACT_RULE_CHOICES_PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
