"""Synthetic-only adversarial tests for Run11V independent seed181 raw verifier."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts import c2_body_disjoint_paired181_run11v as m
from scripts import c2_body_disjoint_paired181_verify_run11v as v


def write_json(path, obj):
    path.write_text(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n")


def synthetic_all_invalid(directory):
    """A structurally complete RED report, explicitly NOT native evidence."""
    directory = Path(directory)
    rawdir = directory / "raw"
    rawdir.mkdir()
    (directory / "preclose").mkdir()
    rows = []
    for i in range(24):
        f = m.FIXTURES[i // 6]
        arm = m.ARM_ORDER[i // 6][i % 6]
        row = {"index": i, "fixture": f["project"], "arm": arm,
               "error_type": "SyntheticFailure", "error": "no native execution",
               "flags": {"valid_native": False, "native_c2_invocation": False,
                         "native_c2_selected": False},
               "score": {"a": False, "b": False, "correct": 0, "out_of": 2}}
        rows.append(row)
        write_json(rawdir / f"{i:02d}_{arm}.json", row)
    totals = {a: 0 for a in m.ARMS}
    report = {
        "schema": m.SCHEMA, "status": "PILOT_PARTIAL_RED",
        "seed": m.SEED, "fixture_sha256": m.FIXTURE_SHA256,
        "fixtures": [dict(f) for f in m.FIXTURES], "arms": m.ARMS,
        "arm_order": m.ARM_ORDER, "rows": rows,
        "model_verification": {k: {"ok": True, "hash_checked": True}
                               for k in ("needle", "language", "body", "gist")},
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        "step2_gate_promoted": False, "b3_promoted": False,
        "body_jepa_available": False, "redmi_measured": False,
        "whole_system_complete": False, "comparative_utility_proven": False,
        "score_totals_out_of_8": dict(totals),
        "secondary_totals_out_of_8": dict(totals),
        "native_c2_invocations": 0, "native_c2_selected": 0,
        "pilot_signal_not_gate": False,
        "native_auto_signal_not_gate": False,
    }
    write_json(directory / "report.json", report)
    return report



def inject_valid_synthetic_c3(directory, report, output=None):
    """One positive *synthetic* replay row; other 23 remain explicit RED."""
    directory = Path(directory)
    fixture = m.FIXTURES[0]
    arm = "A_C3_ONLY"
    output = output or "Fern: 153 Euro remaining. Slate: 44 Euro remaining."
    audit = {
        "event_id": "synthetic-event", "output": output,
        "checks": {"source_refs_valid": True}, "source_errors": [],
        "offers": [],
        "output_metadata": {
            "route": {"source": "OPERATOR_ROUTE_OVERRIDE"},
            "c2_packet": {"route": "simple"},
            "runner": {"role": "C3_LANGUAGE", "actual_model": m.LANGUAGE_MODEL},
            "model_generated": True,
        },
    }
    receipts = [{"role": "C3_LANGUAGE", "process_reaped": True}]
    flags = m.row_evidence(audit, arm, receipts)
    assert flags["valid_native"] is True  # software stub, NOT native evidence
    raw = {
        "index": 0, "fixture": fixture["project"], "arm": arm,
        "prompt": m.prompt(fixture), "event_id": "synthetic-event",
        "session_id": "synthetic-session", "raw_audit": audit,
        "final_output": output, "context_packet": None,
        "body_process_releases_before_close": [],
        "body_process_releases": receipts,
        "release_capture_phase": "after_close",
        "native_c2_alive_before_close": False,
        "source_exact_before_close": False,
        "native_c2_process_reaped": True, "native_c2_pid": None,
        "b1_model_key": "body", "b2_model_key": "gist",
        "b2_control": "two_body", "flags": flags,
        "score": m.score_pair(fixture, output),
        "secondary_score": m.score_primary(fixture, output),
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        "step2_gate_promoted": False, "b3_promoted": False,
        "body_jepa_available": False, "redmi_measured": False,
        "whole_system_complete": False,
    }
    row = {k: value for k, value in raw.items()
           if k not in ("raw_audit", "context_packet", "prompt", "route_info")}
    report["rows"][0] = row
    report["score_totals_out_of_8"][arm] = row["score"]["correct"]
    report["secondary_totals_out_of_8"][arm] = row["secondary_score"]["correct"]
    write_json(directory / "report.json", report)
    write_json(directory / "raw" / f"00_{arm}.json", raw)
    final_only = {"body_process_releases", "release_capture_phase",
                  "native_c2_process_reaped", "native_c2_pid",
                  "flags", "score", "secondary_score"}
    witness = {k: value for k, value in raw.items() if k not in final_only}
    write_json(directory / "preclose" / f"00_{arm}.json", witness)
    return raw

class VerifyRun11V(unittest.TestCase):
    def test_structural_red_does_not_become_native_green(self):
        with tempfile.TemporaryDirectory() as d:
            synthetic_all_invalid(d)
            verdict = v.verify_report(d)
            self.assertEqual(verdict["rows_verified"], 24)
            self.assertEqual(verdict["status"], "PILOT_PARTIAL_RED")
            self.assertFalse(verdict["utility_gate_pass"])
            self.assertFalse(verdict["redmi_measured"])

    def test_synthetic_primary_and_secondary_totals_are_independent(self):
        with tempfile.TemporaryDirectory() as d:
            report = synthetic_all_invalid(d)
            self.assertIsNot(report["score_totals_out_of_8"],
                             report["secondary_totals_out_of_8"])
            report["secondary_totals_out_of_8"]["A_C3_ONLY"] = 1
            self.assertEqual(report["score_totals_out_of_8"]["A_C3_ONLY"], 0)

    def test_forged_positive_row_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            report = synthetic_all_invalid(d)
            report["rows"][0]["score"]["correct"] = 1
            write_json(Path(d) / "report.json", report)
            with self.assertRaisesRegex(ValueError, "RAW_REPORT_DIVERGENCE"):
                v.verify_report(d)

    def test_extra_raw_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            synthetic_all_invalid(d)
            (Path(d) / "raw" / "unregistered.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "RAW_FILES_MISMATCH"):
                v.verify_report(d)

    def test_missing_raw_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            synthetic_all_invalid(d)
            (Path(d) / "raw" / f"00_{m.ARM_ORDER[0][0]}.json").unlink()
            with self.assertRaisesRegex(ValueError, "RAW_FILES_MISMATCH"):
                v.verify_report(d)

    def test_changed_source_fixture_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            report = synthetic_all_invalid(d)
            report["fixtures"][0]["budget"] += 1
            write_json(Path(d) / "report.json", report)
            with self.assertRaisesRegex(ValueError, "FIXTURE_CONTENT_CHANGED"):
                v.verify_report(d)

    def test_negative_gate_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as d:
            report = synthetic_all_invalid(d)
            report["step2_gate_promoted"] = True
            write_json(Path(d) / "report.json", report)
            with self.assertRaisesRegex(ValueError, "GATE_CHANGED_step2_gate_promoted"):
                v.verify_report(d)

    def test_forged_valid_without_original_audit_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            report = synthetic_all_invalid(d)
            row = report["rows"][0]
            row["flags"]["valid_native"] = True
            write_json(Path(d) / "report.json", report)
            write_json(Path(d) / "raw" / f"00_{row['arm']}.json", row)
            with self.assertRaisesRegex(ValueError, "ERROR_ROW_FORGED"):
                v.verify_report(d)


    def test_one_synthetic_positive_row_replayed_without_promoting_red(self):
        with tempfile.TemporaryDirectory() as d:
            report = synthetic_all_invalid(d)
            inject_valid_synthetic_c3(d, report)
            verdict = v.verify_report(d)
            self.assertEqual(verdict["status"], "PILOT_PARTIAL_RED")
            self.assertEqual(verdict["primary_totals"]["A_C3_ONLY"], 2)
            self.assertFalse(verdict["utility_gate_pass"])

    def test_tampered_synthetic_native_score_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            report = synthetic_all_invalid(d)
            raw = inject_valid_synthetic_c3(d, report)
            raw["final_output"] = "Fern: 154 Euro remaining."
            write_json(Path(d) / "raw" / "00_A_C3_ONLY.json", raw)
            with self.assertRaisesRegex(ValueError, "RAW_REPORT_DIVERGENCE|SOURCE_OR_EVENT_CHANGED"):
                v.verify_report(d)

    def test_tampered_postclose_release_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            report = synthetic_all_invalid(d)
            raw = inject_valid_synthetic_c3(d, report)
            raw["body_process_releases"] = []
            write_json(Path(d) / "raw" / "00_A_C3_ONLY.json", raw)
            with self.assertRaisesRegex(ValueError, "NATIVE_FLAGS_REPLAY_MISMATCH"):
                v.verify_report(d)



    def test_equation_tuple_json_list_roundtrip_replays(self):
        with tempfile.TemporaryDirectory() as d:
            report = synthetic_all_invalid(d)
            output = ("Fern: 396 - 243 = 153 Euro remaining.\n"
                      "Slate: 396 - 352 = 44 Euro remaining.")
            raw = inject_valid_synthetic_c3(d, report, output=output)
            equations = raw["secondary_score"]["equation"]["a"]["equations"]
            self.assertTrue(equations)
            self.assertIsInstance(equations[0], tuple)  # pre-wire scorer
            verdict = v.verify_report(d)  # JSON stores lists, not tuples
            self.assertEqual(verdict["status"], "PILOT_PARTIAL_RED")
            self.assertFalse(verdict["utility_gate_pass"])

    def test_same_line_dual_owner_equations_remain_ambiguous(self):
        # The frozen diagnostic assigns equations only to a single named
        # option per line. This is not a verifier or scorer defect.
        f = m.FIXTURES[0]
        output = ("Fern: 396 - 243 = 153 Euro remaining. "
                  "Slate: 396 - 352 = 44 Euro remaining.")
        result = m.score_pair(f, output)["equation"]
        for option in ("a", "b"):
            self.assertEqual(result[option]["status"], "AMBIGUOUS")
            self.assertEqual(result[option]["equations"], [])
            self.assertEqual(result[option]["ambiguous_lines"], 1)

    def test_missing_preclose_witness_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            report = synthetic_all_invalid(d)
            inject_valid_synthetic_c3(d, report)
            (Path(d) / "preclose" / "00_A_C3_ONLY.json").unlink()
            with self.assertRaisesRegex(ValueError, "PRECLOSE_WITNESS_MISSING"):
                v.verify_report(d)

    def test_changed_preclose_witness_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            report = synthetic_all_invalid(d)
            inject_valid_synthetic_c3(d, report)
            path = Path(d) / "preclose" / "00_A_C3_ONLY.json"
            witness = json.loads(path.read_text())
            witness["prompt"] = "forged"
            write_json(path, witness)
            with self.assertRaisesRegex(ValueError, "PRECLOSE_WITNESS_CHANGED"):
                v.verify_report(d)

    def test_report_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            synthetic_all_invalid(d)
            p = Path(d) / "report.json"
            target = Path(d) / "saved.json"
            p.rename(target)
            p.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "RAW_MISSING_OVERSIZE_OR_SYMLINK"):
                v.verify_report(d)


if __name__ == "__main__":
    unittest.main()
