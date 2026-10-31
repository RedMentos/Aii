#!/usr/bin/env python3
"""Bounded read-only W7S Actions raw ZIP attestation; never runs native code."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

from scripts import verify_w7s_full_gates as gates

EXPECTED_HEAD = "676ee271bc5f156f911027c3ae203b649f6e3b6a"
STAGES = ("PINS", "VENV", "DEPS", "TEST", "REALFILE",
          "REPORT_CHECK", "COMPILE", "PRIVACY", "DIFF")
REQUIRED_PINS = {
    "v13/code/scripts/w7s_world_jepa_disjoint_support_real.py":
        "563030370bd30688138c0d31c32fe6494abfc817",
    "v13/code/tests/test_w7s_world_jepa_disjoint_support.py":
        "afff18393c1522f7e4c3987154dd6af5251caea0",
    "v13/code/docs/WORLD_JEPA_W7_DISJOINT_SUPPORT_PREREG_20261031.md":
        "90d171529808d5b42af89d8556e2d53c061332b7",
    "v13/code/v13/world_jepa.py":
        "99a686a131a1bdc89efe0d0cf9610ec54cbd853b",
    "v13/code/scripts/z12b_world_jepa.py":
        "2fd1366dc1b6d8c02803ee3254020f70e5bf3eb4",
    "v13/code/v13/world_jepa_slot_candidate.py":
        "67e14e0d03c50c4767b74d5b02a819a95c6cc262",
    "v13/code/v13/world_jepa_fullslot_candidate.py":
        "51bc5260cde8db3bc6cf7924a7a089a5cdfe5fd0",
    "v13/code/scripts/run35_world_jepa_slot_alignment_real.py":
        "219bf7233cb91c746c89a60f9b7789dc3b5ca9ef",
    "v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md":
        "218464b12a2d27d92524c751922fa8e1c3fb0ea7",
}
MAX_MEMBERS = 200000
MAX_UNCOMPRESSED = 2 * 1024**3
MAX_JSON = 8 * 1024**2


def need(ok, label):
    if not ok:
        raise ValueError("W7S_ZIP_" + label)


def digest_stream(stream):
    h = hashlib.sha256()
    while True:
        block = stream.read(1024 * 1024)
        if not block:
            break
        h.update(block)
    return h.hexdigest()


def audit(path):
    path = Path(path)
    with path.open("rb") as stream:
        archive_sha = digest_stream(stream)
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [i.filename for i in infos if not i.is_dir()]
        need(0 < len(names) <= MAX_MEMBERS, "MEMBER_COUNT")
        need(len(names) == len(set(names)), "DUPLICATE_MEMBER")
        need(sum(i.file_size for i in infos) <= MAX_UNCOMPRESSED,
             "UNCOMPRESSED_BUDGET")
        for name in names:
            parts = PurePosixPath(name).parts
            need(name and not name.startswith("/")
                 and "\\" not in name and ".." not in parts
                 and not name.startswith("./../"), "PATH_TRAVERSAL")
        need(z.testzip() is None, "CRC")
        need("SHA256SUMS" in names, "MISSING_MANIFEST")
        manifest = {}
        for line in z.read("SHA256SUMS").decode("utf-8").splitlines():
            want, sep, name = line.partition("  ")
            need(bool(sep) and len(want) == 64
                 and all(c in "0123456789abcdef" for c in want),
                 "MANIFEST_GRAMMAR")
            name = name.removeprefix("./")
            need(name not in manifest, "MANIFEST_DUPLICATE")
            manifest[name] = want
        need(set(manifest) == set(names) - {"SHA256SUMS"},
             "MANIFEST_COVERAGE")
        for name, want in manifest.items():
            with z.open(name) as stream:
                need(digest_stream(stream) == want, "SHA256_" + name[:60])
        need(z.read("HEAD.txt").decode().strip() == EXPECTED_HEAD,
             "HEAD_IDENTITY")
        pins = {}
        for line in z.read("PINS.txt").decode().splitlines():
            want, sep, name = line.partition(" ")
            need(bool(sep) and name not in pins, "PINS_GRAMMAR")
            pins[name] = want
        need(all(pins.get(name) == sha for name, sha in REQUIRED_PINS.items()),
             "FROZEN_PINS")
        receipts = {}
        for line in z.read("PINS_RAW.log").decode().splitlines():
            parts = line.split(" ", 2)
            need(len(parts) == 3, "PIN_RECEIPT_GRAMMAR")
            want, got, name = parts
            need(name not in receipts and pins.get(name) == want == got,
                 "PIN_RECEIPT_MISMATCH")
            receipts[name] = got
        need(receipts == pins, "PIN_RECEIPT_COVERAGE")
        exits = {}
        for stage in STAGES:
            raw = z.read(stage + "_EXIT.txt").decode().strip()
            need(raw.isdecimal(), "STAGE_GRAMMAR_" + stage)
            exits[stage] = int(raw)
        need(all(code == 0 for code in exits.values()), "STAGE_RED")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = root / "RESULT.json"
            work = root / "work"
            work.mkdir()
            required = ["RESULT.json"] + [
                f"work/{arm}-{seed}-RESULT.json"
                for arm in gates.base.ARMS for seed in gates.base.SEEDS]
            for name in required:
                need(name in names, "ROW_MISSING")
                info = z.getinfo(name)
                need(0 < info.file_size <= MAX_JSON, "ROW_SIZE")
                dest = result if name == "RESULT.json" else work / Path(name).name
                with z.open(name) as stream, dest.open("wb") as output:
                    while True:
                        block = stream.read(1024 * 1024)
                        if not block:
                            break
                        output.write(block)
            verdict = gates.verify(result, work)
            need(verdict["status"] ==
                 "W7S_W1_W7_FULL_RAW_REPLAY_VERIFIED_SHADOW",
                 "FULL_GATE_REPLAY_RED")
    return {
        "status": "W7S_RAWZIP_SELF_CONSISTENT_SHADOW",
        "archive_sha256": archive_sha,
        "inner_sha256_verified": len(manifest),
        "stage_exits": exits,
        "source_head": EXPECTED_HEAD,
        "w1_w7_raw_replay": True,
        "native_proof": False,
        "redmi_measured": False,
        "promotion": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    args = p.parse_args()
    try:
        result = audit(args.zip)
    except Exception as exc:
        result = {"status": "W7S_RAWZIP_RED",
                  "reason": type(exc).__name__ + ":" + str(exc)[:150],
                  "native_proof": False, "redmi_measured": False,
                  "promotion": False}
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    raise SystemExit(0 if result["status"] ==
                     "W7S_RAWZIP_SELF_CONSISTENT_SHADOW" else 1)


if __name__ == "__main__":
    main()
