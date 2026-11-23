"""Independent read-only replay of seed83 native raw and preregistered gates.

No model invocation and no production authority. A structurally valid RED
pilot remains RED; this auditor does not repair raw, scores or source.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from v13.agi import listarith
from v13.agi import listarith_de_shadow_pipeline as pipeline

MODEL_SHA256 = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
BINARY_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
FIXTURE_BLOB = "cc052aa9eaecd213124f9c79df15f30637c5a80c"
SOURCE_BLOBS = {
    "fixture": FIXTURE_BLOB,
    "pipeline": "25cacd7388e5464dd814f4b18c545e2ec2f78b54",
    "german": "f9791c84846db660e9bde0e002defa55321f47b3",
    "listarith": "35893e9f829a591ffb9a792a73cef9bce986b3c4",
    "runners": "efda7aa1aa5729e974d0d641870d4da05d21c961",
    "models": "7af05962af41d0bc3f7dd18ef01d4eba55eabf99",
}
FIXTURE = Path(__file__).resolve().parents[1] / "specs/listarith_de83_native_shadow_frozen.json"
GATES = ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
         "redmi_measured", "whole_system_complete")


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def source_invented(values, text):
    tokens = Counter(x.replace("−", "-").lstrip("+") for x in listarith._INT.findall(text))
    got = Counter(str(v["number"]) for v in values
                  if not listarith.AGGREGATE.fullmatch(v["name"]))
    return sum(max(0, n - tokens[value]) for value, n in got.items())


def independent_score(expected, shadow):
    op = expected["expected_operation"]
    emitted = shadow["status"] == "SHADOW_RESULT"
    if op is None:
        return {"supported": False, "correct": not emitted,
                "wrong_emitted": False, "unsupported_false_positive": emitted,
                "abstain_supported": False}
    exact = emitted and shadow["operation"] == op and shadow["value"] == expected["expected_answer"]
    return {"supported": True, "correct": bool(exact),
            "wrong_emitted": bool(emitted and not exact),
            "unsupported_false_positive": False,
            "abstain_supported": not emitted}


def replay(directory):
    directory = Path(directory)
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    require(fixture["schema"] == "v13.de83.native_shadow.v1"
            and fixture["seed"] == 83 and len(fixture["rows"]) == 24, "FIXTURE_RED")
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    require(report["schema"] == "v13.de83.native_shadow.report.v1"
            and report["seed"] == 83
            and report["fixture_blob"] == FIXTURE_BLOB
            and report["source_blobs"] == SOURCE_BLOBS
            and report["model_sha256"] == MODEL_SHA256
            and report["native_binary_sha256"] == BINARY_SHA256
            and report["learning_mode"] == "RECORD_ONLY"
            and report["jepa_weight"] == 0
            and report["live_tool_execution"] is False
            and report["external_action_authority"] is False
            and report["evidence_level"] == "LINUX_NATIVE_NOT_REDMI",
            "REPORT_SOURCE_OR_AUTHORITY_RED")
    for gate in GATES:
        require(report[gate] is False, "REPORT_GATE_RED:" + gate)
    require(len(report["rows"]) == 24, "REPORT_ROW_COUNT_RED")
    expected_names = set()
    used_pids = set()
    complete = supported_correct = supported_wrong = unsupported_fp = invented = 0
    all_reaped = True
    for index, expected in enumerate(fixture["rows"]):
        name = "%02d_%s.json" % (index, expected["id"])
        expected_names.add(name)
        raw = json.loads((directory / "raw" / name).read_text(encoding="utf-8"))
        summary = report["rows"][index]
        require(raw["index"] == summary["index"] == index
                and raw["id"] == summary["id"] == expected["id"]
                and raw["text"] == expected["text"]
                and raw["expected"] == expected["values"]
                and raw["expected_operation"] == expected["expected_operation"]
                and raw["expected_answer"] == expected["expected_answer"]
                and raw["model_sha256"] == MODEL_SHA256
                and raw["source_exact"] is True
                and raw["learning_mode"] == "RECORD_ONLY"
                and raw["jepa_weight"] == 0
                and raw["status"] == summary["status"]
                and raw["native_pid"] == summary["native_pid"]
                and raw["postclose_process_reaped"] == summary["postclose_process_reaped"],
                "RAW_SOURCE_OR_SUMMARY_RED:" + str(index))
        for gate in GATES:
            require(raw[gate] is False, "RAW_GATE_RED:" + str(index))
        reaped = (raw["postclose_process_reaped"] is True
                  and raw["release"]["process_reaped"] is True)
        all_reaped &= reaped
        require(reaped, "PROCESS_NOT_REAPED:" + str(index))
        if raw["status"] != "NATIVE_ROW_COMPLETE":
            require(raw["status"] == "NATIVE_ROW_RED"
                    and "error_type" in raw and "traceback" in raw,
                    "RAW_ERROR_MISSING:" + str(index))
            continue
        pid = raw["native_pid"]
        require(type(pid) is int and pid not in used_pids
                and raw["native_metrics"]["status"] == "FINAL"
                and raw["native_metrics"]["actual_model"] == raw["native_model"]
                and raw["native_metrics"]["memory"]["pid"] == pid,
                "NATIVE_PID_OR_MODEL_RED:" + str(index))
        used_pids.add(pid)
        parsed = pipeline.parse_typed(raw["raw_output"])
        require(parsed == raw["parsed"], "PARSED_RAW_MISMATCH:" + str(index))
        computed_shadow = pipeline.evaluate(expected["text"], raw["raw_output"])
        require(computed_shadow == raw["shadow"] == summary["shadow"],
                "SHADOW_REPLAY_MISMATCH:" + str(index))
        computed_score = independent_score(expected, computed_shadow)
        require(computed_score == raw["score"] == summary["score"],
                "SCORE_REPLAY_MISMATCH:" + str(index))
        n = source_invented(parsed, expected["text"])
        require(n == raw["invented_nonaggregate"] == summary["invented_nonaggregate"],
                "SOURCE_NUMBER_GUARD_RED:" + str(index))
        complete += 1
        invented += n
        supported_correct += int(computed_score["supported"] and computed_score["correct"])
        supported_wrong += int(computed_score["wrong_emitted"])
        unsupported_fp += int(computed_score["unsupported_false_positive"])
    require({p.name for p in (directory / "raw").glob("*.json")} == expected_names,
            "RAW_COVERAGE_RED")
    require((complete, supported_correct, supported_wrong, unsupported_fp, invented,
             all_reaped) ==
            (report["native_completed"], report["supported_correct"],
             report["supported_wrong_emitted"], report["unsupported_false_positive"],
             report["invented_nonaggregate"], report["all_processes_reaped"]),
            "REPORT_TOTALS_RED")
    status = ("PILOT_PARTIAL_RED" if complete != 24 or not all_reaped else
              "NATIVE_DE83_SHADOW_PILOT_SIGNAL"
              if supported_correct >= 12 and supported_wrong <= 1
              and unsupported_fp == 0 and invented == 0 else
              "NATIVE_DE83_SHADOW_NOT_SUPPORTED")
    require(report["status"] == status, "FROZEN_STATUS_REPLAY_RED")
    return {"schema": "v13.de83.independent_native_raw_replay.v1",
            "native_status_original": status, "native_completed": complete,
            "supported_correct": supported_correct, "supported_wrong_emitted": supported_wrong,
            "unsupported_false_positive": unsupported_fp,
            "invented_nonaggregate": invented, "all_processes_reaped": all_reaped,
            "evidence_level": "LINUX_NATIVE_RAW_REPLAY_NOT_REDMI",
            "step2_gate_promoted": False, "b3_promoted": False,
            "body_jepa_available": False, "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dir", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError("FRESH_AUDIT_OUTPUT_REQUIRED")
    result = replay(args.dir)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
