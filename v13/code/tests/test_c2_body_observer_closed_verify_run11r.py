"""Synthetic-only adversarial tests for Run11R independent raw verifier."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts import c2_body_observer_closed_run11r as m
from scripts import c2_body_observer_closed_verify_run11r as v


def write_json(path, obj):
    path.write_text(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n")


def synthetic_all_invalid(directory):
    """A structurally complete RED report, explicitly NOT native evidence."""
    directory = Path(directory)
    rawdir = directory / "raw"
    rawdir.mkdir()
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
        "score_totals_out_of_8": totals,
        "secondary_totals_out_of_8": totals,
        "native_c2_invocations": 0, "native_c2_selected": 0,
        "pilot_signal_not_gate": False,
        "native_auto_signal_not_gate": False,
    }
    write_json(directory / "report.json", report)
    return report


class VerifyRun11R(unittest.TestCase):
    def test_structural_red_does_not_become_native_green(self):
        with tempfile.TemporaryDirectory() as d:
            synthetic_all_invalid(d)
            verdict = v.verify_report(d)
            self.assertEqual(verdict["rows_verified"], 24)
            self.assertEqual(verdict["status"], "PILOT_PARTIAL_RED")
            self.assertFalse(verdict["utility_gate_pass"])
            self.assertFalse(verdict["redmi_measured"])

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
