"""Run117: isolated exact-source prior-rule span candidate (SOFTWARE ONLY).

No runtime authority, no native/model calls, no fixture/oracle changes.
The candidate transports one bounded exact historical source span, not a
semantic rule decision or a learned memory. Requires separate native ablation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from scripts import run109_step2_fresh_fixtures as corpus
from scripts import run111_step2_fresh_native_preflight as pre

RULE = re.compile(
    r"\bBudget\s+\d+\s+euros\.\s+Deadline\s+\d+\s+days\.\s+"
    r"Local-only requirement:\s+(?:true|false)\.", re.IGNORECASE)
RULE_KEY = re.compile(
    r"\b(?:Budget\s+\d+|Deadline\s+\d+|Local-only requirement\s*:)",
    re.IGNORECASE)
PROJECT = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
CAP = 200
LEGACY_EXCERPT = 240
FIXTURE_SHA256 = pre.FIXTURE_SHA256


def require(ok, message):
    if not ok:
        raise ValueError(message)


def select(sources, project, cap=CAP):
    """Latest complete single-source triplet, with byte-bound original provenance.

    This does not merge partial revisions. Any later partial rule update for the
    same project is ambiguous and refuses, rather than using stale earlier rules.
    """
    require(isinstance(project, str) and PROJECT.fullmatch(project) is not None,
            "INVALID_PROJECT")
    require(type(cap) is int and 0 < cap <= CAP, "INVALID_CAP")
    require(isinstance(sources, (list, tuple)) and sources
            and all(isinstance(s, str) for s in sources), "INVALID_SOURCES")
    candidate = None
    for index, source in enumerate(sources):
        # Require a literal project prefix plus word boundary. No fuzzy matches.
        prefix = "Project " + project
        if not source.startswith(prefix) or (
                len(source) > len(prefix)
                and (source[len(prefix)].isalnum()
                     or source[len(prefix)] in "_-")):
            continue
        mentioned = re.findall(r"\bProject\s+([A-Za-z][A-Za-z0-9_-]*)\b", source)
        if any(name != project for name in mentioned):
            raise ValueError("CROSS_PROJECT_SOURCE_AMBIGUOUS")
        matches = list(RULE.finditer(source))
        keys = list(RULE_KEY.finditer(source))
        if len(matches) > 1:
            raise ValueError("AMBIGUOUS_SAME_SOURCE_REVISIONS")
        if not matches:
            if keys:
                raise ValueError("INCOMPLETE_LATER_RULE_SOURCE")
            continue
        match = matches[0]
        if any(not (match.start() <= key.start() < match.end())
               for key in keys):
            raise ValueError("AMBIGUOUS_EXTRA_RULE_FIELDS")
        span = source[match.start():match.end()]
        require(len(span) <= cap, "RULE_SPAN_OVER_CAP")
        require(source[match.start():match.end()] == span, "SOURCE_SPAN_MISMATCH")
        candidate = {
            "source_index": index, "char_start": match.start(),
            "char_end": match.end(), "text": span,
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "span_sha256": hashlib.sha256(span.encode("utf-8")).hexdigest(),
            "provenance": "EXACT_ORIGINAL_SOURCE_SUBSTRING",
            "semantic_authority": False, "native_calls": 0,
        }
    if candidate is None:
        raise ValueError("NO_COMPLETE_SOURCE_RULE")
    return candidate


def evaluate():
    inspection = corpus.inspect()
    require(inspection["fixture_sha256"] == FIXTURE_SHA256
            and all(inspection["checks"].values())
            and len(inspection["fixtures"]) == 6,
            "FROZEN_FIXTURE_DRIFT")
    records = []
    for fixture in inspection["fixtures"]:
        # Only exact project identifier and source history are supplied to select.
        # No oracle, desired action, options or score enters the selector.
        name = fixture["id"]
        sources = fixture["history"]
        candidate = select(sources, name)
        legacy = None
        legacy_error = None
        try:
            legacy = select([s[:LEGACY_EXCERPT] for s in sources], name)
        except ValueError as exc:
            legacy_error = str(exc)
        records.append({
            "fixture": name, "kind": fixture["fixture_kind"],
            "candidate": candidate,
            "legacy_first_240_covered": legacy is not None,
            "legacy_error": legacy_error,
            "latest_source_index": candidate["source_index"],
            "exact_substring": (
                sources[candidate["source_index"]][candidate["char_start"]:
                    candidate["char_end"]] == candidate["text"]),
            "native_calls": 0,
        })
    covered = sum(bool(r["exact_substring"]) for r in records)
    baseline = sum(r["legacy_first_240_covered"] for r in records)
    return {
        "schema": "v13.run117.exact_rule_source_candidate.v1",
        "status": ("SOFTWARE_SOURCE_SPAN_COVERAGE_PASS_NO_AUTHORITY"
                   if covered == 6 and baseline < 6 else "SOFTWARE_COVERAGE_FAIL"),
        "fixture_sha256": FIXTURE_SHA256, "source_kind": "SYNTHETIC_SOFTWARE",
        "candidate_covered": covered, "legacy_covered": baseline,
        "rows": records, "models_loaded": False, "native_calls": 0,
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
    return 0 if report["status"].startswith("SOFTWARE_SOURCE_SPAN_COVERAGE_PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
