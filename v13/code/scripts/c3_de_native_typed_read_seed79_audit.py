"""Independent read-only audit of seed79 original native C3 raw rows; no gate."""
from __future__ import annotations
from collections import Counter
import argparse
import json
from pathlib import Path

from scripts.c3_de_native_typed_read_seed79 import (
    fixtures, measure, parse_raw, MODEL_SHA256, MODEL_REVISION, PINS,
)

GATES = ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
         "redmi_measured", "whole_system_complete")


def require(ok, code):
    if not ok:
        raise ValueError(code)


def audit(directory):
    directory = Path(directory)
    j = json.loads((directory / "report.json").read_text())
    rows = fixtures()
    require(j["schema"] == "v13.c3.de.native_typed_read.seed79.report.v1"
            and j["seed"] == 79 and j["fixture_blob"] == PINS["fixture"]
            and j["source_blobs"] == PINS
            and j["model_revision"] == MODEL_REVISION
            and j["model_sha256"] == MODEL_SHA256
            and j["learning_mode"] == "RECORD_ONLY"
            and j["jepa_weight"] == 0 and j["live_tool_execution"] is False
            and j["external_action_authority"] is False
            and j["evidence_level"] == "LINUX_NATIVE_NOT_REDMI",
            "REPORT_IDENTITY_OR_AUTHORITY_RED")
    for gate in GATES:
        require(j[gate] is False, "REPORT_GATE_RED:" + gate)
    require(len(j["rows"]) == 12, "REPORT_ROW_COUNT_RED")
    exact = invented = aggregate = completed = 0
    raw_names = set()
    for i, row in enumerate(rows):
        name = f'{i:02d}_{row["id"]}.json'
        raw_names.add(name)
        raw = json.loads((directory / "raw" / name).read_text())
        summary = j["rows"][i]
        require(raw["index"] == i and summary["index"] == i
                and raw["id"] == row["id"] == summary["id"]
                and raw["text"] == row["text"]
                and raw["expected"] == row["values"]
                and raw["model_sha256"] == MODEL_SHA256
                and raw["native_model"] == "LFM2.5-350M-QAD-Q4_0.gguf"
                and raw["source_exact"] is True
                and raw["learning_mode"] == "RECORD_ONLY"
                and raw["jepa_weight"] == 0,
                "RAW_ROW_SOURCE_RED:" + str(i))
        for gate in GATES:
            require(raw[gate] is False, "RAW_GATE_RED:" + str(i))
        require(raw["status"] == summary["status"]
                and raw["native_pid"] == summary["native_pid"]
                and raw["postclose_process_reaped"] == summary["postclose_process_reaped"],
                "RAW_SUMMARY_RED:" + str(i))
        require(raw["postclose_process_reaped"] is True
                and raw["release"]["process_reaped"] is True,
                "UNREAPED_PROCESS_RED:" + str(i))
        if raw["status"] != "NATIVE_ROW_COMPLETE":
            require("error_type" in raw and "traceback" in raw,
                    "ERROR_RAW_MISSING:" + str(i))
            continue
        require(type(raw["native_pid"]) is int
                and raw["native_metrics"]["memory"]["pid"] == raw["native_pid"]
                if "memory" in raw["native_metrics"] else type(raw["native_pid"]) is int,
                "NATIVE_PID_METRIC_RED:" + str(i))
        require(raw["native_metrics"]["status"] == "FINAL"
                and raw["native_metrics"]["actual_model"] == raw["native_model"],
                "NATIVE_MODEL_METRIC_RED:" + str(i))
        values = parse_raw(raw["raw_output"])
        require(values == raw["parsed"], "RAW_JSON_CHANGED:" + str(i))
        computed = measure(values, row)
        require(computed == raw["score"] == summary["score"],
                "SCORE_REPLAY_RED:" + str(i))
        completed += 1
        exact += int(computed["exact"])
        invented += computed["invented_nonaggregate"]
        aggregate += computed["aggregate_read"]
    require({p.name for p in (directory / "raw").glob("*.json")} == raw_names,
            "RAW_FILE_COVERAGE_RED")
    require((completed, exact, invented, aggregate) ==
            (j["completed"], j["exact"], j["invented_nonaggregate"], j["aggregate_read"]),
            "REPORT_TOTALS_RED")
    require(j["all_processes_reaped"] is True, "PROCESS_SUMMARY_RED")
    expected = ("PILOT_PARTIAL_RED" if completed != 12 else
                "NATIVE_C3_DE_READ_SUPPORTED" if exact >= 9 and invented == 0 else
                "NATIVE_C3_DE_READ_NOT_SUPPORTED")
    require(j["status"] == expected, "REPORT_STATUS_RED")
    return {"schema": "v13.c3.de.seed79.independent_raw_replay.v1",
            "source_blobs": PINS, "native_rows": completed, "exact": exact,
            "invented_nonaggregate": invented, "aggregate_read": aggregate,
            "all_processes_reaped": True, "native_status_original": j["status"],
            "replay": "SOURCE_BOUND_NO_GATE", "redmi_measured": False,
            "step2_gate_promoted": False, "b3_promoted": False,
            "body_jepa_available": False, "jepa_weight": 0,
            "whole_system_complete": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError("FRESH_AUDIT_OUTPUT_REQUIRED")
    result = audit(a.dir)
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"replay": result["replay"], "exact": result["exact"],
                      "native_status": result["native_status_original"]}))


if __name__ == "__main__":
    main()
