#!/usr/bin/env python3
"""Read-only, fail-closed comparison of two retained V13 full-suite ZIPs.

An equivalent failure fingerprint does not prove that a patch is regression-free.
Never promotes a RED test suite or executes archived code.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile

STAGES = ("PINS", "VENV", "DEPS", "TORCH", "TRANSFORMERS", "PEFT",
          "PIP_CHECK", "TORCH_IMPORT", "TRANSFORMERS_IMPORT",
          "PEFT_IMPORT", "COMPILE", "PRIVACY", "DIFF")
MANIFEST_LINE = re.compile(r"([0-9a-f]{64})  \\./([A-Za-z0-9_.-]+)")
SUMMARY = re.compile(r"(?m)^Ran (\\d+) tests in [0-9.]+s\\s*\\n\\s*FAILED \\(failures=(\\d+), errors=(\\d+), skipped=(\\d+)\\)")
FAILURE = re.compile(r"(?m)^(ERROR|FAIL): ([^\\r\\n]+)$")
MAX_ZIP = 32 * 1024 * 1024
MAX_MEMBER = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_bundle(path, expected_zip_sha, expected_head):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_ZIP:
        raise ValueError("missing or oversized ZIP")
    raw_zip = path.read_bytes()
    if sha256(raw_zip) != expected_zip_sha:
        raise ValueError("ZIP SHA256 mismatch")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > 64 or sum(i.file_size for i in infos) > MAX_TOTAL:
            raise ValueError("unbounded ZIP inventory")
        names = [i.filename for i in infos]
        if len(set(names)) != len(names):
            raise ValueError("duplicate ZIP member")
        for i in infos:
            p = PurePosixPath(i.filename)
            if (i.is_dir() or i.file_size > MAX_MEMBER or i.flag_bits & 1
                    or p.is_absolute() or len(p.parts) != 1
                    or p.name != i.filename or (i.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError("unsafe ZIP member")
        if archive.testzip() is not None:
            raise ValueError("ZIP CRC mismatch")
        members = {name: archive.read(name) for name in names}
    if "SHA256SUMS" not in members:
        raise ValueError("missing SHA256SUMS")
    manifest = members.pop("SHA256SUMS").decode("ascii").splitlines()
    entries = [MANIFEST_LINE.fullmatch(line) for line in manifest]
    if not entries or any(m is None for m in entries):
        raise ValueError("invalid SHA256SUMS")
    want = {m.group(2): m.group(1) for m in entries}
    if len(want) != len(entries) or set(want) != set(members):
        raise ValueError("manifest inventory mismatch")
    if any(sha256(members[name]) != digest for name, digest in want.items()):
        raise ValueError("manifest member hash mismatch")
    if members.get("HEAD.txt", b"").decode("ascii").strip() != expected_head:
        raise ValueError("tested HEAD mismatch")
    for stage in STAGES:
        if members.get(stage + "_EXIT.txt", b"").strip() != b"0":
            raise ValueError(stage + " prerequisite not PASS")
    if members.get("FULL_EXIT.txt", b"").strip() != b"1":
        raise ValueError("expected original full-suite RED, not an arbitrary exit")
    report = members["FULL_RAW.log"].decode("utf-8")
    matches = list(SUMMARY.finditer(report))
    if not matches:
        raise ValueError("missing final unittest RED summary")
    last = matches[-1]
    if report[last.end():].strip():
        raise ValueError("trailing unaccounted report content")
    n, failures, errors, skipped = map(int, last.groups())
    if failures == 0 and errors == 0:
        raise ValueError("not a failure baseline")
    headers = Counter(FAILURE.findall(report))
    if sum(headers.values()) < failures + errors:
        raise ValueError("missing traceback headers")
    return {"head": expected_head, "zip_sha256": expected_zip_sha,
            "manifest_entries": len(want), "tests": n, "failures": failures,
            "errors": errors, "skipped": skipped, "failure_headers": headers}


def compare(baseline, candidate, expected_extra):
    if candidate["tests"] - baseline["tests"] != expected_extra:
        raise ValueError("unexpected test-count delta")
    for key in ("failures", "errors", "skipped", "failure_headers"):
        if baseline[key] != candidate[key]:
            raise ValueError("changed RED failure fingerprint: " + key)
    return {"status": "MATCHING_RETAINED_FAILURE_HEADERS_NOT_A_GREEN_SUITE",
            "baseline_head": baseline["head"], "candidate_head": candidate["head"],
            "baseline_zip_sha256": baseline["zip_sha256"],
            "candidate_zip_sha256": candidate["zip_sha256"],
            "baseline_manifest_entries": baseline["manifest_entries"],
            "candidate_manifest_entries": candidate["manifest_entries"],
            "baseline_tests": baseline["tests"], "candidate_tests": candidate["tests"],
            "extra_tests": expected_extra, "failures": candidate["failures"],
            "errors": candidate["errors"], "skipped": candidate["skipped"],
            "observed_header_occurrences": sum(candidate["failure_headers"].values()),
            "observed_distinct_headers": len(candidate["failure_headers"]),
            "claim_limit": "Identical retained failure-header multiset and counts only; no proof of zero regressions, no full-suite/STEP2/JEPA/Redmi promotion."}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--baseline-sha", required=True)
    p.add_argument("--candidate-sha", required=True)
    p.add_argument("--baseline-head", required=True)
    p.add_argument("--candidate-head", required=True)
    p.add_argument("--expected-extra", type=int, default=4)
    args = p.parse_args(argv)
    try:
        if args.expected_extra < 0:
            raise ValueError("negative extra tests")
        a = read_bundle(args.baseline, args.baseline_sha, args.baseline_head)
        b = read_bundle(args.candidate, args.candidate_sha, args.candidate_head)
        print(json.dumps(compare(a, b, args.expected_extra), sort_keys=True))
        return 0
    except (ValueError, KeyError, OSError, UnicodeError, zipfile.BadZipFile) as exc:
        print("AUDIT_RED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
