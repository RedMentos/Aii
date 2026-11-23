"""Run11V independent seed181 source/row/score replay; structural PASS never promotes native."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import c2_body_disjoint_paired181_run11v as m

SCHEMA = "v13.c2_body.disjoint.seed181.audit.v1"
MAX_JSON_BYTES = 5_000_000
NEGATIVE_GATES = ("step2_gate_promoted", "b3_promoted",
                  "body_jepa_available", "redmi_measured",
                  "whole_system_complete", "comparative_utility_proven")
RAW_NEGATIVE_GATES = NEGATIVE_GATES[:5]


def _read_json(path):
    path = Path(path)
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_size > MAX_JSON_BYTES):
        raise ValueError("RAW_MISSING_OVERSIZE_OR_SYMLINK")
    return json.loads(path.read_text(encoding="utf-8"))


def _require(condition, label):
    if not condition:
        raise ValueError(label)


def verify_report(directory):
    """Independently recompute preregistered primary/secondary frozen scores and native flags."""
    directory = Path(directory)
    _require(directory.is_dir() and not directory.is_symlink(), "REPORT_DIRECTORY_INVALID")
    report = _read_json(directory / "report.json")
    _require(report.get("schema") == m.SCHEMA, "REPORT_SCHEMA_CHANGED")
    _require(report.get("seed") == m.SEED, "SEED_CHANGED")
    _require(report.get("fixture_sha256") == m.FIXTURE_SHA256, "FIXTURE_PIN_CHANGED")
    _require(report.get("fixtures") == list(m.FIXTURES), "FIXTURE_CONTENT_CHANGED")
    _require(report.get("arms") == list(m.ARMS), "ARM_IDENTITY_CHANGED")
    _require(report.get("arm_order") == [list(a) for a in m.ARM_ORDER], "ARM_ORDER_CHANGED")
    _require(report.get("learning_mode") == "RECORD_ONLY"
             and report.get("jepa_weight") == 0, "AGE0_GATE_CHANGED")
    for k in NEGATIVE_GATES:
        _require(report.get(k) is False, "GATE_CHANGED_" + k)
    models = report.get("model_verification")
    _require(isinstance(models, dict) and set(models) == {"needle", "language", "body", "gist"}
             and all(v == {"ok": True, "hash_checked": True}
                     for v in models.values()), "MODEL_PIN_EVIDENCE_MISSING")
    rows = report.get("rows")
    _require(isinstance(rows, list) and len(rows) == 24, "ROW_COUNT_INVALID")
    rawdir = directory / "raw"
    _require(rawdir.is_dir() and not rawdir.is_symlink(), "RAW_DIRECTORY_INVALID")
    expected_names = {
        f"{i:02d}_{m.ARM_ORDER[i // 6][i % 6]}.json" for i in range(24)
    }
    _require({p.name for p in rawdir.iterdir()} == expected_names, "RAW_FILES_MISMATCH")
    preclosedir = directory / "preclose"
    _require(preclosedir.is_dir() and not preclosedir.is_symlink(),
             "PRECLOSE_DIRECTORY_INVALID")
    preclose_names = {p.name for p in preclosedir.iterdir()}
    _require(preclose_names <= expected_names, "PRECLOSE_FILES_UNREGISTERED")
    totals = {a: 0 for a in m.ARMS}
    secondary = {a: 0 for a in m.ARMS}
    invocations = selected = 0
    valid = True
    for i, row in enumerate(rows):
        fixture = m.FIXTURES[i // 6]
        arm = m.ARM_ORDER[i // 6][i % 6]
        _require(isinstance(row, dict)
                 and row.get("index") == i
                 and row.get("fixture") == fixture["project"]
                 and row.get("arm") == arm, "ROW_ORDER_OR_IDENTITY")
        raw = _read_json(rawdir / f"{i:02d}_{arm}.json")
        _require(raw.get("index") == i and raw.get("arm") == arm
                 and raw.get("fixture") == fixture["project"], "RAW_IDENTITY_CHANGED")
        _require(raw.get("flags") == row.get("flags")
                 and raw.get("score") == row.get("score")
                 and ("raw_audit" not in raw or
                      raw.get("final_output") == row.get("final_output")),
                 "RAW_REPORT_DIVERGENCE")
        score = row.get("score")
        _require(isinstance(score, dict)
                 and type(score.get("correct")) is int
                 and 0 <= score["correct"] <= 2, "SCORE_TYPE_INVALID")
        if "raw_audit" not in raw:
            _require("error_type" in raw
                     and raw.get("flags", {}).get("valid_native") is False
                     and score["correct"] == 0, "ERROR_ROW_FORGED")
            _require(raw.get("error_type") == row.get("error_type"), "ERROR_ROW_DIVERGENCE")
            valid = False
        else:
            preclose_name = f"{i:02d}_{arm}.json"
            _require(preclose_name in preclose_names, "PRECLOSE_WITNESS_MISSING")
            witness = _read_json(preclosedir / preclose_name)
            _require(type(witness) is dict and all(
                raw.get(k) == value for k, value in witness.items()),
                "PRECLOSE_WITNESS_CHANGED")
            _require(raw.get("raw_audit", {}).get("event_id") == row.get("event_id")
                     and raw["raw_audit"].get("output") == row.get("final_output")
                     and raw.get("prompt") == m.prompt(fixture), "SOURCE_OR_EVENT_CHANGED")
            _require(raw.get("learning_mode") == "RECORD_ONLY"
                     and raw.get("jepa_weight") == 0, "RAW_AGE0_CHANGED")
            for k in RAW_NEGATIVE_GATES:
                _require(raw.get(k) is False, "RAW_GATE_CHANGED_" + k)
            before = raw.get("body_process_releases_before_close")
            after = raw.get("body_process_releases")
            _require(type(before) is list and type(after) is list
                     and after[:len(before)] == before
                     and raw.get("release_capture_phase") == "after_close",
                     "POSTCLOSE_RELEASE_PROOF_MISSING")
            _require(type(raw.get("native_c2_alive_before_close")) is bool
                     and type(raw.get("source_exact_before_close")) is bool
                     and type(raw.get("native_c2_process_reaped")) is bool,
                     "C2_LIFECYCLE_PROOF_MISSING")
            _require(raw.get("b1_model_key") == "body"
                     and raw.get("b2_model_key") == (
                         "body" if arm == "E_SHARED_DUAL_COLD" else "gist"),
                     "BODY_MODEL_IDENTITY_CHANGED")
            _require(raw.get("b2_control") == (
                "shared_body_dual_state" if arm == "E_SHARED_DUAL_COLD"
                else "two_body"), "BODY_CONTROL_CHANGED")
            flags = m.row_evidence(
                raw["raw_audit"], arm, after,
                native_context=raw.get("context_packet"),
                native_alive=raw["native_c2_alive_before_close"],
                native_reaped=raw["native_c2_process_reaped"],
                native_pid=raw.get("native_c2_pid"),
                source_exact=raw["source_exact_before_close"],
                session=raw.get("session_id"), event_id=raw.get("event_id"),
                source_text=raw["prompt"],
                release_capture_phase=raw["release_capture_phase"])
            _require(flags == row["flags"], "NATIVE_FLAGS_REPLAY_MISMATCH")
            _require(raw.get("secondary_score") == row.get("secondary_score"),
                     "SECONDARY_REPORT_DIVERGENCE")
            expected = (m.score_pair(fixture, row["final_output"])
                        if flags["valid_native"] else
                        {"a": False, "b": False, "correct": 0, "out_of": 2})
            expected_secondary = (m.score_primary(fixture, row["final_output"])
                                  if flags["valid_native"] else
                                  {"a": False, "b": False, "correct": 0, "out_of": 2})
            # JSON evidence stores equation tuples as arrays; compare the wire
            # representation, never change the frozen scorer or native bytes.
            wire = lambda value: json.loads(json.dumps(value, sort_keys=True, allow_nan=False))
            _require(wire(expected) == score and wire(expected_secondary) == row["secondary_score"],
                     "SOURCE_SCORE_REPLAY_MISMATCH")
            valid = valid and flags["valid_native"]
            secondary[arm] += row["secondary_score"]["correct"]
            if arm == "F_NATIVE_AUTO":
                invocations += int(flags["native_c2_invocation"])
                selected += int(flags["native_c2_selected"])
        totals[arm] += score["correct"]
    _require(report.get("score_totals_out_of_8") == totals, "PRIMARY_TOTALS_CHANGED")
    _require(report.get("secondary_totals_out_of_8") == secondary, "SECONDARY_TOTALS_CHANGED")
    _require(report.get("native_c2_invocations") == invocations
             and report.get("native_c2_selected") == selected, "C2_TOTALS_CHANGED")
    _require(report.get("pilot_signal_not_gate") is m.pilot_signal(totals, valid),
             "PILOT_SIGNAL_CHANGED")
    native_signal = bool(valid and selected >= 1
                         and totals["F_NATIVE_AUTO"] >= totals["A_C3_ONLY"] + 2)
    _require(report.get("native_auto_signal_not_gate") is native_signal,
             "C2_SIGNAL_CHANGED")
    status = "PILOT_COMPLETE_NO_GATE" if valid else "PILOT_PARTIAL_RED"
    _require(report.get("status") == status, "STATUS_CHANGED")
    return {"schema": SCHEMA, "status": status, "rows_verified": len(rows),
            "primary_totals": totals, "secondary_totals": secondary,
            "native_c2_invocations": invocations,
            "native_c2_selected": selected, "utility_gate_pass": False,
            "redmi_measured": False, "whole_system_complete": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(verify_report(args.pilot), sort_keys=True))


if __name__ == "__main__":
    main()
