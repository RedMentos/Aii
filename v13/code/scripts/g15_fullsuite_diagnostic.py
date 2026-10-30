"""G15: offline exact-original full-suite ZIP comparator; diagnostic, never a waiver.

No Runtime imports, native/model calls, downloads, or gate promotion.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile

REQUIRED_STAGES = frozenset({
    "CANON", "VENV", "DEPS", "TORCH", "TRANSFORMERS", "PEFT",
    "PIP_CHECK", "TORCH_IMPORT", "TRANSFORMERS_IMPORT", "PEFT_IMPORT",
    "COMPILE", "PRIVACY", "DIFF",
})
MAX_ZIP = 64 * 1024 * 1024
MAX_MEMBER = 32 * 1024 * 1024
MAX_MEMBERS = 512
IDENTITY = re.compile(r"^(ERROR|FAIL): (.+)$", re.M)
SUMMARY = re.compile(r"^Ran (\d+) tests in [0-9.]+s$", re.M)


def _hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_archive(path, expected_sha, expected_head):
    path = Path(path)
    if not 0 < path.stat().st_size <= MAX_ZIP:
        raise ValueError("ZIP_SIZE_RED")
    if (type(expected_sha) is not str or not re.fullmatch("[0-9a-f]{64}", expected_sha)
            or _hash_file(path) != expected_sha):
        raise ValueError("ZIP_SHA256_RED")
    if type(expected_head) is not str or not re.fullmatch("[0-9a-f]{40}", expected_head):
        raise ValueError("HEAD_PIN_RED")
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [info.filename for info in infos]
        if (not 0 < len(infos) <= MAX_MEMBERS or len(names) != len(set(names))
                or any(info.is_dir() or info.file_size > MAX_MEMBER
                       or name.startswith("/") or "\\" in name
                       or any(part in ("", ".", "..") for part in name.split("/"))
                       for name, info in zip(names, infos))
                or sum(info.file_size for info in infos) > MAX_ZIP):
            raise ValueError("ZIP_ENTRIES_RED")
        if z.testzip() is not None:
            raise ValueError("ZIP_CRC_RED")
        if "SHA256SUMS" not in names:
            raise ValueError("INNER_MANIFEST_MISSING")
        manifest = z.read("SHA256SUMS").decode("utf-8")
        checks = {}
        for line in manifest.splitlines():
            if "  " not in line:
                raise ValueError("INNER_MANIFEST_SYNTAX_RED")
            digest, name = line.split("  ", 1)
            name = name.removeprefix("./")
            if (not re.fullmatch("[0-9a-f]{64}", digest) or name in checks
                    or name == "SHA256SUMS" or name not in names):
                raise ValueError("INNER_MANIFEST_IDENTITY_RED")
            checks[name] = digest
        if set(checks) != set(names) - {"SHA256SUMS"}:
            raise ValueError("INNER_MANIFEST_COVERAGE_RED")
        for name, digest in checks.items():
            if hashlib.sha256(z.read(name)).hexdigest() != digest:
                raise ValueError("INNER_HASH_RED")
        head = z.read("HEAD.txt").decode("ascii").strip()
        if head != expected_head:
            raise ValueError("HEAD_MISMATCH_RED")
        stages = {}
        for name in names:
            if name.endswith("_EXIT.txt"):
                stage = name.removesuffix("_EXIT.txt")
                value = z.read(name).decode("ascii").strip()
                if not re.fullmatch("[0-9]{1,3}", value):
                    raise ValueError("STAGE_EXIT_SYNTAX_RED")
                stages[stage] = int(value)
        if not REQUIRED_STAGES <= set(stages) or "FULL" not in stages:
            raise ValueError("STAGE_MISSING_RED")
        if any(stages[s] != 0 for s in REQUIRED_STAGES):
            raise ValueError("NON_FULL_STAGE_RED")
        raw = z.read("FULL_RAW.log").decode("utf-8", errors="replace")
        summaries = SUMMARY.findall(raw)
        if not summaries:
            raise ValueError("FULL_SUMMARY_MISSING")
        identities = Counter(IDENTITY.findall(raw))
        if stages["FULL"] == 0 and identities:
            raise ValueError("FALSE_GREEN_WITH_FAILURE_IDENTITIES")
        return {
            "sha256": expected_sha, "head": head, "full_exit": stages["FULL"],
            "test_count": int(summaries[-1]), "identities": identities,
            "identity_count": sum(identities.values()),
            "inner_hash_count": len(checks),
        }


def _items(counter):
    return [
        {"kind": kind, "identity": name, "count": count}
        for (kind, name), count in sorted(counter.items())
    ]


def compare(baseline_zip, candidate_zip, baseline_sha256, candidate_sha256,
            baseline_head, candidate_head):
    """Returns evidence status, not permission to promote any V13 gate."""
    common = {
        "evidence_level": "SOFTWARE_UNFILTERED_DIAGNOSTIC_ONLY",
        "age0": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
        "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "canonical_architecture_complete": False,
        "user_full_scope_complete": False,
    }
    try:
        a = _read_archive(baseline_zip, baseline_sha256, baseline_head)
        b = _read_archive(candidate_zip, candidate_sha256, candidate_head)
        if a["full_exit"] == 0:
            raise ValueError("BASELINE_MUST_BE_HISTORICAL_RED")
        added = b["identities"] - a["identities"]
        removed = a["identities"] - b["identities"]
        if b["full_exit"] == 0:
            status = "FULL_PASS"
        elif not added and not removed:
            status = "HISTORICAL_RED_SAME_IDENTITIES"
        else:
            status = "RED_CHANGED_IDENTITIES"
        return {
            **common, "status": status, "evidence_valid": True,
            "software_suite_gate_pass": status == "FULL_PASS",
            "baseline": {k: v for k, v in a.items() if k != "identities"},
            "candidate": {k: v for k, v in b.items() if k != "identities"},
            "added_failure_identities": _items(added),
            "removed_failure_identities": _items(removed),
        }
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile,
            zipfile.LargeZipFile, RuntimeError, KeyError) as exc:
        return {
            **common, "status": "INTEGRITY_RED", "evidence_valid": False,
            "software_suite_gate_pass": False,
            "reason": str(exc) if type(exc) is ValueError else type(exc).__name__,
            "added_failure_identities": [], "removed_failure_identities": [],
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--baseline-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--baseline-head", required=True)
    parser.add_argument("--candidate-head", required=True)
    args = parser.parse_args(argv)
    result = compare(args.baseline, args.candidate,
                     args.baseline_sha256, args.candidate_sha256,
                     args.baseline_head, args.candidate_head)
    print(json.dumps(result, sort_keys=True))
    return 2 if not result["evidence_valid"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
