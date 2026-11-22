"""Run26 read-only, fail-closed paired coverage of original closed AG12 native ZIPs.

Oracle unions are diagnostic upper bounds, NOT actual B1/B2/JEF fusion.
No holdout prompts, answers or per-item IDs are exported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

from v13.agi.generality import build_suite

C3_HEAD = "f86c93b40d84d66a05bad0fa672a1f35bb8ac93e"
BODIES_HEAD = "5a7262bd23592cad69ea1af2b266c90383268be9"
RUNNER_SHA = "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443"
RUNNER_BINARY_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
MODELS = {
    "c3": ("C3_LANGUAGE", "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"),
    "b1": ("B1_DETAIL", "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1"),
    "b2": ("B2_GIST", "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf"),
}
STAGES = ("PINS", "VENV", "DEPS", "TEST", "NATIVE",
          "REPORT_CHECK", "COMPILE", "PRIVACY", "DIFF")
MAX_UNCOMPRESSED = 10 * 1024 * 1024


class EvidenceError(ValueError):
    pass


def _require(ok, reason):
    if not ok:
        raise EvidenceError("RUN26_" + reason + "_RED")


def _hash_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _zip(path, expected_sha, expected_head):
    _require(type(expected_sha) is str and re.fullmatch("[0-9a-f]{64}", expected_sha),
             "INPUT_SHA_FORMAT")
    _require(_hash_file(path) == expected_sha, "ORIGINAL_ZIP_SHA")
    z = zipfile.ZipFile(path)
    try:
        members = z.infolist()
        names = [m.filename for m in members]
        _require(len(names) == len(set(names)) and "SHA256SUMS" in names, "ZIP_MEMBERS")
        _require(sum(m.file_size for m in members) <= MAX_UNCOMPRESSED, "ZIP_SIZE")
        for m in members:
            parts = PurePosixPath(m.filename).parts
            _require(not m.is_dir() and not m.filename.startswith("/")
                     and "\\" not in m.filename and ".." not in parts
                     and not stat.S_ISLNK(m.external_attr >> 16), "ZIP_PATH")
        _require(z.testzip() is None, "ZIP_CRC")
        listed = {}
        for line in z.read("SHA256SUMS").decode("utf-8").splitlines():
            bits = line.split("  ", 1)
            _require(len(bits) == 2, "MANIFEST_FORMAT")
            digest, path_ = bits
            name = path_.removeprefix("./")
            _require(re.fullmatch("[0-9a-f]{64}", digest) is not None
                     and name not in listed, "MANIFEST_ENTRY")
            listed[name] = digest
        _require(set(listed) == set(names) - {"SHA256SUMS"}, "MANIFEST_COVERAGE")
        for name, digest in listed.items():
            _require(hashlib.sha256(z.read(name)).hexdigest() == digest, "MANIFEST_HASH")
        _require(z.read("HEAD.txt").decode().strip() == expected_head, "SOURCE_HEAD")
        for stage in STAGES:
            _require(z.read(stage + "_EXIT.txt").decode().strip() == "0", "STAGE_" + stage)
        return z
    except BaseException:
        z.close()
        raise


def _negative_gates(report):
    _require(report.get("learning_mode") == "RECORD_ONLY"
             and report.get("jepa_weight") == 0
             and report.get("b3_promoted") is False
             and report.get("step2_promoted") is False
             and report.get("body_jepa_promoted") is False
             and report.get("redmi_measured") is False
             and report.get("learned_german_transfer_proven") is False
             and report.get("whole_system_complete") is False, "NEGATIVE_GATES")


def _row_vector(z, path, lang):
    suite = build_suite(seed=13, lang=lang)
    obj = json.loads(z.read(path))
    rows = obj.get("results")
    _require(obj.get("status") == "DONE" and obj.get("items") == 88
             and obj.get("suite_hash") == suite["hash"]
             and type(rows) is list and len(rows) == 88, "ROW_SUITE")
    for item, expected in zip(rows, suite["items"]):
        _require(type(item) is dict
                 and set(item) == {"id", "correct", "confidence"}
                 and item["id"] == expected["id"]
                 and type(item["correct"]) is int and item["correct"] in (0, 1)
                 and type(item["confidence"]) in (int, float)
                 and math.isfinite(item["confidence"])
                 and 0 <= item["confidence"] <= 1, "ROW_INTEGRITY")
    return [row["correct"] for row in rows], [i["family"] for i in suite["items"]]


def _validate_c3(z):
    r = json.loads(z.read("native/REPORT.json"))
    _negative_gates(r)
    role, sha = MODELS["c3"]
    _require(r.get("evidence_kind") == "LINUX_NATIVE_C3_AG12_ONLY"
             and r.get("seed") == 13 and r.get("native_role") == role
             and r.get("model_sha256") == sha
             and r.get("runner_tar_sha256") == RUNNER_SHA
             and r.get("actual_llama_server_sha256") == RUNNER_BINARY_SHA
             and r.get("native_calls_observed") == 176
             and r.get("runtime_closed") is True
             and r.get("no_holdout_prompts_in_events") is True
             and r.get("no_holdout_prompts_in_messages") is True, "C3_NATIVE")
    for lang in ("de", "en"):
        run = r["runs"][lang]
        _require(run.get("status") == "DONE" and run.get("roles") == [role]
                 and run.get("stats", {}).get(role, {}).get("items") == 88
                 and run["stats"][role].get("errors") == 0, "C3_" + lang.upper())
    return r


def _validate_bodies(z):
    r = json.loads(z.read("native/REPORT.json"))
    _negative_gates(r)
    _require(r.get("evidence_kind") == "LINUX_NATIVE_B1_B2_AG12_ONLY"
             and r.get("seed") == 13 and r.get("status") == "DONE"
             and r.get("native_calls") == 352, "BODIES_NATIVE")
    for name in ("b1", "b2"):
        role, sha = MODELS[name]
        body = r["models"][name]
        _require(body.get("status") == "DONE" and body.get("role") == role
                 and body.get("model_sha256") == sha
                 and body.get("runner_tar_sha256") == RUNNER_SHA
                 and body.get("runner_binary_sha256") == RUNNER_BINARY_SHA
                 and body.get("native_calls") == 176
                 and body.get("closed") is True and body.get("process_reaped") is True
                 and body.get("no_events") is True and body.get("no_messages") is True,
                 "BODY_" + name.upper())
        for lang in ("de", "en"):
            run = body["runs"][lang]
            _require(run.get("status") == "DONE" and run.get("roles") == [role]
                     and run.get("stats", {}).get(role, {}).get("items") == 88
                     and run["stats"][role].get("errors") == 0,
                     "BODY_" + name.upper() + "_" + lang.upper())
    return r


def _coverage(vectors, families):
    _require(set(vectors) == {"c3", "b1", "b2"}
             and all(len(v) == 88 for v in vectors.values())
             and len(families) == 88, "COVERAGE_SHAPE")
    total = len(families)
    counts = {name: sum(rows) for name, rows in vectors.items()}
    counts["b1_or_b2_oracle"] = sum(
        a or b for a, b in zip(vectors["b1"], vectors["b2"]))
    counts["all_three_oracle"] = sum(
        a or b or c for a, b, c in
        zip(vectors["b1"], vectors["b2"], vectors["c3"]))
    exclusive = {
        name: sum(vectors[name][i] and all(not vectors[other][i]
                  for other in vectors if other != name) for i in range(total))
        for name in vectors
    }
    by_family = {}
    for family in sorted(set(families)):
        ix = [i for i, f in enumerate(families) if f == family]
        by_family[family] = {
            "items": len(ix),
            **{name: sum(vectors[name][i] for i in ix)
               for name in ("c3", "b1", "b2")},
            "b1_or_b2_oracle": sum(
                vectors["b1"][i] or vectors["b2"][i] for i in ix),
            "all_three_oracle": sum(
                any(vectors[name][i] for name in vectors) for i in ix),
        }
    return {"items": total, "correct_counts": counts,
            "exclusive_correct_counts": exclusive,
            "by_family": by_family,
            "claim_limit": "Oracle coverage upper bounds only; no actual fusion, learning or transfer."}


def analyze(c3_zip, bodies_zip, c3_sha, bodies_sha):
    with _zip(c3_zip, c3_sha, C3_HEAD) as c3, _zip(bodies_zip, bodies_sha, BODIES_HEAD) as bodies:
        _validate_c3(c3)
        _validate_bodies(bodies)
        languages = {}
        for lang in ("de", "en"):
            c, families = _row_vector(c3, "native/AG12_" + lang.upper() + "_ROWS.json", lang)
            a, fa = _row_vector(bodies, "native/b1/AG12_" + lang.upper() + "_ROWS.json", lang)
            b, fb = _row_vector(bodies, "native/b2/AG12_" + lang.upper() + "_ROWS.json", lang)
            _require(families == fa == fb, "FAMILY_ALIGNMENT")
            languages[lang] = _coverage({"c3": c, "b1": a, "b2": b}, families)
    return {
        "schema": "v13.run26.ag12_closed_native_coverage.v1",
        "status": "DIAGNOSTIC_ONLY",
        "source_heads": {"c3": C3_HEAD, "bodies": BODIES_HEAD},
        "source_zip_sha256": {"c3": c3_sha, "bodies": bodies_sha},
        "seed": 13, "language_order": ["de", "en"],
        "languages": languages,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "learned_german_transfer_proven": False,
        "actual_fusion_proven": False, "whole_system_complete": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--c3-zip", type=Path, required=True)
    p.add_argument("--bodies-zip", type=Path, required=True)
    p.add_argument("--c3-sha", required=True)
    p.add_argument("--bodies-sha", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    if args.out.exists():
        raise FileExistsError("RUN26_FRESH_OUTPUT_REQUIRED")
    try:
        result = analyze(args.c3_zip, args.bodies_zip, args.c3_sha, args.bodies_sha)
    except Exception as exc:
        result = {"schema": "v13.run26.ag12_closed_native_coverage.v1",
                  "status": "RED", "error": type(exc).__name__ + ": " + str(exc)[:300],
                  "coverage": None, "jepa_weight": 0,
                  "step2": "UTILITY_FAIL", "b3": "NO_PROMOTION",
                  "whole_system_complete": False}
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n",
                        encoding="utf-8")
    if result["status"] != "DIAGNOSTIC_ONLY":
        raise RuntimeError("RUN26_INVALID_NATIVE_EVIDENCE; RED report retained")
    print("RUN26_CLOSED_NATIVE_ORACLE_DIAGNOSTIC_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
