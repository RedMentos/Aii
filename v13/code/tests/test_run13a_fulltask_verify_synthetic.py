"""Run13A 32-row verifier replay/tamper tests on synthetic closed raw.

This test deliberately stubs the native witness/classifier. It tests the
independent verifier's file, score, report and negative-gate replay only;
it is NOT Linux-native evidence or C2 invocation proof.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import c2_body_fulltask_run13a as m
from scripts import c2_body_fulltask_verify_run13a as v
from scripts import c2_body_disjoint_paired181_run11v as frozen

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/c2_body_fulltask_run13a_seed211_20261030.json")


def write(path, obj):
    path.write_text(json.dumps(obj, sort_keys=True, allow_nan=False) + "\n")


def build_synthetic(root):
    root = Path(root)
    (root / "raw").mkdir()
    (root / "preclose").mkdir()
    cases = m.load_fixture(FIXTURE)["cases"]
    rows = []
    for i, case in enumerate(cases):
        for arm in m.ARM_ORDER[i]:
            idx = len(rows)
            auto = arm == "F_NATIVE_AUTO"
            name = f"{idx:02d}_{arm}.json"
            expected = (case["a"] if case["a_days"] < case["b_days"]
                        else case["b"])
            output = (
                f"{case['a']} leaves {case['budget'] - case['a_cost']} Euro. "
                f"{case['b']} leaves {case['budget'] - case['b_cost']} Euro. "
                f"{expected} finishes sooner.")
            score = frozen.score_pair(case, output)
            secondary = frozen.score_primary(case, output)
            full = m.full_task_score(case, output, score, True)
            flags = {
                "valid_native": True, "body_offer_roles": [],
                "expected_offer_roles": [], "observer_mode": "off",
                "native_c2_invocation": auto, "native_c2_selected": auto,
                "route": "simple", "runner_role": "C3_LANGUAGE",
            }
            event = f"synthetic-{idx}"
            pre = {
                "index": idx, "fixture": case["project"], "arm": arm,
                "event_id": event, "session_id": f"s-{idx}",
                "prompt": frozen.prompt(case), "final_output": output,
                "raw_audit": {
                    "event_id": event, "output": output,
                    "synthetic_flags": flags,
                },
                "route_info": {"source": "SYNTHETIC_ONLY"},
                "context_packet": {}, "source_exact_before_close": True,
                "native_c2_pid": 321 if auto else None,
                "native_c2_alive_before_close": auto,
                "body_process_releases_before_close": [],
            }
            raw = {
                **pre,
                "body_process_releases": [
                    {"role": "C3_LANGUAGE", "process_reaped": True}],
                "native_c2_process_reaped": auto,
                "release_capture_phase": "after_close",
                "flags": flags, "score": score,
                "secondary_score": secondary, "full_task": full,
                "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
                "step2_gate_promoted": False, "b3_promoted": False,
                "body_jepa_available": False, "redmi_measured": False,
                "whole_system_complete": False,
            }
            row = {
                "index": idx, "fixture": case["project"], "arm": arm,
                "event_id": event, "final_output": output,
                "flags": flags, "score": score,
                "secondary_score": secondary, "full_task": full,
            }
            if auto:
                row["strict_admission"] = {"matches": True}
                write(root / "raw" / f"{idx:02d}_STRICT_ADMISSION.json",
                      row["strict_admission"])
            write(root / "preclose" / name, pre)
            write(root / "raw" / name, raw)
            rows.append(row)
    report = {
        "schema": m.SCHEMA, "seed": m.SEED,
        "fixture_sha256": m.FIXTURE_SHA256,
        "fixtures": cases, "arms": list(m.ARMS),
        "arm_order": [list(x) for x in m.ARM_ORDER],
        "model_verification": {
            k: {"ok": True, "hash_checked": True} for k in m.ROLES},
        "rows": rows, **m.summarize(rows),
    }
    write(root / "report.json", report)
    return report


def replay(root):
    def fake_witness(audit, arm, releases, **kwargs):
        return audit["synthetic_flags"]
    with patch.object(m, "zero_offer_witness", side_effect=fake_witness), \
            patch.object(v, "classify", return_value={"matches": True}):
        return v.verify(root, FIXTURE)


class Run13ASyntheticReplayTests(unittest.TestCase):
    def test_complete_32_row_score_replay_is_not_native_proof(self):
        with TemporaryDirectory() as td:
            build_synthetic(td)
            result = replay(td)
            self.assertEqual(result["rows_verified"], 32)
            self.assertEqual(result["native_c2_invocations"], 8)
            self.assertEqual(result["status"], "PILOT_COMPLETE_NO_GATE")
            self.assertFalse(result["utility_gate_promoted"])
            self.assertFalse(result["redmi_measured"])
            self.assertFalse(result["whole_system_complete"])

    def test_full_task_tamper_rejected_even_if_report_unchanged(self):
        with TemporaryDirectory() as td:
            build_synthetic(td)
            p = Path(td) / "raw/00_A_C3_ONLY.json"
            d = json.loads(p.read_text())
            d["full_task"]["component_points"] += 1
            write(p, d)
            with self.assertRaisesRegex(ValueError, "FULL_TASK_SCORE_REPLAY_CHANGED"):
                replay(td)

    def test_precise_preclose_tamper_rejected(self):
        with TemporaryDirectory() as td:
            build_synthetic(td)
            p = Path(td) / "preclose/00_A_C3_ONLY.json"
            d = json.loads(p.read_text())
            d["event_id"] = "foreign"
            write(p, d)
            with self.assertRaisesRegex(ValueError, "PRECLOSE_WITNESS_CHANGED"):
                replay(td)

    def test_source_prompt_tamper_rejected(self):
        with TemporaryDirectory() as td:
            build_synthetic(td)
            p = Path(td) / "raw/00_A_C3_ONLY.json"
            d = json.loads(p.read_text())
            d["prompt"] = "FOREIGN"
            write(p, d)
            pre = Path(td) / "preclose/00_A_C3_ONLY.json"
            witness = json.loads(pre.read_text())
            witness["prompt"] = "FOREIGN"
            write(pre, witness)
            with self.assertRaisesRegex(ValueError, "SOURCE_OUTPUT_IDENTITY_CHANGED"):
                replay(td)

    def test_summary_signal_tamper_rejected(self):
        with TemporaryDirectory() as td:
            build_synthetic(td)
            p = Path(td) / "report.json"
            d = json.loads(p.read_text())
            d["native_auto_utility_pilot_signal_not_gate"] = not d[
                "native_auto_utility_pilot_signal_not_gate"]
            write(p, d)
            with self.assertRaisesRegex(ValueError, "SUMMARY_CHANGED"):
                replay(td)

    def test_missing_strict_file_rejected(self):
        with TemporaryDirectory() as td:
            build_synthetic(td)
            (Path(td) / "raw/03_STRICT_ADMISSION.json").unlink()
            with self.assertRaisesRegex(ValueError, "RAW_FILES_CHANGED"):
                replay(td)


if __name__ == "__main__":
    unittest.main()
