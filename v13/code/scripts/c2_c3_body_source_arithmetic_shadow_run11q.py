#!/usr/bin/env python3
"""Run11Q source-bound posthoc arithmetic shadow scorer; never an authority gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

ORIGINAL_ZIP_SHA256 = "df680697f65f9879b7817179b8d4a2d1f8625656579c68f03c0268d599f6d4c4"
ORIGINAL_HEAD = "4f73e39db16d9ff4570dc6d3b4586160dc18d0a3"
FIXTURE_SHA256 = "74818535a13819a65d4d32801d704fecd7716ea99c112b33c3bca248f3442c36"
SCHEMA = "v13.c2_c3_body.source_arithmetic_shadow.v1"
MAX_ZIP_BYTES = 2_000_000


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def load_verified_zip(path, expected_sha=ORIGINAL_ZIP_SHA256):
    """Require pinned outer bytes, safe names, CRC and complete original inner manifest."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError("ZIP_MISSING_OR_OVERSIZE")
    blob = path.read_bytes()
    actual = _digest(blob)
    if actual != expected_sha:
        raise ValueError("ORIGINAL_ZIP_SHA_MISMATCH")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if (len(names) != len(set(names)) or "SHA256SUMS" not in names
                or "pilot/report.json" not in names or "HEAD.txt" not in names):
            raise ValueError("ZIP_MEMBERS_INVALID")
        for name in names:
            parts = PurePosixPath(name).parts
            if (not name or "\\" in name or name.startswith("/")
                    or ".." in parts or ":" in parts[0]):
                raise ValueError("UNSAFE_ZIP_MEMBER")
        if z.testzip() is not None:
            raise ValueError("ZIP_CRC_INVALID")
        manifest = {}
        for line in z.read("SHA256SUMS").decode("ascii").splitlines():
            fields = line.split(maxsplit=1)
            if len(fields) != 2 or not re.fullmatch(r"[0-9a-f]{64}", fields[0]):
                raise ValueError("MANIFEST_INVALID")
            name = fields[1].removeprefix("./")
            if name in manifest or name == "SHA256SUMS":
                raise ValueError("MANIFEST_DUPLICATE")
            manifest[name] = fields[0]
        if set(manifest) != set(names) - {"SHA256SUMS"}:
            raise ValueError("MANIFEST_INCOMPLETE")
        for name, sha in manifest.items():
            if _digest(z.read(name)) != sha:
                raise ValueError("MANIFEST_HASH_MISMATCH")
        if z.read("HEAD.txt").decode().strip() != ORIGINAL_HEAD:
            raise ValueError("ORIGINAL_HEAD_MISMATCH")
        report = json.loads(z.read("pilot/report.json"))
    if (report.get("schema") != "v13.c2_c3_body.auto_native_smoke.v1"
            or report.get("seed") != 47
            or report.get("fixture_sha256") != FIXTURE_SHA256):
        raise ValueError("ORIGINAL_REPORT_PIN_MISMATCH")
    fixtures = report.get("fixtures")
    rows = report.get("rows")
    if type(fixtures) is not list or type(rows) is not list or len(fixtures) != 3 or len(rows) != 3:
        raise ValueError("ORIGINAL_ROWS_INCOMPLETE")
    fixture_hash = _digest(json.dumps(fixtures, sort_keys=True, separators=(",", ":")).encode())
    if fixture_hash != FIXTURE_SHA256:
        raise ValueError("FIXTURE_CONTENT_CHANGED")
    ids = [f.get("project") for f in fixtures if isinstance(f, dict)]
    if len(set(ids)) != 3 or len(ids) != 3 or {r.get("fixture") for r in rows} != set(ids):
        raise ValueError("FIXTURE_ROW_MISMATCH")
    return report, actual


def _bounded_numbers(matches):
    numbers = set()
    for match in matches:
        value = int(match)
        if value > 1_000_000_000:
            raise ValueError("CLAIM_INTEGER_OUT_OF_RANGE")
        numbers.add(value)
    return numbers


def extract_remaining(text, option, other):
    """Narrow option-linked grammar; no bare numbers, costs or times."""
    if type(text) is not str or not text.strip():
        return set()
    name = re.escape(option)
    unit = r"(?:Euro|EUR|€)"
    patterns = (
        rf"(?<!\w){name}(?!\w)\s*:\s*(\d{{1,10}})\s*{unit}\s+remaining\b",
        rf"\bOption\s+{name}(?!\w)\s+leaves\s+(\d{{1,10}})\s*{unit}\b",
        rf"\bremaining\s+budget\s+for\s+Option\s+{name}(?!\w)\s+is\s+(\d{{1,10}})\s*{unit}\b",
    )
    found = []
    for pattern in patterns:
        found.extend(m.group(1) for m in re.finditer(pattern, text, re.IGNORECASE))
    # Strict second-clause coreference: same sentence must first state
    # the remaining budget for the *other* named option.
    clause = rf"\bfor\s+Option\s+{name}(?!\w)\s+it\s+is\s+(\d{{1,10}})\s*{unit}\b"
    anchor = rf"\bremaining\s+budget\s+for\s+Option\s+{re.escape(other)}(?!\w)\s+is\s+\d{{1,10}}\s*{unit}\b"
    for m in re.finditer(clause, text, re.IGNORECASE):
        sentence = re.split(r"[.!?\n]", text[:m.start()])[-1]
        if re.search(anchor, sentence, re.IGNORECASE):
            found.append(m.group(1))
    return _bounded_numbers(found)


def score_option(fixture, output, key):
    """Only source fixture arithmetic is authoritative."""
    if key not in ("a", "b"):
        raise ValueError("OPTION_KEY_INVALID")
    option = fixture[key]
    other = fixture["b" if key == "a" else "a"]
    budget, cost = fixture["budget"], fixture[key + "_cost"]
    if any(type(x) is not int or x < 0 or x > 1_000_000_000 for x in (budget, cost)):
        raise ValueError("SOURCE_ARITHMETIC_INVALID")
    expected = budget - cost
    if expected < 0:
        raise ValueError("SOURCE_NEGATIVE_REMAINDER")
    numbers = extract_remaining(output, option, other)
    status = ("UNSCORED" if not numbers else
              "CONTRADICTORY_CLAIMS" if len(numbers) > 1 else
              "MATCH" if next(iter(numbers)) == expected else
              "CONTRADICTS_SOURCE")
    return {"option": option, "expected_remainder": expected,
            "extracted_claims": sorted(numbers), "status": status}


def score_report(report, original_sha):
    fixtures = {f["project"]: f for f in report["fixtures"]}
    rows = []
    for item in report["rows"]:
        f = fixtures[item["fixture"]]
        output = item.get("final_output")
        scores = [score_option(f, output, key) for key in ("a", "b")]
        rows.append({"fixture": f["project"], "output_role": item.get("output_role"),
                     "scores": scores})
    totals = {key: sum(s["status"] == key for row in rows for s in row["scores"])
              for key in ("MATCH", "CONTRADICTS_SOURCE", "CONTRADICTORY_CLAIMS", "UNSCORED")}
    return {"schema": SCHEMA, "evidence_class": "LINUX_NATIVE_POSTHOC_SOURCE_BOUND_SHADOW",
            "original_zip_sha256": original_sha, "original_head": ORIGINAL_HEAD,
            "fixture_sha256": FIXTURE_SHA256, "rows": rows, "totals": totals,
            "total_options": sum(len(row["scores"]) for row in rows),
            "native_route_selection_proven": False, "utility_gate_pass": False,
            "production_activation": False, "age_authority": 0,
            "jepa_weight": 0, "redmi_measured": False,
            "whole_system_complete": False}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--original-zip", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists() or a.out.is_symlink():
        raise ValueError("REFUSE_OVERWRITE")
    report, sha = load_verified_zip(a.original_zip)
    result = score_report(report, sha)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"totals": result["totals"], "total_options": result["total_options"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
