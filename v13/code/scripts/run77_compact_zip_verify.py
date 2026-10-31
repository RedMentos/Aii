#!/usr/bin/env python3
"""Independent bounded Run77 compact GitHub Actions artifact ZIP auditor.

Does not trust CI success, ZIP names, stored SHA256SUMS, or report status.
Engineering evidence only; no scientific/STEP2/Redmi promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import PurePosixPath, Path
import re
import zipfile

from scripts.run77_native_forensic_diagnostic import diagnose

MAX_ZIP_BYTES = 25 * 1024 * 1024
MAX_UNCOMPRESSED = 40 * 1024 * 1024
MAX_ENTRIES = 100
HEX = re.compile(r"^[0-9a-f]{64}$")
ROW_NAME = re.compile(r"^raw_rows/[A-Za-z0-9_]+\.json$")
AUDIT_NAME = re.compile(r"^store_audits/[A-Za-z0-9_]+\.json$")
STANDARD = {
    "HEAD.txt", "PINS.txt", "PINS_RAW.log", "report.json",
    "DIAG.json", "SHA256SUMS", "SIZE_RAW.log",
}
RECEIPTS = (
    "ANCESTRY", "PINS", "VENV", "DEPS", "TEST", "LEGACY_TEST",
    "BOOTSTRAP", "NATIVE", "VERIFY", "DIAG", "AUDIT", "COMPILE",
    "PRIVACY", "DIFF", "SIZE",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit_zip(raw):
    findings = []

    def red(code):
        if code not in findings:
            findings.append(code)

    if len(raw) > MAX_ZIP_BYTES:
        return {"status": "COMPACT_ZIP_OVERSIZE_RED",
                "findings": ["ZIP_BYTES_OVER_BUDGET"], "zip_sha256": sha(raw)}
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        infos = archive.infolist()
    except Exception:
        return {"status": "COMPACT_ZIP_INVALID_RED",
                "findings": ["ZIP_PARSE_RED"], "zip_sha256": sha(raw)}
    if len(infos) > MAX_ENTRIES:
        red("TOO_MANY_ENTRIES")
    total = 0
    data = {}
    for info in infos:
        name = info.filename
        p = PurePosixPath(name)
        if (name.endswith("/") or name.startswith("/")
                or ".." in p.parts or "\\" in name
                or (info.external_attr >> 16) & 0o170000 == 0o120000):
            red("UNSAFE_ZIP_MEMBER")
            continue
        if (name not in STANDARD
                and not name.endswith("_EXIT.txt")
                and not name.endswith("_RAW.log")
                and not ROW_NAME.fullmatch(name)
                and not AUDIT_NAME.fullmatch(name)):
            red("UNEXPECTED_ZIP_MEMBER")
        if name in data:
            red("DUPLICATE_ZIP_MEMBER")
            continue
        total += info.file_size
        if total > MAX_UNCOMPRESSED:
            red("UNCOMPRESSED_BUDGET_RED")
            break
        if info.file_size > MAX_UNCOMPRESSED:
            red("GIANT_ZIP_MEMBER")
            continue
        try:
            data[name] = archive.read(info)
        except Exception:
            red("ZIP_MEMBER_READ_RED")
    if archive.testzip() is not None:
        red("ZIP_CRC_RED")
    required = {"report.json", "DIAG.json", "HEAD.txt",
                "PINS.txt", "PINS_RAW.log", "SHA256SUMS"}
    required |= {s + "_EXIT.txt" for s in RECEIPTS}
    if not required.issubset(data):
        red("REQUIRED_EVIDENCE_MISSING")
    row_files = sorted(x for x in data if ROW_NAME.fullmatch(x))
    audit_files = sorted(x for x in data if AUDIT_NAME.fullmatch(x))
    if len(row_files) != 12:
        red("RAW_ROW_COUNT_RED")
    if len(audit_files) != 12:
        red("STORE_AUDIT_COUNT_RED")
    hashes = {}
    try:
        lines = data["SHA256SUMS"].decode("utf-8").splitlines()
        for line in lines:
            m = re.fullmatch(r"([0-9a-f]{64})\s+\./(.+)", line)
            if not m:
                red("SHA_MANIFEST_FORMAT_RED")
                continue
            digest, path = m.groups()
            if path in hashes:
                red("SHA_MANIFEST_DUPLICATE_RED")
            hashes[path] = digest
            if path not in data or sha(data[path]) != digest:
                red("SHA_MANIFEST_MISMATCH_RED")
        missing = set(data) - set(hashes) - {"SHA256SUMS"}
        if missing:
            red("UNHASHED_MEMBERS_RED")
    except Exception:
        red("SHA_MANIFEST_MISSING_RED")
    for s in RECEIPTS:
        key = s + "_EXIT.txt"
        if key not in data:
            continue
        code = data[key].decode("utf-8", errors="replace").strip()
        if code != "0":
            red("RECEIPT_" + s + "_RED")
    report = None
    try:
        report = json.loads(data["report.json"])
        diagnostic = diagnose(report)
        if diagnostic["status"] != "INDEPENDENT_RUN77_NATIVE_REPARSE_PASS":
            red("ORIGINAL_REPORT_VERIFIER_RED")
        archived_diag = json.loads(data["DIAG.json"])
        if archived_diag != diagnostic:
            red("FORENSIC_DIAGNOSTIC_MISMATCH_RED")
        for row in report.get("rows", []):
            key = row.get("project", "") + "_" + row.get("arm", "")
            path = "raw_rows/" + key + ".json"
            if path not in data or json.loads(data[path]) != row:
                red("RAW_ROW_REPORT_DIVERGENCE_RED")
    except Exception:
        red("REPORT_OR_DIAGNOSTIC_PARSE_RED")
    for path in audit_files:
        try:
            if json.loads(data[path]).get("ok") is not True:
                red("CLOSED_STORE_AUDIT_RED")
        except Exception:
            red("CLOSED_STORE_AUDIT_PARSE_RED")
    return {
        "status": ("COMPACT_EVIDENCE_VERIFIED_ENGINEERING_ONLY"
                   if not findings else "COMPACT_EVIDENCE_RED"),
        "findings": findings,
        "zip_sha256": sha(raw),
        "entries": len(data),
        "sha256sum_entries": len(hashes),
        "raw_rows": len(row_files),
        "store_audits": len(audit_files),
        "native_report_status": (report or {}).get("status"),
        "step2_promoted": False,
        "redmi_measured": False,
        "whole_system_complete": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    result = audit_zip(args.artifact.read_bytes())
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] ==
                     "COMPACT_EVIDENCE_VERIFIED_ENGINEERING_ONLY" else 1)


if __name__ == "__main__":
    main()
