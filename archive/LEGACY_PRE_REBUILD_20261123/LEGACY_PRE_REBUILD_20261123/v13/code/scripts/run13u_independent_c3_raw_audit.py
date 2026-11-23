#!/usr/bin/env python3
"""Read-only stdlib Run13T original ZIP audit; independent of frozen runner.

Requires original ZIP SHA256 as an explicit argument. Never executes models.
Preserves RED instead of treating artifact upload as evidence of utility.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import zipfile

SEED = 283
ARMS = ("COPY_BASELINE", "COPY_STRICT")
CASE_ROWS = (
    ("Alder283", 5400, "Cedar", 1475, 11, "Mica", 2310, 7),
    ("Brim283", 8700, "Quartz", 3290, 18, "Birch", 4175, 26),
    ("Canto283", 9600, "Iris", 4060, 5, "Flint", 5870, 8),
    ("Dune283", 7350, "Amber", 2985, 13, "Slate", 3110, 12),
    ("Echo283", 11900, "Garnet", 5760, 21, "Pearl", 4325, 19),
    ("Fable283", 14800, "Cedar", 6995, 4, "Ruby", 7590, 9),
    ("Grove283", 6200, "Opal", 2140, 17, "Moss", 1895, 16),
    ("Harbor283", 10750, "Aspen", 4725, 22, "Onyx", 5930, 14),
)
FIXTURE_SHA256 = "c9a28de0e7fb198015b4b8845096d31f4af43f5c9679df7a8019a55ee4767b11"
MODEL_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
MODEL_REVISION = "657e078c94084481950a2d555a941481f715536b"
COPY_PREFIX = ("Reproduce the text between BEGIN_VERIFIED and END_VERIFIED exactly, "
               "including line breaks. Output only that text.\nBEGIN_VERIFIED\n")
COPY_SUFFIX = "\nEND_VERIFIED"
SYSTEM_BASELINE = ("You are a literal text copier. Reproduce only the text between "
                   "BEGIN_VERIFIED and END_VERIFIED from the user message, preserving "
                   "names, numbers, punctuation and line breaks. Do not calculate, "
                   "explain, or add text.")
SYSTEM_STRICT = ("You are a lossless transcription engine. Copy exactly the characters "
                 "between BEGIN_VERIFIED and END_VERIFIED in the user message. Every "
                 "character is data. Do not calculate, paraphrase, reorder, omit, "
                 "normalize, translate, explain, or add anything. Output only the copied "
                 "characters, starting immediately with the first character after "
                 "BEGIN_VERIFIED and ending immediately before END_VERIFIED.")
STAGES = ("PINS", "VENV", "DEPS", "TEST", "BOOTSTRAP", "NATIVE",
          "REPORT_CHECK", "COMPILE", "PRIVACY", "DIFF")
SCHEMA = "v13.run13t.c3_verbatim_heldout_native.v1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError(code)


def expected_answer(row):
    project, budget, a, ac, ad, b, bc, bd = row
    faster = a if ad < bd else b
    return (f"Project {project}.\n"
            f"{a} leaves {budget-ac} Euro remaining.\n"
            f"{b} leaves {budget-bc} Euro remaining.\n"
            f"{faster} finishes sooner.")


def wrong_claims(row, output):
    _, budget, a, ac, ad, b, bc, bd = row
    wrong = 0
    for name, expected in ((a, budget-ac), (b, budget-bc)):
        p = rf"\b{re.escape(name)}\s+leaves\s+([0-9]{{1,6}})\s+Euros?\s+remaining\b"
        wrong += sum(int(m.group(1)) != expected for m in re.finditer(p, output, re.I))
    faster = a if ad < bd else b
    wrong += sum(m.group(1).casefold() != faster.casefold() for m in re.finditer(
        r"\b([A-Za-z][A-Za-z0-9_-]{0,63})\s+finishes\s+sooner\b", output, re.I))
    return wrong


def load_original(path, expected_sha):
    raw = Path(path).read_bytes()
    require(sha(raw) == expected_sha, "ORIGINAL_ZIP_SHA_RED")
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None, "ORIGINAL_ZIP_CRC_RED")
        info = z.infolist()
        names = [x.filename for x in info]
        require(len(names) == len(set(names)), "DUPLICATE_ZIP_MEMBER")
        require(all(not n.startswith('/') and '..' not in n.split('/')
                    and '\\' not in n for n in names), "ZIP_PATH_RED")
        require(sum(x.file_size for x in info) <= 3_000_000, "ZIP_SIZE_RED")
        files = {n: z.read(n) for n in names if not n.endswith('/')}
    manifest = files["SHA256SUMS"].decode().splitlines()
    listed = {}
    for line in manifest:
        m = re.fullmatch(r"([0-9a-f]{64})  \./(.+)", line)
        require(m is not None, "MANIFEST_FORMAT_RED")
        h, name = m.groups()
        require(name not in listed, "DUPLICATE_MANIFEST_RED")
        listed[name] = h
    require(set(listed) == set(files) - {"SHA256SUMS"}, "MANIFEST_FILE_SET_RED")
    for n, h in listed.items():
        require(sha(files[n]) == h, "MANIFEST_HASH_RED:" + n)
    for stage in STAGES:
        require(files[stage + "_EXIT.txt"].decode().strip() == "0",
                "STAGE_RED:" + stage)
    require("CLEAN" in files["PRIVACY_RAW.log"].decode(), "PRIVACY_RED")
    require("Ran 18 tests" in files["TEST_RAW.log"].decode()
            and "\nOK\n" in files["TEST_RAW.log"].decode(), "TESTS_RED")
    return files, len(listed)


def audit(path, expected_sha):
    files, manifest_count = load_original(path, expected_sha)
    prefix = "pilot/"
    # Original Actions artifact can contain pilot/ or flat raw/ paths.
    if "pilot/report.json" not in files and "report.json" in files:
        prefix = ""
    require(prefix + "report.json" in files, "NATIVE_REPORT_MISSING")
    report = json.loads(files[prefix + "report.json"])
    require(report["schema"] == SCHEMA and report["seed"] == SEED
            and report["fixture_sha256"] == FIXTURE_SHA256
            and report["rows"] == 16, "NATIVE_REPORT_SOURCE_RED")
    require(set(report["totals"]) == set(ARMS), "REPORT_ARMS_RED")
    for key, value in {"learning_mode": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
                       "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE",
                       "jepa_weight": 0, "redmi_measured": False,
                       "utility_gate_promoted": False, "whole_system_complete": False,
                       "production_activation": False, "semantic_quality_proven": False,
                       "all_native_final": True, "all_native_reaped": True}.items():
        require(type(report.get(key)) is type(value) and report[key] == value,
                "REPORT_NEGATIVE_GATE_RED:" + key)
    require({n for n in files if n.startswith(prefix + "raw/") and n.endswith('.json')}
            == {prefix + f"raw/{i:02d}_{arm}.json" for i in range(8) for arm in ARMS},
            "RAW_COVERAGE_RED")
    pids, rows = set(), []
    for i, case in enumerate(CASE_ROWS):
        answer = expected_answer(case)
        prompt = COPY_PREFIX + answer + COPY_SUFFIX
        pair = []
        for arm in ARMS:
            row = json.loads(files[prefix + f"raw/{i:02d}_{arm}.json"])
            system = SYSTEM_BASELINE if arm == ARMS[0] else SYSTEM_STRICT
            require(row.get("schema") == SCHEMA and row.get("seed") == SEED
                    and row.get("index") == i and row.get("project") == case[0]
                    and row.get("arm") == arm
                    and row.get("answer_sha256") == sha(answer.encode())
                    and row.get("prompt_sha256") == sha(prompt.encode())
                    and row.get("system_sha256") == sha(system.encode())
                    and row.get("model_sha256") == MODEL_SHA
                    and row.get("model_revision") == MODEL_REVISION,
                    "ROW_BINDING_RED")
            for key in ("source_event_id", "query_event_id", "context_plan_packet_id"):
                require(type(row.get(key)) is str and bool(row[key]), "ROW_SOURCE_ID_RED")
            require(row.get("learning_mode") == "RECORD_ONLY"
                    and row.get("jepa_weight") == 0
                    and row.get("step2_status") == "UTILITY_FAIL"
                    and row.get("b3_status") == "NO_PROMOTION"
                    and row.get("body_jepa_status") == "UNAVAILABLE"
                    and row.get("redmi_measured") is False
                    and row.get("whole_system_complete") is False, "ROW_GATE_RED")
            require(row.get("native_calls") == 1
                    and row.get("native_status") == "FINAL"
                    and row.get("native_reaped") is True
                    and row.get("native_role") == "C3_LANGUAGE"
                    and row.get("native_release", {}).get("process_reaped") is True
                    and type(row.get("native_pid")) is int and row["native_pid"] > 0
                    and type(row.get("final_output")) is str,
                    "ROW_NATIVE_RED")
            require(row.get("native_metrics", {}).get("status") == "FINAL"
                    and row["native_metrics"].get("role") == "C3_LANGUAGE"
                    and row["native_metrics"].get("actual_model") == "LFM2.5-350M-QAD-Q4_0.gguf",
                    "ROW_MODEL_METRICS_RED")
            require(row["native_pid"] not in pids, "NATIVE_PID_REUSE_RED")
            pids.add(row["native_pid"])
            output = row["final_output"]
            require(row.get("exact_copy") is (output == answer), "EXACT_COPY_REPLAY_RED")
            require(row.get("wrong_claims") == wrong_claims(case, output),
                    "WRONG_CLAIMS_REPLAY_RED")
            pair.append(row)
            rows.append(row)
        for key in ("source_event_id", "query_event_id", "context_plan_packet_id",
                    "source_sha256", "answer_sha256", "prompt_sha256",
                    "model_sha256", "model_revision"):
            require(pair[0][key] == pair[1][key], "PAIRED_BINDING_RED:" + key)
        require(pair[0]["system_sha256"] != pair[1]["system_sha256"],
                "SYSTEM_ABLATION_RED")
    totals = {arm: {
        "n": sum(x["arm"] == arm for x in rows),
        "native_final": sum(x["arm"] == arm and x["native_status"] == "FINAL"
                            and x["native_reaped"] for x in rows),
        "exact_copy": sum(x["arm"] == arm and x["exact_copy"] for x in rows),
        "source_facts_verified": sum(x["arm"] == arm and x["source_facts_verified"] for x in rows),
        "wrong_claims": sum(x["wrong_claims"] for x in rows if x["arm"] == arm),
        "numeric_correct": sum(x["score"]["numeric"]["correct"]
                               for x in rows if x["arm"] == arm),
        "faster_correct": sum(x["score"]["faster_correct"]
                              for x in rows if x["arm"] == arm),
        "strict_full": sum(x["score"]["strict_full"]
                           for x in rows if x["arm"] == arm),
        "literal_abstain_dot": sum(x["arm"] == arm and x["final_output"] == "ABSTAIN."
                                  for x in rows),
    } for arm in ARMS}
    require(report["totals"] == totals, "TOTALS_REPLAY_RED")
    base, strict = totals[ARMS[0]], totals[ARMS[1]]
    signal = (strict["exact_copy"] >= base["exact_copy"] + 2
              and strict["strict_full"] >= base["strict_full"]
              and strict["source_facts_verified"] >= base["source_facts_verified"]
              and strict["wrong_claims"] <= base["wrong_claims"])
    hurt = strict["strict_full"] < base["strict_full"] or strict["exact_copy"] < base["exact_copy"]
    status = ("BOUNDED_SYNTHETIC_FIDELITY_SIGNAL_NOT_UTILITY_GATE" if signal
              else "FIDELITY_HURT" if hurt else "NO_ATTRIBUTABLE_FIDELITY_GAIN")
    require(report["status"] == status, "VERDICT_REPLAY_RED")
    return {"schema": "v13.run13u.independent_run13t_native_raw_audit.v1",
            "source_zip_sha256": expected_sha, "manifest_hashes_verified": manifest_count,
            "stage_exits_zero": len(STAGES), "native_rows": len(rows),
            "distinct_native_pids": len(pids), "totals": totals,
            "replayed_status": status,
            "evidence_class": "INDEPENDENT_REPLAY_OF_LINUX_NATIVE_SYNTHETIC_C3_RAW",
            "native_executed_by_this_audit": False, "utility_gate_pass": False,
            "redmi_measured": False, "whole_system_complete": False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("zip", type=Path)
    p.add_argument("--expected-sha", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(audit(a.zip, a.expected_sha), sort_keys=True, indent=2))
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile,
            json.JSONDecodeError) as exc:
        print(f"RUN13U_RAW_AUDIT_RED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())