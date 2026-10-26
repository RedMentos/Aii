#!/usr/bin/env python3
"""Run580: independently classify immutable Run568 native RED artifact; never rerun models."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import zipfile

ORIGINAL_ARTIFACT_ID = 12671404476
ORIGINAL_SHA256 = "9652c6b03d7918ef148b85ec8f18d70bce78a99b959de2382bc79cd2bfc4288e"
ORIGINAL_WORKFLOW = 40367841707
ORIGINAL_HEAD = "db6047b267edceed9055d9702a2810492ffbfe8a"
FLAGS = ("DEPS", "FIXTURE", "BOOTSTRAP", "NATIVE", "AUDIT", "SAFE", "PRIVACY")
NAME = re.compile(r"RUN568_[A-Za-z0-9_.-]+\Z")
SHA_LINE = re.compile(r"([0-9a-f]{64})  (?:\./)?(RUN568_[A-Za-z0-9_.-]+)\Z")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _members(path):
    data = Path(path).read_bytes()
    if len(data) > 50_000_000:
        raise ValueError("ORIGINAL_ARTIFACT_TOO_LARGE")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        names = [m.filename for m in members]
        if len(names) != len(set(names)):
            raise ValueError("DUPLICATE_MEMBER")
        if not names or any(
            not NAME.fullmatch(name) or "/" in name or "\\" in name or ".." in name
            or info.is_dir() or stat.S_ISLNK(info.external_attr >> 16)
            for name, info in zip(names, members)
        ):
            raise ValueError("UNSAFE_ORIGINAL_MEMBER")
        if sum(m.file_size for m in members) > 100_000_000:
            raise ValueError("ORIGINAL_UNCOMPRESSED_TOO_LARGE")
        if archive.testzip() is not None:
            raise ValueError("ORIGINAL_CRC_FAIL")
        return {name: archive.read(name) for name in names}


def _closure(files):
    manifest = files.get("RUN568_SHA256SUMS.txt")
    if manifest is None:
        raise ValueError("ORIGINAL_SHA_MANIFEST_MISSING")
    lines = manifest.decode("utf-8").splitlines()
    expected = {}
    for line in lines:
        match = SHA_LINE.fullmatch(line)
        if not match or match.group(2) in expected:
            raise ValueError("ORIGINAL_SHA_MANIFEST_INVALID")
        expected[match.group(2)] = match.group(1)
    if set(expected) != set(files) - {"RUN568_SHA256SUMS.txt"}:
        raise ValueError("ORIGINAL_SHA_MANIFEST_INCOMPLETE")
    if any(digest(files[name]) != hexdigest for name, hexdigest in expected.items()):
        raise ValueError("ORIGINAL_SHA_CLOSURE_CHANGED")
    return expected


def _diagnostics(data):
    text = data.decode("utf-8", errors="replace")
    selected = []
    for line in text.splitlines():
        if re.search(r"(?:Traceback|[A-Za-z_]+(?:Error|Exception):|timed out|Timeout|Killed|signal)", line, re.I):
            # Bounded diagnostics; avoid publishing full native logs or absolute host paths.
            clean = re.sub(r"/(?:home|tmp|data|mnt)/[^\s:]+", "<PATH>", line.strip())
            clean = re.sub(r"(?i)(token|password|secret|key)=\S+", r"\1=<REDACTED>", clean)
            selected.append(clean[:220])
    return {"sha256": digest(data), "bytes": len(data),
            "line_count": len(text.splitlines()), "bounded_error_lines": selected[-12:]}


def audit(path, expected_sha=ORIGINAL_SHA256, require_red=True):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("ORIGINAL_ARCHIVE_MISSING_OR_SYMLINK")
    outer = digest(path.read_bytes())
    if outer != expected_sha:
        raise ValueError("ORIGINAL_OUTER_SHA256_CHANGED")
    files = _members(path)
    closure = _closure(files)
    exits = {}
    for name in FLAGS:
        raw = files.get(f"RUN568_{name}_EXIT.txt")
        if raw is None or not re.fullmatch(rb"[0-9]+\s*", raw):
            raise ValueError("ORIGINAL_EXIT_MISSING_OR_INVALID:" + name)
        exits[name] = int(raw.strip())
    nonzero = [name for name, value in exits.items() if value != 0]
    if require_red and not nonzero:
        raise ValueError("ORIGINAL_NOT_RED")
    logs = {}
    for stage in ("NATIVE", "AUDIT", "BOOTSTRAP"):
        logs[stage] = _diagnostics(files.get(f"RUN568_{stage}_RAW.log", b""))
    progress = files.get("RUN568_BATCH_PROGRESS.jsonl", b"")
    return {
        "schema": "V13_RUN580_ORIGINAL_NATIVE_RED_INDEPENDENT_AUDIT_V1",
        "status": "ORIGINAL_NATIVE_RED_CONFIRMED" if nonzero else "ORIGINAL_ALL_ZERO_NOT_RED",
        "original_run": ORIGINAL_WORKFLOW, "original_head": ORIGINAL_HEAD,
        "original_artifact_id": ORIGINAL_ARTIFACT_ID,
        "original_outer_sha256": outer,
        "original_member_count": len(files),
        "original_member_sha256_closed": len(closure),
        "original_exit_flags": exits, "nonzero_stages": nonzero,
        "original_progress_sha256": digest(progress) if progress else None,
        "original_progress_lines": len(progress.splitlines()),
        "logs": logs, "native_attempted": bool(logs["NATIVE"]["bytes"]),
        "native_executed_independently_verified": False,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "b3_l1": "FAIL", "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False,
        "claim_limit": "Original artifact integrity and RED classification only; no native rerun or independent process proof"
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-zip", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.original_zip)
    if args.report.exists() or args.report.is_symlink():
        raise ValueError("REPORT_ALREADY_EXISTS")
    with args.report.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({key: result[key] for key in
                      ("status", "original_exit_flags", "nonzero_stages",
                       "original_progress_lines", "native_attempted",
                       "native_executed_independently_verified")}, sort_keys=True))


if __name__ == "__main__":
    main()
