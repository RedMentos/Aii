"""Run12N independent original-raw verifier for disjoint 16 native turns.

Replays frozen Run11V source-bound scores and source/route/process evidence.
Structural validity and pilot signal are separate from all production gates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import c2_body_disjoint_paired181_run11v as frozen
from scripts import c2_body_observer_off_run12n as pilot
from scripts.c2_strict_native_compat_run12k import classify

SCHEMA = "v13.c2_c3_body.observer_off.run12n.audit.v1"
MAX_JSON_BYTES = 5_000_000
NEGATIVE = ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
            "redmi_measured", "whole_system_complete",
            "comparative_utility_proven")


def require(ok, why):
    if not ok:
        raise ValueError(why)


def read_json(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= MAX_JSON_BYTES,
            "RAW_MISSING_OVERSIZE_OR_SYMLINK")
    return json.loads(path.read_text(encoding="utf-8"))


def wire(value):
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def verify(directory, fixture_path):
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), "DIRECTORY_INVALID")
    fixture = pilot.load_fixture(fixture_path)
    report = read_json(directory / "report.json")
    require(report.get("schema") == pilot.SCHEMA
            and report.get("seed") == 197
            and report.get("fixture_sha256") == pilot.FIXTURE_SHA256
            and report.get("fixtures") == fixture["cases"]
            and report.get("arms") == list(pilot.ARMS)
            and report.get("arm_order") == [list(a) for a in pilot.ARM_ORDER],
            "REPORT_COHORT_OR_ORDER_CHANGED")
    require(report.get("model_verification") == {
        k: {"ok": True, "hash_checked": True} for k in pilot.ROLES},
        "MODEL_PINS_UNVERIFIED")
    rows = report.get("rows")
    require(type(rows) is list and len(rows) == 16, "ROW_COUNT_CHANGED")
    rawdir = directory / "raw"
    preclose = directory / "preclose"
    require(rawdir.is_dir() and preclose.is_dir()
            and not rawdir.is_symlink() and not preclose.is_symlink(),
            "RAW_DIR_MISSING")
    expected = {
        f"{i:02d}_{pilot.ARM_ORDER[i // 4][i % 4]}.json"
        for i in range(16)}
    strict_names = {
        f"{i:02d}_STRICT_ADMISSION.json"
        for i, r in enumerate(rows) if r.get("arm") == "F_NATIVE_AUTO"}
    require({p.name for p in rawdir.iterdir()} == expected | strict_names,
            "RAW_FILES_CHANGED")
    require({p.name for p in preclose.iterdir()} == expected,
            "PRECLOSE_FILES_CHANGED")
    for i, row in enumerate(rows):
        fixture_case = fixture["cases"][i // 4]
        arm = pilot.ARM_ORDER[i // 4][i % 4]
        require(type(row) is dict and row.get("index") == i
                and row.get("fixture") == fixture_case["project"]
                and row.get("arm") == arm, "ROW_IDENTITY_CHANGED")
        raw = read_json(rawdir / f"{i:02d}_{arm}.json")
        witness = read_json(preclose / f"{i:02d}_{arm}.json")
        require(all(raw.get(k) == v for k, v in witness.items()),
                "PRECLOSE_WITNESS_CHANGED")
        require(raw.get("prompt") == frozen.prompt(fixture_case)
                and raw.get("index") == i and raw.get("arm") == arm
                and raw.get("raw_audit", {}).get("event_id") == row.get("event_id")
                and raw.get("raw_audit", {}).get("output") == row.get("final_output"),
                "SOURCE_OUTPUT_IDENTITY_CHANGED")
        require(raw.get("learning_mode") == "RECORD_ONLY"
                and raw.get("jepa_weight") == 0
                and all(raw.get(k) is False for k in NEGATIVE[:5]),
                "RAW_NEGATIVE_GATE_CHANGED")
        before = raw.get("body_process_releases_before_close")
        after = raw.get("body_process_releases")
        require(type(before) is list and type(after) is list
                and after[:len(before)] == before
                and raw.get("release_capture_phase") == "after_close",
                "POSTCLOSE_RECEIPT_CHANGED")
        flags = pilot.zero_offer_witness(
            raw["raw_audit"], arm, after,
            native_context=raw.get("context_packet"),
            native_alive=raw.get("native_c2_alive_before_close"),
            native_reaped=raw.get("native_c2_process_reaped"),
            native_pid=raw.get("native_c2_pid"),
            source_exact=raw.get("source_exact_before_close"),
            session=raw.get("session_id"), event_id=raw.get("event_id"),
            source_text=raw["prompt"],
            release_capture_phase=raw["release_capture_phase"])
        require(flags == row.get("flags"), "NATIVE_FLAGS_REPLAY_CHANGED")
        require(flags.get("observer_mode") == "off"
                and flags.get("expected_offer_roles") == []
                and flags.get("body_offer_roles") == [],
                "OBSERVER_OFF_ZERO_OFFER_CHANGED")
        require(raw.get("flags") == row.get("flags"), "RAW_FLAGS_DIVERGE")
        score = (frozen.score_pair(fixture_case, row["final_output"])
                 if flags["valid_native"] else
                 {"a": False, "b": False, "correct": 0, "out_of": 2})
        secondary = (frozen.score_primary(fixture_case, row["final_output"])
                     if flags["valid_native"] else
                     {"a": False, "b": False, "correct": 0, "out_of": 2})
        require(wire(score) == row.get("score") == raw.get("score")
                and wire(secondary) == row.get("secondary_score") == raw.get("secondary_score"),
                "SOURCE_BOUND_SCORE_REPLAY_CHANGED")
        if arm == "F_NATIVE_AUTO":
            strict = classify({"route_info": raw["route_info"],
                               "route": flags["route"]})
            saved = read_json(rawdir / f"{i:02d}_STRICT_ADMISSION.json")
            require(strict == saved == row.get("strict_admission"),
                    "STRICT_ADMISSION_REPLAY_CHANGED")
    summary = pilot.summarize(rows)
    for key, value in summary.items():
        require(report.get(key) == value, "SUMMARY_CHANGED_" + key)
    require(report.get("learning_mode") == "RECORD_ONLY"
            and report.get("jepa_weight") == 0
            and all(report.get(k) is False for k in NEGATIVE),
            "REPORT_NEGATIVE_GATE_CHANGED")
    return {
        "schema": SCHEMA, "status": summary["status"],
        "rows_verified": 16, "native_c2_invocations": summary["native_c2_invocations"],
        "native_c2_changed_routes": summary["native_c2_changed_routes"],
        "score_totals_out_of_8": summary["score_totals_out_of_8"],
        "native_auto_signal_not_gate": summary["native_auto_utility_pilot_signal_not_gate"],
        "utility_gate_promoted": False, "redmi_measured": False,
        "whole_system_complete": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(verify(a.pilot, a.fixture), sort_keys=True))


if __name__ == "__main__":
    main()
