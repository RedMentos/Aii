"""Run108: deterministic B2 pointer source-transport stress, no model inference.

Prereg: docs/proofs/continuation-20261028/RUN108_STEP2_POINTER_LONG_NOTES_PREREG.md
This does not measure B1/B2 complementarity or promote STEP2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from v13.cognition import quote_choices, quote_span, sentence_spans

HEADER = "Project Kestrel kickoff notes."
OLD = "Budget 100 euros. Deadline 5 days. Local-only requirement: true."
NEW = "Revision: Budget 120 euros. Deadline 7 days. Local-only requirement: false."
FILLER = "Supplier review item {i} is informational only."
SCHEMA = "v13.run108.step2_pointer_long_note_structural.v1"


def fixtures():
    return {
        "SHORT": HEADER + " " + OLD,
        "LONG": HEADER + " " + " ".join(FILLER.format(i=i) for i in range(12)) + " " + OLD,
        "REVISED": HEADER + " " + OLD + " " + NEW,
        "CAP24": HEADER + " " + " ".join(FILLER.format(i=i) for i in range(30)) + " " + OLD,
    }


def values(text):
    return {
        "budget": [int(x) for x in re.findall(r"\bBudget (\d+) euros\b", text, re.I)],
        "deadline": [int(x) for x in re.findall(r"\bDeadline (\d+) days\b", text, re.I)],
        "local_only": [x.lower() == "true" for x in re.findall(
            r"\bLocal-only requirement: (true|false)\b", text, re.I)],
    }


def evaluate(name, source):
    all_sentences = sentence_spans(source)
    choices = quote_choices([source], cap=24)
    span = quote_span(HEADER, source, context_chars=200)
    if span is None:
        raise AssertionError("HEADER_POINTER_MISSING")
    start, end = span
    if not (0 <= start < end <= len(source) and HEADER in source[start:end]
            and end - start <= 200):
        raise AssertionError("SOURCE_SPAN_OUTSIDE_BOUNDARY")
    extracted = source[start:end]
    selected = [source[a:b] for index, a, b in choices if index == 0]
    if any(sentence not in source for sentence in selected):
        raise AssertionError("UNVERIFIED_SOURCE_CHOICE")
    v = values(extracted)
    rule_choice_count = sum(bool(any(values(sentence)[key] for key in v))
                            for sentence in selected)
    return {
        "name": name, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "source_chars": len(source), "sentence_count": len(all_sentences),
        "choice_count": len(choices), "header_span": [start, end],
        "header_span_chars": end - start, "header_values": v,
        "rule_bearing_choices": rule_choice_count,
        "revision_ambiguous": all(len(v[k]) > 1 for k in v),
        "semantic_truth_authority": False, "model_called": False,
        "native_calls": 0,
    }


def run():
    rows = {name: evaluate(name, source) for name, source in fixtures().items()}
    short = rows["SHORT"]
    long = rows["LONG"]
    revised = rows["REVISED"]
    cap = rows["CAP24"]
    checks = {
        "short_header_carries_all_rules": short["header_values"] == {
            "budget": [100], "deadline": [5], "local_only": [True]},
        "long_header_does_not_carry_all_rules": long["header_values"] != {
            "budget": [100], "deadline": [5], "local_only": [True]},
        "long_rules_remain_selectable": long["rule_bearing_choices"] >= 3,
        "revision_is_ambiguous_not_resolved": revised["revision_ambiguous"],
        "cap24_truncates_rule_choices": cap["choice_count"] == 24
            and cap["sentence_count"] > 24 and cap["rule_bearing_choices"] == 0,
        "no_model_or_semantic_authority": all(
            not x["model_called"] and x["native_calls"] == 0
            and x["semantic_truth_authority"] is False for x in rows.values()),
    }
    return {
        "schema": SCHEMA, "status": "TRANSPORT_BOUNDARY_OBSERVED"
            if all(checks.values()) else "STRUCTURAL_PROBE_RED",
        "evidence_kind": "DETERMINISTIC_SOFTWARE_NO_MODEL",
        "checks": checks, "cases": rows, "canonical_gate_pass": False,
        "step2_status": "UTILITY_FAIL", "redmi_measured": False,
        "whole_system_complete": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    out = args.out.expanduser().resolve()
    if out.exists():
        raise FileExistsError("FRESH_EVIDENCE_FILE_REQUIRED")
    out.parent.mkdir(parents=True, exist_ok=True)
    report = run()
    out.write_text(json.dumps(report, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": report["checks"]},
                     sort_keys=True))
    return 0 if report["status"] == "TRANSPORT_BOUNDARY_OBSERVED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
