"""Posthoc, read-only full-task diagnostic on the exact original Run12N ZIP.

Not a preregistered gate. Numeric points reuse frozen verified report; the
explicit faster-choice extractor is a conservative exploratory lexical probe.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

SCHEMA = "v13.run12n.fulltask.posthoc.readonly.v1"
ZIP_SHA256 = "c058f33d1055d838000cc31e27b6e6ba6d37f86caa8e7b0d15a643672d44c447"
FIXTURE_SHA256 = "94cce591dcf9ade126cfdb2d32261543c8334523b6d268295759d9ef7b691df1"
ARMS = ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY", "F_NATIVE_AUTO")
ORDER = tuple(ARMS[i:] + ARMS[:i] for i in range(4))
MAX_ZIP_BYTES = 10_000_000


def explicit_faster_claim(output: str, a: str, b: str) -> str:
    """Return named winner, ABSTAIN or CONTRADICTORY; no implicit math."""
    if not isinstance(output, str) or not output.strip():
        return "ABSTAIN"
    text = re.sub(r"[*_`]+", "", output).casefold()
    found = set()
    for name in (a, b):
        if not isinstance(name, str) or not name:
            raise ValueError("INVALID_NAME")
        label = re.escape(name.casefold())
        pats = (
            rf"(?<!\w){label}\s+(?:finishes|completes)\s+(?:sooner|first|earlier|faster)\b",
            rf"(?<!\w){label}\s+will\s+(?:finish|complete)\s+(?:sooner|first|earlier|faster)\b",
            rf"(?<!\w){label}\s+is\s+(?:the\s+)?(?:sooner|first|earlier|faster)\b",
            rf"(?<!\w){label}\s+takes\s+(?:fewer|less)\s+(?:days|time)\b",
        )
        if any(re.search(p, text) for p in pats):
            found.add(name)
    if len(found) > 1:
        return "CONTRADICTORY"
    return next(iter(found)) if found else "ABSTAIN"


def inspect_zip(path: Path) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or not (0 < path.stat().st_size <= MAX_ZIP_BYTES):
        raise ValueError("ZIP_MISSING_SYMLINK_OR_OVERSIZE")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha != ZIP_SHA256:
        raise ValueError("ORIGINAL_ZIP_HASH_MISMATCH")
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError("ZIP_CRC_RED")
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError("DUPLICATE_ZIP_ENTRY")
        manifest = z.read("SHA256SUMS").decode().splitlines()
        verified = set()
        for line in manifest:
            parts = line.split("  ", 1)
            if len(parts) != 2:
                raise ValueError("BAD_MANIFEST_LINE")
            want, name = parts
            name = name.removeprefix("./")
            if name in verified or name == "SHA256SUMS" or name not in names:
                raise ValueError("BAD_MANIFEST_ENTRY")
            if hashlib.sha256(z.read(name)).hexdigest() != want:
                raise ValueError("INNER_HASH_MISMATCH")
            verified.add(name)
        if verified != set(names) - {"SHA256SUMS"} or len(verified) != 60:
            raise ValueError("MANIFEST_COVERAGE_MISMATCH")
        report = json.loads(z.read("pilot/report.json"))
        cases = report.get("fixtures")
        if not isinstance(cases, list) or len(cases) != 4:
            raise ValueError("COHORT_CASES_MISMATCH")
        fixture_hash = hashlib.sha256(json.dumps(
            tuple(cases), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if (fixture_hash != FIXTURE_SHA256 or report.get("seed") != 197
                or report.get("all_native_structurally_valid") is not True
                or report.get("arms") != list(ARMS)
                or report.get("arm_order") != [list(a) for a in ORDER]):
            raise ValueError("FROZEN_REPORT_MISMATCH")
        rows = report.get("rows")
        if not isinstance(rows, list) or len(rows) != 16:
            raise ValueError("ROW_COUNT_MISMATCH")
        expected_raw = {f"pilot/raw/{i:02d}_{ORDER[i//4][i%4]}.json"
                        for i in range(16)}
        expected_pre = {f"pilot/preclose/{i:02d}_{ORDER[i//4][i%4]}.json"
                        for i in range(16)}
        expected_strict = {f"pilot/raw/{i:02d}_STRICT_ADMISSION.json"
                           for i in range(16) if ORDER[i//4][i%4] == "F_NATIVE_AUTO"}
        if ({n for n in names if n.startswith("pilot/raw/")}
                != expected_raw | expected_strict
                or {n for n in names if n.startswith("pilot/preclose/")} != expected_pre):
            raise ValueError("RAW_PRECLOSE_STRICT_MISMATCH")
        stats = {a: {"numeric_points": 0, "faster_correct": 0,
                     "faster_wrong": 0, "faster_abstain": 0,
                     "faster_contradictory": 0, "strict_full_task": 0}
                 for a in ARMS}
        details = []
        for i, row in enumerate(rows):
            case = cases[i // 4]
            arm = ORDER[i // 4][i % 4]
            raw = json.loads(z.read(f"pilot/raw/{i:02d}_{arm}.json"))
            if (row.get("index") != i or row.get("arm") != arm
                    or row.get("fixture") != case["project"]
                    or raw.get("final_output") != row.get("final_output")
                    or row.get("flags", {}).get("valid_native") is not True):
                raise ValueError("ROW_IDENTITY_OR_NATIVE_MISMATCH")
            expected = case["a"] if case["a_days"] < case["b_days"] else case["b"]
            claim = explicit_faster_claim(row["final_output"], case["a"], case["b"])
            status = ("ABSTAIN" if claim == "ABSTAIN" else
                      "CONTRADICTORY" if claim == "CONTRADICTORY" else
                      "CORRECT" if claim == expected else "WRONG")
            numeric = row["score"]["correct"]
            if type(numeric) is not int or not 0 <= numeric <= 2:
                raise ValueError("FROZEN_NUMERIC_SCORE_INVALID")
            d = stats[arm]
            d["numeric_points"] += numeric
            d["faster_" + status.lower()] += 1
            d["strict_full_task"] += int(numeric == 2 and status == "CORRECT")
            details.append({"index": i, "arm": arm, "project": case["project"],
                            "expected_faster": expected, "claim": claim,
                            "faster_status": status, "numeric_points": numeric})
    return {"schema": SCHEMA, "evidence": "POSTHOC_READONLY_NOT_A_GATE",
            "source_zip_sha256": sha, "manifest_verified": 60,
            "native_rows": 16, "preclose_rows": 16, "strict_c2": 4,
            "stats": stats, "rows": details,
            "baseline": "Exact integer subtraction and min(days) yields 4/4 full tasks; task-specific deterministic control, not an LLM.",
            "limitations": "Explicit lexical faster claims only; no negation, pragmatics, or semantic entailment calibration. Frozen numeric scorer unchanged.",
            "step2_gate_promoted": False, "comparative_utility_proven": False,
            "redmi_measured": False, "whole_system_complete": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(inspect_zip(a.zip), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()