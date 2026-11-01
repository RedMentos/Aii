#!/usr/bin/env python3
"""Run117CR read-only, complete frozen-integrated vs live source drift audit.

Never alters the accepted source set, production files, or frozen tests.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path

from scripts.integrated_candidates import ROOT, NAMES, integrated_sources

SCHEMA = "v13.run117cr.source_chain_drift_audit.v1"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def compare(expected, actual, names=NAMES):
    if (type(expected) is not dict or type(actual) is not dict
            or type(names) not in (tuple, list)
            or not names or len(set(names)) != len(names)
            or set(expected) != set(names) or set(actual) != set(names)
            or any(type(x) is not str or not x for x in names)
            or any(type(expected[n]) is not str or type(actual[n]) is not str
                   for n in names)):
        raise ValueError("SOURCE_CHAIN_INPUT_RED")
    files = []
    for name in names:
        want, have = expected[name], actual[name]
        lines = list(difflib.unified_diff(
            want.splitlines(keepends=True), have.splitlines(keepends=True),
            fromfile="expected/" + name, tofile="live/" + name, n=3))
        diff = "".join(lines)
        files.append({
            "path": name,
            "exact": want == have,
            "expected_sha256": digest(want.encode("utf-8")),
            "live_sha256": digest(have.encode("utf-8")),
            "expected_lines": len(want.splitlines()),
            "live_lines": len(have.splitlines()),
            "diff_lines": len(lines),
            "unified_diff_sha256": digest(diff.encode("utf-8")),
        })
    changed = [f["path"] for f in files if not f["exact"]]
    return {
        "schema": SCHEMA,
        "status": "EXACT_REVIEWED_CHAIN" if not changed
                  else "CHAIN_DRIFT_REQUIRES_REVIEW",
        "changed_files": changed,
        "checked_files": len(files),
        "files": files,
        "acceptance_modified": False,
        "native_calls": 0,
        "model_calls": 0,
        "full_suite_promoted": False,
        "age0": "RECORD_ONLY",
        "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION",
        "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0,
        "redmi_measured": False,
        "whole_system_complete": False,
    }


def audit(root=ROOT):
    root = Path(root)
    before = {name: (root / name).read_bytes() for name in NAMES}
    expected = integrated_sources(root)
    if set(expected) != set(NAMES):
        raise ValueError("INCOMPLETE_REVIEWED_SOURCE_SET_RED")
    actual = {name: before[name].decode("utf-8") for name in NAMES}
    result = compare(expected, actual)
    after = {name: (root / name).read_bytes() for name in NAMES}
    if before != after:
        raise ValueError("LIVE_SOURCE_CHANGED_DURING_AUDIT_RED")
    return result, expected, actual


def unified_diffs(expected, actual, names=NAMES):
    if set(expected) != set(names) or set(actual) != set(names):
        raise ValueError("INCOMPLETE_SOURCE_SET_RED")
    for name in names:
        yield "".join(difflib.unified_diff(
            expected[name].splitlines(keepends=True),
            actual[name].splitlines(keepends=True),
            fromfile="expected/" + name, tofile="live/" + name, n=3))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--diff-output", type=Path)
    args = parser.parse_args()
    report, expected, actual = audit(args.root)
    if args.diff_output is not None:
        # The caller owns this explicit report destination. Never write to
        # the repository's source files or acceptance manifest.
        args.diff_output.write_text("".join(unified_diffs(expected, actual)),
                                    encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
