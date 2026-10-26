#!/usr/bin/env python3
"""Run449: classify the actual RED Run446 full-checkout unittest log, never promote it.

The classifier is diagnostic only. Matching a known failure category does not
make a failed test pass, waive a gate, or authorize changing frozen identities.
No model weights or private artifacts are read beyond the pinned source log.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

HEADING = re.compile(r"(?m)^(ERROR|FAIL): ([^\n]+)$")
SUMMARY = re.compile(r"FAILED \(failures=(\d+), errors=(\d+), skipped=(\d+)\)")
RUN = re.compile(r"Ran (\d+) tests in [\d.]+s")


def category(kind, title, block):
    if "Live sources differ from complete baseline/candidate" in block:
        return "LIVE_SOURCE_IDENTITY_REFUSAL"
    if "Runtime is neither exact frozen baseline nor complete reviewed candidate" in block:
        return "FROZEN_RUNTIME_IDENTITY_REFUSAL"
    if "RECORDED_RUNNER_IDENTITY_MISMATCH" in block:
        return "RECORDED_RUNNER_IDENTITY_REFUSAL"
    if "No module named 'torch'" in block:
        return "OPTIONAL_TORCH_UNAVAILABLE"
    if "RUN147_native.zip" in block:
        return "EXTERNAL_NATIVE_ARTIFACT_UNAVAILABLE"
    if "test_lp3_serial_cohort" in block:
        return "HISTORICAL_TEST_MODULE_UNAVAILABLE"
    if kind == "FAIL" and "test_run404_stage2_resume" in title:
        return "STAGE1_SYNTHETIC_RECEIPT_NOT_REUSABLE"
    return "UNCLASSIFIED_REQUIRES_REVIEW"


def classify(raw, exit_text):
    if not isinstance(raw, bytes):
        raise TypeError("raw must be original log bytes")
    if not re.fullmatch(r"EXIT=[1-9][0-9]*\s*", exit_text):
        raise ValueError("FULL_SUITE_RED_EXIT_REQUIRED")
    text = raw.decode("utf-8")
    summaries = list(SUMMARY.finditer(text))
    runs = list(RUN.finditer(text))
    if len(summaries) != 1 or len(runs) != 1:
        raise ValueError("UNIQUE_UNITTTEST_SUMMARY_REQUIRED")
    failures, errors, skipped = map(int, summaries[0].groups())
    n = int(runs[0].group(1))
    if not (n > 0 and failures + errors > 0):
        raise ValueError("FAILED_SUITE_WITH_CASES_REQUIRED")
    hits = list(HEADING.finditer(text))
    if len(hits) != failures + errors:
        raise ValueError("FAILURE_HEADINGS_DO_NOT_MATCH_SUMMARY")
    categories = Counter()
    cases = []
    for i, match in enumerate(hits):
        kind, title = match.groups()
        end = hits[i + 1].start() if i + 1 < len(hits) else summaries[0].start()
        cause = category(kind, title, text[match.end():end])
        categories[cause] += 1
        cases.append({"kind": kind, "test": title, "category": cause})
    if sum(c["kind"] == "FAIL" for c in cases) != failures:
        raise ValueError("FAILURE_KIND_COUNT_MISMATCH")
    return {
        "schema": "V13_RUN449_RUN446_RED_CLASSIFICATION_V1",
        "status": "RED_FULL_SUITE_UNRESOLVED",
        "source": "actual original Run446 full-checkout unittest raw log",
        "log_sha256": hashlib.sha256(raw).hexdigest(),
        "tests_run": n, "failures": failures, "errors": errors, "skipped": skipped,
        "categories": dict(sorted(categories.items())),
        "unclassified": categories["UNCLASSIFIED_REQUIRES_REVIEW"],
        "cases": cases,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "b3": "FAIL", "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "meaning": "Diagnostic grouping only; all original failures remain RED."
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--exit-file", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = classify(a.log.read_bytes(), a.exit_file.read_text())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "tests_run", "failures", "errors", "skipped", "categories", "unclassified")}, sort_keys=True))


if __name__ == "__main__":
    main()
