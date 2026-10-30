"""Run13A prospective source-only and fake-lifecycle tests; never native evidence."""
import ast
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import c2_body_fulltask_run13a as m
from scripts import c2_body_fulltask_verify_run13a as verify
from scripts import c2_body_disjoint_paired181_run11v as frozen
from tests.test_c2_body_observer_off_lifecycle_integration import (
    FakeRuntime, fake_audit)
from v13.config import initialize
from v13.runtime import Runtime

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/c2_body_fulltask_run13a_seed211_20261030.json")


def fake_rows():
    rows = []
    for i in range(8):
        for arm in m.ARM_ORDER[i]:
            auto = arm == "F_NATIVE_AUTO"
            flags = {"valid_native": True, "body_offer_roles": [],
                     "expected_offer_roles": [], "observer_mode": "off",
                     "native_c2_invocation": auto, "native_c2_selected": auto}
            row = {"arm": arm, "flags": flags,
                   "score": {"correct": 2 if auto else 0},
                   "secondary_score": {"correct": 0},
                   "full_task": {"strict_full": auto,
                                 "component_points": 3 if auto else 0}}
            if auto:
                row["strict_admission"] = {"matches": True}
            rows.append(row)
    return rows


class Run13ASourceTests(unittest.TestCase):
    def test_frozen_fixture_and_eight_latin_cycles(self):
        f = m.load_fixture(FIXTURE)
        self.assertEqual(f["seed"], 211)
        self.assertEqual(len(f["cases"]), 8)
        self.assertEqual(m.fixture_hash(f["cases"]), m.FIXTURE_SHA256)
        self.assertEqual(len(m.ARM_ORDER), 8)
        self.assertTrue(all(set(order) == set(m.ARMS) for order in m.ARM_ORDER))
        self.assertNotEqual(m.FIXTURE_SHA256, "94cce591dcf9ade126cfdb2d32261543c8334523b6d268295759d9ef7b691df1")

    def test_tampered_fixture_fails_closed(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "tamper.json"
            f = json.loads(FIXTURE.read_text())
            f["cases"][0]["a_days"] += 1
            p.write_text(json.dumps(f))
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE"):
                m.load_fixture(p)

    def test_frozen_full_task_components_and_contradiction(self):
        c = m.load_fixture(FIXTURE)["cases"][0]
        correct = m.full_task_score(c, "Quartz finishes sooner.",
                                    {"correct": 2}, True)
        self.assertEqual(correct["expected"], "Quartz")
        self.assertEqual(correct["component_points"], 3)
        self.assertTrue(correct["strict_full"])
        for answer, status in (
                ("Cedar finishes sooner.", "WRONG"),
                ("Cedar finishes sooner. Quartz finishes sooner.", "CONTRADICTORY"),
                ("Neither is faster.", "ABSTAIN")):
            x = m.full_task_score(c, answer, {"correct": 2}, True)
            self.assertEqual(x["status"], status)
            self.assertEqual(x["component_points"], 2)
            self.assertFalse(x["strict_full"])
        partial = m.full_task_score(c, "Quartz finishes sooner.",
                                    {"correct": 1}, True)
        self.assertEqual(partial["component_points"], 2)
        self.assertFalse(partial["strict_full"])
        invalid = m.full_task_score(c, "Quartz finishes sooner.",
                                    {"correct": 0}, False)
        self.assertEqual(invalid["status"], "INVALID_NATIVE")
        self.assertEqual(invalid["component_points"], 0)

    def test_structural_and_signal_synthetic_no_promotion(self):
        rows = fake_rows()
        r = m.summarize(rows)
        self.assertTrue(r["all_native_structurally_valid"])
        self.assertTrue(r["native_auto_utility_pilot_signal_not_gate"])
        self.assertEqual(r["native_c2_invocations"], 8)
        self.assertEqual(r["strict_full_totals_out_of_8"]["F_NATIVE_AUTO"], 8)
        self.assertEqual(r["score_totals_out_of_16"]["F_NATIVE_AUTO"], 16)
        for k in ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
                  "redmi_measured", "whole_system_complete",
                  "comparative_utility_proven"):
            self.assertFalse(r[k], k)

    def test_signal_and_structural_counterexamples(self):
        rows = fake_rows()
        self.assertFalse(m.summarize(rows[:-1])["all_native_structurally_valid"])
        rows = fake_rows()
        next(r for r in rows if r["arm"] == "F_NATIVE_AUTO")[
            "strict_admission"]["matches"] = False
        self.assertFalse(m.summarize(rows)["all_native_structurally_valid"])
        rows = fake_rows()
        rows[0]["arm"] = "B_B1_ONLY"
        self.assertFalse(m.summarize(rows)["all_native_structurally_valid"])
        rows = fake_rows()
        rows[0]["flags"]["body_offer_roles"] = ["B1_DETAIL"]
        self.assertFalse(m.summarize(rows)["all_native_structurally_valid"])
        rows = fake_rows()
        for r in rows:
            if r["arm"] == "F_NATIVE_AUTO":
                r["full_task"]["strict_full"] = False
        summary = m.summarize(rows)
        self.assertTrue(summary["all_native_structurally_valid"])
        self.assertFalse(summary["native_auto_utility_pilot_signal_not_gate"])
        rows = fake_rows()
        for r in rows:
            if r["arm"] == "F_NATIVE_AUTO":
                r["flags"]["native_c2_selected"] = False
        self.assertFalse(m.summarize(rows)["native_auto_utility_pilot_signal_not_gate"])

    def test_runtime_api_stays_real_and_no_start(self):
        self.assertEqual(list(inspect.signature(Runtime.submit).parameters),
                         ["self", "text"])
        calls = [n for n in ast.walk(ast.parse(inspect.getsource(m.fresh_turn)))
                 if isinstance(n, ast.Call)]
        self.assertTrue(any(isinstance(n.func, ast.Name)
                            and n.func.id == "audit_event" for n in calls))
        self.assertFalse(any(isinstance(n.func, ast.Attribute)
                             and n.func.attr == "start" for n in calls))

    def test_fake_runtime_actual_preclose_postclose(self):
        FakeRuntime.instances.clear()
        case = m.load_fixture(FIXTURE)["cases"][0]
        with TemporaryDirectory() as td:
            root = Path(td)
            home = root / "installed"
            cfg = initialize(home)
            (home / "config/models.json").write_text("{}")
            out = root / "out"
            (out / "raw").mkdir(parents=True)
            (out / "preclose").mkdir()
            with patch.object(m, "Runtime", FakeRuntime), patch.object(
                    m, "audit_event", fake_audit):
                row = m.fresh_turn(home, cfg, case, "A_C3_ONLY", 0, out)
            self.assertEqual(FakeRuntime.instances[-1].submitted,
                             [frozen.prompt(case)])
            self.assertTrue(FakeRuntime.instances[-1].closed)
            self.assertTrue(row["flags"]["valid_native"])
            self.assertEqual(row["full_task"]["status"], "ABSTAIN")
            raw = json.loads((out / "raw/00_A_C3_ONLY.json").read_text())
            pre = json.loads((out / "preclose/00_A_C3_ONLY.json").read_text())
            self.assertEqual(raw["event_id"], pre["event_id"])
            self.assertEqual(raw["full_task"], row["full_task"])
            self.assertEqual(raw["release_capture_phase"], "after_close")
            self.assertFalse(raw["step2_gate_promoted"])

    def test_verifier_fail_closed_without_original_raw(self):
        self.assertNotEqual(verify.SCHEMA, m.SCHEMA)
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "RAW_MISSING"):
                verify.verify(td, FIXTURE)


if __name__ == "__main__":
    unittest.main()
