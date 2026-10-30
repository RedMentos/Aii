"""Independent read-only audit of the fresh STEP2 v2 native Actions raw ZIP.

A positive audit is only a 4-task Linux-native pilot, NEVER STEP2 acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from scripts.step2_paired_raw_validator_audit_20261030 import semantic_diagnostic

EXPECTED_HEAD = "382990040c770a89116099d05b60dc87c269d864"
EXPECTED_FIXTURE_SHA = "b8dba3465d80aa90142065550a6d1b6770b562fd852e25f598ec8260d2bf6cf4"
EXPECTED_BLOBS = {
    "CANON_BLOB.txt": "218464b12a2d27d92524c751922fa8e1c3fb0ea7",
    "CATALOG_BLOB.txt": "7af05962af41d0bc3f7dd18ef01d4eba55eabf99",
    "TOOLS_BLOB.txt": "954a3f468f10195fbce12d27f68585ee7edee2c9",
}
EXPECTED_SOURCES = (
    "6bd49f34c0abba03bf459a2031d2fe19ac290bcf",
    "ff39f76dd2551b945a9f928b5b53f0918225e0b3",
    "fcd44ccce3b8b40d65a25187a78b0a8d49d9609d",
)
ARMS = ("A_C3_ONLY", "B_DEFAULT_BOTH", "C_ARITH_BOTH")
MODELS = {
    ARMS[0]: "LFM2.5-350M-QAD-Q4_0.gguf",
    ARMS[1]: "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
    ARMS[2]: "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
}
STAGES = ("PINS", "VENV", "DEPS", "FOCUSED", "BOOTSTRAP", "PILOT",
          "REPORT_CHECK", "COMPILE", "PRIVACY", "DIFF")


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_manifest(z):
    need(z.testzip() is None, "CRC_RED")
    names = z.namelist()
    need(len(names) == len(set(names)), "DUPLICATE_MEMBER_RED")
    manifest = z.read("SHA256SUMS").decode("utf-8").splitlines()
    declared = set()
    for line in manifest:
        m = re.fullmatch(r"([a-f0-9]{64})  \./([^\n]+)", line)
        need(m is not None, "MANIFEST_FORMAT_RED")
        digest, name = m.groups()
        need(name in names and name not in declared and name != "SHA256SUMS",
             "MANIFEST_MEMBER_RED")
        declared.add(name)
        need(sha(z.read(name)) == digest, "INNER_SHA_RED")
    need(declared == set(names) - {"SHA256SUMS"}, "MANIFEST_COVERAGE_RED")
    return len(manifest)


def _model_and_route_valid(event, row):
    meta = event.get("output_metadata", {})
    arm = row["arm"]
    runner = meta.get("runner", {})
    offers = {p.get("role") for p in event.get("offers", [])}
    route = "simple" if arm == ARMS[0] else "both"
    releases = row.get("native_process_releases", [])
    body = {"B1_DETAIL", "B2_GIST"}
    release_ok = (not releases if arm == ARMS[0] else
                  len(releases) == 2 and {x.get("role") for x in releases} == body
                  and all(x.get("process_reaped") is True for x in releases))
    return (len(event.get("checks", {})) == 13
            and all(v is True for v in event["checks"].values())
            and event.get("source_errors") == []
            and meta.get("model_generated") is True
            and meta.get("route") == {"source": "OPERATOR_ROUTE_OVERRIDE"}
            and meta.get("c2_packet", {}).get("route") == route
            and runner.get("actual_model") == MODELS[arm]
            and runner.get("role") == row.get("runner_role")
            and (not offers and runner.get("role") == "C3_LANGUAGE" if arm == ARMS[0]
                 else offers == body and runner.get("role") in body)
            and release_ok)


def _score(fixture, output):
    diagnostic = semantic_diagnostic(fixture, output)
    a, b = diagnostic["a"]["correct"], diagnostic["b"]["correct"]
    return {"a": a, "b": b, "correct": int(a) + int(b),
            "out_of": 2, "diagnostic": diagnostic}


def audit_zip(path, expected_sha256):
    raw = Path(path).read_bytes()
    need(re.fullmatch(r"[a-f0-9]{64}", expected_sha256) is not None,
         "EXPECTED_SHA_SHAPE_RED")
    need(sha(raw) == expected_sha256, "ORIGINAL_ZIP_SHA_RED")
    with zipfile.ZipFile(path) as z:
        count = verify_manifest(z)
        need(z.read("HEAD.txt").decode().strip() == EXPECTED_HEAD,
             "SOURCE_HEAD_RED")
        for filename, digest in EXPECTED_BLOBS.items():
            need(z.read(filename).decode().strip() == digest,
                 "SOURCE_PIN_RED_" + filename)
        need(tuple(z.read("SOURCE_BLOBS.txt").decode().splitlines())
             == EXPECTED_SOURCES, "PILOT_SOURCE_BLOBS_RED")
        exits = {stage: z.read(stage + "_EXIT.txt").decode().strip()
                 for stage in STAGES}
        result = {
            "schema": "v13.step2.paired_v2_raw_independent_audit.v1",
            "original_zip_sha256": expected_sha256,
            "source_head": EXPECTED_HEAD,
            "manifest_verified": f"{count}/{count}",
            "stage_exits": exits,
            "native_c2_control_proven": False,
            "comparative_step2_gate_promoted": False,
            "redmi_measured": False,
            "jepa_weight": 0,
            "claim_limit": "Four-task Linux-native pilot only, never STEP2 or C2 gate",
        }
        if "pilot/report.json" not in z.namelist():
            result.update(status="NATIVE_NOT_RUN_RED", valid_native_rows=0,
                          scores_out_of_8=None)
            return result
        report = json.loads(z.read("pilot/report.json"))
        need(report.get("schema") == "v13.step2.budget_paired_native_pilot.v2"
             and report.get("fixture_sha256") == EXPECTED_FIXTURE_SHA
             and report.get("seed") == 29 and report.get("arms") == list(ARMS),
             "REPORT_FIXTURE_IDENTITY_RED")
        need(report.get("comparative_step2_gate_promoted") is False
             and report.get("native_c2_control_proven") is False
             and report.get("jepa_weight") == 0
             and report.get("redmi_measured") is False,
             "REPORT_NEGATIVE_GATE_RED")
        fixtures = report["fixtures"]
        need(len(fixtures) == 4 and len({f["project"] for f in fixtures}) == 4,
             "FIXTURE_COUNT_RED")
        lookup = {f["project"]: f for f in fixtures}
        seen, rows, releases = set(), [], 0
        for row in report["rows"]:
            key = (row.get("fixture"), row.get("arm"))
            need(key[0] in lookup and key[1] in ARMS and key not in seen,
                 "DUPLICATE_OR_FOREIGN_ROW_RED")
            seen.add(key)
            if "raw_file" not in row:
                need(row.get("valid_native") is False and
                     row.get("score", {}).get("correct") == 0,
                     "MISSING_NATIVE_ROW_NOT_RED")
                rows.append({"fixture": key[0], "arm": key[1],
                             "valid_native": False, "correct": 0,
                             "reason": row.get("error_type", "NO_RAW")})
                continue
            filename = row["raw_file"]
            need(filename == f'{list(lookup).index(key[0]):02d}_{key[1]}.json',
                 "RAW_FILENAME_RED")
            event = json.loads(z.read("pilot/raw/" + filename))
            need(event.get("event_id") == row.get("event_id")
                 and event.get("output") == row.get("final_output"),
                 "RAW_REPORT_MISMATCH_RED")
            valid = _model_and_route_valid(event, row)
            need(valid == row.get("valid_native"), "NATIVE_VALIDITY_MISMATCH_RED")
            score = (_score(lookup[key[0]], event["output"]) if valid else
                     {"a": False, "b": False, "correct": 0, "out_of": 2})
            need(score == row.get("score"), "NATIVE_SCORE_MISMATCH_RED")
            if valid:
                releases += len(row.get("native_process_releases", []))
            rows.append({"fixture": key[0], "arm": key[1],
                         "valid_native": valid, "correct": score["correct"]})
        totals = {arm: sum(x["correct"] for x in rows if x["arm"] == arm)
                  for arm in ARMS}
        complete = (len(rows) == 12 and len(seen) == 12
                    and all(x["valid_native"] for x in rows))
        if complete:
            need(releases == 16, "BODY_RELEASE_RECEIPTS_RED")
            need(report.get("status") == "PILOT_COMPLETE_NO_GATE",
                 "COMPLETE_STATUS_MISMATCH_RED")
        else:
            need(report.get("status") in ("PILOT_PARTIAL_RED", "PILOT_ERROR"),
                 "PARTIAL_STATUS_MISMATCH_RED")
        need(totals == report.get("score_totals_out_of_8", totals),
             "REPORT_TOTAL_MISMATCH_RED")
        gain = (complete and totals[ARMS[2]] >= totals[ARMS[1]] + 2
                and totals[ARMS[2]] >= totals[ARMS[0]] + 2)
        need(report.get("pilot_gain", False) is gain, "PILOT_SIGNAL_MISMATCH_RED")
        result.update(status=report["status"], valid_native_rows=sum(
            int(x["valid_native"]) for x in rows),
            rows_observed=len(rows), body_release_receipts=releases,
            scores_out_of_8=totals, pilot_signal=gain,
            original_report_preserved=True)
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_zip", type=Path)
    p.add_argument("--sha256", required=True)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    result = audit_zip(a.original_zip, a.sha256)
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if a.out:
        if a.out.exists():
            raise FileExistsError("FRESH_RESULT_PATH_REQUIRED")
        a.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
