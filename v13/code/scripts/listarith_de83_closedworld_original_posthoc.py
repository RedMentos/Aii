"""Read-only, posthoc closed-world replay of the ORIGINAL seed83 native ZIP.

No native inference, no model downloads, no change to original scorer.
The original ZIP bytes are hash-pinned before any extraction; the original
independent raw verifier runs before any candidate comparison.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import tempfile
import zipfile
from io import BytesIO

from scripts import listarith_de83_native_shadow_audit as original
from v13.agi import listarith_de_closedworld_candidate as candidate

ORIGINAL_ZIP_SHA256 = "e92fda4b20a0ba01e533d1b2a343091fb4f46bebe7c9e8a60efdf3f2ca667f57"
ORIGINAL_ARTIFACT_ID = 12958586993
ORIGINAL_ACTIONS_ID = 41013265710
EXPECTED_INNER_HASHES = 48
FIXTURE_BLOB = "cc052aa9eaecd213124f9c79df15f30637c5a80c"
BASELINE_BLOB = "25cacd7388e5464dd814f4b18c545e2ec2f78b54"
GATES = ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
         "redmi_measured", "whole_system_complete")


def git_blob(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _safe_name(info):
    name = info.filename
    path = PurePosixPath(name)
    if (not name or "\\" in name or path.is_absolute()
            or any(p in ("", ".", "..") for p in path.parts)
            or name.endswith("/")):
        raise ValueError("ZIP_UNSAFE_PATH")
    mode = (info.external_attr >> 16) & 0o170000
    if mode == stat.S_IFLNK:
        raise ValueError("ZIP_SYMLINK_REJECTED")
    return name


def verified_members(data, expected_sha=ORIGINAL_ZIP_SHA256):
    """Return closed, CRC/hash-verified file bytes, never extracted paths."""
    if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() != expected_sha:
        raise ValueError("ORIGINAL_ZIP_SHA256_MISMATCH")
    with zipfile.ZipFile(BytesIO(data)) as z:
        infos = z.infolist()
        names = [_safe_name(info) for info in infos]
        if len(names) != len(set(names)):
            raise ValueError("ZIP_DUPLICATE_NAME")
        if "SHA256SUMS" not in names:
            raise ValueError("ZIP_MANIFEST_MISSING")
        if z.testzip() is not None:
            raise ValueError("ZIP_CRC_RED")
        members = {info.filename: z.read(info) for info in infos}
    lines = members["SHA256SUMS"].decode("utf-8").splitlines()
    if len(lines) != EXPECTED_INNER_HASHES:
        raise ValueError("INNER_HASH_COUNT_RED")
    claimed = {}
    for line in lines:
        if "  ./" not in line:
            raise ValueError("INNER_HASH_FORMAT_RED")
        digest, path = line.split("  ./", 1)
        if (len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)
                or path in claimed):
            raise ValueError("INNER_HASH_FORMAT_RED")
        claimed[path] = digest
    if set(claimed) != set(members) - {"SHA256SUMS"}:
        raise ValueError("INNER_MANIFEST_COVERAGE_RED")
    for name, want in claimed.items():
        if hashlib.sha256(members[name]).hexdigest() != want:
            raise ValueError("INNER_HASH_MISMATCH:" + name)
    if len([n for n in members if n.startswith("pilot/raw/") and n.endswith(".json")]) != 24:
        raise ValueError("NATIVE_RAW_ROW_COUNT_RED")
    return members


def audit_zip_bytes(data):
    if git_blob(original.FIXTURE) != FIXTURE_BLOB:
        raise ValueError("FROZEN_SEED83_FIXTURE_CHANGED")
    from v13.agi import listarith_de_shadow_pipeline as baseline
    if git_blob(Path(baseline.__file__)) != BASELINE_BLOB:
        raise ValueError("FROZEN_BASELINE_CHANGED")
    members = verified_members(data)
    with tempfile.TemporaryDirectory(prefix="v13-de83-posthoc-") as td:
        root = Path(td)
        for name, raw in members.items():
            dest = root.joinpath(*PurePosixPath(name).parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        original_report = original.replay(root / "pilot")
        if (original_report["native_status_original"] != "NATIVE_DE83_SHADOW_PILOT_SIGNAL"
                or original_report["native_completed"] != 24
                or original_report["supported_correct"] != 15
                or original_report["supported_wrong_emitted"] != 0
                or original_report["unsupported_false_positive"] != 0
                or original_report["all_processes_reaped"] is not True):
            raise ValueError("ORIGINAL_NATIVE_SCORE_OR_PROCESS_RED")
        fixture = json.loads(original.FIXTURE.read_text(encoding="utf-8"))["rows"]
        details = []
        for i, expected in enumerate(fixture):
            name = "%02d_%s.json" % (i, expected["id"])
            raw = json.loads(members["pilot/raw/" + name])
            before = raw["shadow"]
            after = candidate.evaluate(raw["text"], raw["raw_output"])
            if before["status"] == "SHADOW_ABSTAIN" and after["status"] != "SHADOW_ABSTAIN":
                raise ValueError("BASELINE_ABSTENTION_UPGRADED:" + expected["id"])
            for gate in GATES:
                if after[gate] is not False:
                    raise ValueError("CANDIDATE_GATE_PROMOTED:" + expected["id"])
            if after["jepa_weight"] != 0 or after["authority"] != "SHADOW_ONLY":
                raise ValueError("CANDIDATE_AUTHORITY_CHANGED:" + expected["id"])
            score = original.independent_score(expected, after)
            details.append({"id": expected["id"],
                            "supported": expected["expected_operation"] is not None,
                            "original_status": before["status"],
                            "candidate_status": after["status"],
                            "candidate_reason": after.get("reason"),
                            "candidate_operation": after.get("operation"),
                            "candidate_value": after.get("value"),
                            "candidate_exact": score["correct"],
                            "candidate_wrong_emitted": score["wrong_emitted"],
                            "candidate_unsupported_false_positive": score["unsupported_false_positive"]})
    supported_exact = sum(r["candidate_exact"] for r in details if r["supported"])
    supported_abstain = sum(r["candidate_status"] == "SHADOW_ABSTAIN"
                            for r in details if r["supported"])
    unsupported_abstain = sum(r["candidate_status"] == "SHADOW_ABSTAIN"
                              for r in details if not r["supported"])
    wrong = sum(r["candidate_wrong_emitted"] for r in details)
    fp = sum(r["candidate_unsupported_false_positive"] for r in details)
    return {"schema": "v13.de83.closedworld_original_posthoc.v1",
            "source_zip_sha256": ORIGINAL_ZIP_SHA256,
            "original_artifact_id": ORIGINAL_ARTIFACT_ID,
            "original_actions_id": ORIGINAL_ACTIONS_ID,
            "original_native_status": original_report["native_status_original"],
            "original_supported_exact": original_report["supported_correct"],
            "candidate_supported_exact": supported_exact,
            "candidate_supported_abstain": supported_abstain,
            "candidate_unsupported_abstain": unsupported_abstain,
            "candidate_wrong_emitted": wrong,
            "candidate_unsupported_false_positive": fp,
            "original_native_rows": original_report["native_completed"],
            "inner_hashes_verified": EXPECTED_INNER_HASHES,
            "evidence_level": "POSTHOC_SOFTWARE_ON_VERIFIED_HISTORICAL_LINUX_NATIVE_RAW",
            "new_native_calls": 0,
            "live_tool_execution": False,
            "external_action_authority": False,
            "step2_gate_promoted": False,
            "b3_promoted": False,
            "body_jepa_available": False,
            "jepa_weight": 0,
            "redmi_measured": False,
            "whole_system_complete": False,
            "rows": details}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError("FRESH_REPORT_REQUIRED")
    report = audit_zip_bytes(args.zip.read_bytes())
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True,
                                   ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"},
                     sort_keys=True))


if __name__ == "__main__":
    main()
