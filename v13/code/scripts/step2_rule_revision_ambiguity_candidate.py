"""Fail-closed source revision guard for isolated Run118 pointer candidate.

SOFTWARE ONLY: no native/model call, no oracle, no production mutation or
semantic authority. This deliberately does not alter the frozen Run117/118
comparison; it guards a separate candidate before delegating to Run118.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from scripts import run109_step2_fresh_fixtures as corpus
from scripts import run117_step2_rule_source_candidate as span
from scripts import run118_step2_rule_pointer_choice_candidate as pointer

CHANGE = re.compile(
    r"\b(?:new|updated|revised|superseded|changed)\s+(?:project\s+)?rules?\b"
    r"|\brules?\s+(?:were\s+|have\s+been\s+|has\s+been\s+)?"
    r"(?:changed|updated|revised|superseded)\b"
    r"|\bbudget\s+(?:changed|updated|revised)\b",
    re.IGNORECASE,
)
NO_CHANGE = re.compile(
    r"\bno\s+(?:project\s+)?rules?\s+(?:have\s+|has\s+)?changed\b",
    re.IGNORECASE,
)


def mentions_project(text: str, project: str) -> bool:
    return re.search(r"\bProject\s+" + re.escape(project) + r"(?![\w-])",
                     text, re.IGNORECASE) is not None


def change_signal(text: str) -> bool:
    if span.RULE_KEY.search(text):
        return True
    return CHANGE.search(NO_CHANGE.sub("", text)) is not None


def build(current, history, project, cap=pointer.CAP):
    """Refuse ambiguous newer rules before exposing historical rule choices."""
    if not isinstance(project, str) or span.PROJECT.fullmatch(project) is None:
        raise ValueError("INVALID_PROJECT")
    if type(cap) is not int or not 3 <= cap <= pointer.CAP:
        raise ValueError("INVALID_OR_INSUFFICIENT_CAP")
    if not isinstance(history, (list, tuple)) or not history:
        raise ValueError("INVALID_HISTORY")
    current = pointer.checked_record(current)
    history = [pointer.checked_record(item) for item in history]
    ids = [r["source_ref"]["source_id"] for r in history] + [
        current["source_ref"]["source_id"]]
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_SOURCE_ID")
    selected = span.select([r["text"] for r in history], project)
    for record in history[selected["source_index"] + 1:]:
        text = record["text"]
        if mentions_project(text, project) and change_signal(text):
            raise ValueError("UNRESOLVED_LATER_PROJECT_RULE_SOURCE")
    if mentions_project(current["text"], project) and change_signal(current["text"]):
        raise ValueError("CURRENT_MESSAGE_RULE_UPDATE_UNRESOLVED")
    result = pointer.build(current, history, project, cap=cap)
    result["status"] = "EXACT_PRIOR_RULE_CHOICES_REVISION_GUARDED_SOFTWARE_ONLY"
    result["revision_ambiguity_guard"] = "FAIL_CLOSED_ON_NEWER_RULE_SIGNAL"
    result["semantic_authority"] = False
    result["canonical_gate_pass"] = False
    return result


def evaluate():
    frozen = corpus.inspect()
    if (frozen["fixture_sha256"] != pointer.FIXTURE_SHA256
            or not all(frozen["checks"].values())
            or len(frozen["fixtures"]) != 6):
        raise ValueError("FROZEN_FIXTURE_DRIFT")
    rows = []
    for fixture in frozen["fixtures"]:
        history = [pointer.make_record(text, fixture["id"] + "-h" + str(i))
                   for i, text in enumerate(fixture["history"])]
        current = pointer.make_record(fixture["current"], fixture["id"] + "-current")
        result = build(current, history, fixture["id"])
        rows.append({"fixture": fixture["id"],
                     "candidate_covered": result["candidate_covered"],
                     "legacy_covered": result["legacy_covered"],
                     "selected_prior_source_index": result["selected_prior_source_index"],
                     "choice_count": len(result["choices"]),
                     "native_calls": 0})
    covered = sum(r["candidate_covered"] for r in rows)
    return {
        "schema": "v13.step2.rule_revision_ambiguity_guard.v1",
        "status": ("SOFTWARE_REVISION_GUARD_PASS_NO_AUTHORITY"
                   if covered == 6 else "SOFTWARE_REVISION_GUARD_RED"),
        "fixture_sha256": pointer.FIXTURE_SHA256,
        "candidate_covered": covered, "rows": rows,
        "models_loaded": False, "native_calls": 0,
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
    report = evaluate()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"],
                      "candidate_covered": report["candidate_covered"],
                      "native_calls": 0, "canonical_gate_pass": False}, sort_keys=True))
    return 0 if report["status"] == "SOFTWARE_REVISION_GUARD_PASS_NO_AUTHORITY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
