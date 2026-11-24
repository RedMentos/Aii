"""Read-only posthoc seed79 native ZIP -> German SHADOW arithmetic diagnostic.

Not a preregistered end-to-end native cohort. No new model execution.
The original immutable ZIP is downloaded separately and never committed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from v13.agi.listarith_de_shadow_pipeline import evaluate

ORIGINAL_ZIP_SHA256 = "0538160dbd6f59804a0e670e5c34ea75aab5e6b3f031cac0f6ac13203be08d70"
ORIGINAL_HEAD = "542c8c426f4ff15dd5b26d94dd89152fe60d9dbc"
ORIGINAL_MODEL_SHA256 = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
ORIGINAL_BINARY_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
ORIGINAL_FIXTURE_BLOB = "d0a840c9546fd87c3f7ef15f450b4650aaa06863"
STAGES = ("PINS", "VENV", "DEPS", "TEST", "BOOTSTRAP", "NATIVE",
          "REPORT_CHECK", "COMPILE", "PRIVACY", "DIFF")
NEGATIVE = ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
            "redmi_measured", "whole_system_complete")
FIXTURE = Path(__file__).resolve().parents[1] / "specs/c3_de_native_typed_read_seed79.json"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def verified_files(data, expected_sha256=None):
    """Validate ZIP bytes, unique safe paths, CRC and closed inner manifest."""
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None:
        require(digest == expected_sha256, "ZIP_SHA256_MISMATCH")
    import io
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "ZIP_DUPLICATE_NAME")
        require(all(n and not n.startswith("/") and ".." not in n.split("/")
                    and not n.endswith("/") for n in names), "ZIP_UNSAFE_PATH")
        require(archive.testzip() is None, "ZIP_CRC_RED")
        files = {n: archive.read(n) for n in names}
    require("SHA256SUMS" in files, "INNER_MANIFEST_MISSING")
    lines = files["SHA256SUMS"].decode("utf-8").splitlines()
    manifest = {}
    for line in lines:
        require("  " in line, "INNER_MANIFEST_FORMAT")
        sha, name = line.split("  ", 1)
        name = name.removeprefix("./")
        require(name not in manifest and len(sha) == 64
                and all(c in "0123456789abcdef" for c in sha),
                "INNER_MANIFEST_DUPLICATE_OR_HASH")
        manifest[name] = sha
    require(set(manifest) == set(files) - {"SHA256SUMS"}, "INNER_COVERAGE_RED")
    for name, sha in manifest.items():
        require(hashlib.sha256(files[name]).hexdigest() == sha,
                "INNER_HASH_RED:" + name)
    return files, digest, len(manifest)


def git_blob(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def replay(zip_path):
    files, digest, count = verified_files(Path(zip_path).read_bytes(), ORIGINAL_ZIP_SHA256)
    require(files["HEAD.txt"].decode().strip() == ORIGINAL_HEAD, "ORIGINAL_HEAD_RED")
    require(all(files[stage + "_EXIT.txt"].decode().strip() == "0"
                for stage in STAGES), "ORIGINAL_STAGE_RED")
    require("CLEAN" in files["PRIVACY_RAW.log"].decode(), "ORIGINAL_PRIVACY_RED")
    require(git_blob(FIXTURE) == ORIGINAL_FIXTURE_BLOB, "FIXTURE_BLOB_CHANGED")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    require(fixture["seed"] == 79 and len(fixture["rows"]) == 12, "FIXTURE_COUNT_RED")
    report = json.loads(files["pilot/report.json"])
    require(report["model_sha256"] == ORIGINAL_MODEL_SHA256
            and report["native_binary_sha256"] == ORIGINAL_BINARY_SHA256
            and report["fixture_blob"] == ORIGINAL_FIXTURE_BLOB
            and report["evidence_level"] == "LINUX_NATIVE_NOT_REDMI"
            and report["learning_mode"] == "RECORD_ONLY"
            and report["jepa_weight"] == 0
            and report["status"] == "NATIVE_C3_DE_READ_SUPPORTED"
            and report["completed"] == 12 and report["exact"] == 11
            and report["invented_nonaggregate"] == 0
            and report["all_processes_reaped"] is True,
            "ORIGINAL_REPORT_IDENTITY_RED")
    for gate in NEGATIVE:
        require(report[gate] is False, "ORIGINAL_GATE_RED:" + gate)
    require(len(report["rows"]) == 12, "ORIGINAL_SUMMARY_COUNT_RED")
    rows = []
    pids = set()
    for index, fixture_row in enumerate(fixture["rows"]):
        name = "pilot/raw/%02d_%s.json" % (index, fixture_row["id"])
        raw = json.loads(files[name])
        summary = report["rows"][index]
        require(raw["index"] == index == summary["index"]
                and raw["id"] == fixture_row["id"] == summary["id"]
                and raw["text"] == fixture_row["text"]
                and raw["expected"] == fixture_row["values"]
                and raw["model_sha256"] == ORIGINAL_MODEL_SHA256
                and raw["status"] == summary["status"] == "NATIVE_ROW_COMPLETE"
                and raw["source_exact"] is True
                and raw["learning_mode"] == "RECORD_ONLY"
                and raw["jepa_weight"] == 0
                and raw["native_pid"] == summary["native_pid"]
                and type(raw["native_pid"]) is int
                and raw["native_pid"] not in pids
                and raw["native_metrics"]["memory"]["pid"] == raw["native_pid"]
                and raw["native_metrics"]["status"] == "FINAL"
                and raw["postclose_process_reaped"] is True
                and raw["release"]["process_reaped"] is True
                and summary["postclose_process_reaped"] is True,
                "ORIGINAL_RAW_BINDING_RED:" + str(index))
        for gate in NEGATIVE:
            require(raw[gate] is False, "ORIGINAL_RAW_GATE_RED:" + str(index))
        pids.add(raw["native_pid"])
        shadow = evaluate(raw["text"], raw["raw_output"])
        expected_total = sum(v["number"] for v in fixture_row["values"])
        rows.append({"id": fixture_row["id"], "shadow_status": shadow["status"],
                     "reason": shadow["reason"], "operation": shadow["operation"],
                     "value": shadow["value"], "expected_total": expected_total,
                     "value_correct_if_emitted": (shadow["value"] == expected_total
                                                  if shadow["status"] == "SHADOW_RESULT" else None)})
    require({n for n in files if n.startswith("pilot/raw/")} ==
            {"pilot/raw/%02d_%s.json" % (i, row["id"])
             for i, row in enumerate(fixture["rows"])}, "ORIGINAL_RAW_COVERAGE_RED")
    emitted = [r for r in rows if r["shadow_status"] == "SHADOW_RESULT"]
    abstained = [r for r in rows if r["shadow_status"] == "SHADOW_ABSTAIN"]
    correct = sum(r["value_correct_if_emitted"] is True for r in emitted)
    # Posthoc expected outcome: C79-05 name misread; C79-06 asks to verify a claim.
    require(len(emitted) == 10 and len(abstained) == 2 and correct == 10
            and {r["id"] for r in abstained} == {"C79-05", "C79-06"},
            "POSTHOC_DIAGNOSTIC_CHANGED")
    return {"schema": "v13.de79.native_original_shadow_posthoc.v1",
            "original_zip_sha256": digest, "original_head": ORIGINAL_HEAD,
            "original_inner_sha256_count": count, "original_native_rows": 12,
            "original_exact_named_reads": 11,
            "shadow_emitted": len(emitted), "shadow_abstained": len(abstained),
            "shadow_correct_when_emitted": correct, "rows": rows,
            "evidence_level": "POSTHOC_REPLAY_EXISTING_LINUX_NATIVE",
            "new_native_model_calls": 0, "live_tool_execution": False,
            "external_action_authority": False, "learning_mode": "RECORD_ONLY",
            "step2_gate_promoted": False, "b3_promoted": False,
            "body_jepa_available": False, "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError("FRESH_OUTPUT_REQUIRED")
    result = replay(args.zip)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                   sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("shadow_emitted", "shadow_abstained",
                       "shadow_correct_when_emitted", "evidence_level")}))


if __name__ == "__main__":
    main()
