"""STEP2 TP27 Aquila prereg and fail-closed synthetic receipt guards; no native models."""
import copy
import tempfile
import unittest
from pathlib import Path

from scripts import step2_longnote_tp27_native_pilot as pilot


class Step2TP27PilotGuards(unittest.TestCase):
    def test_fixed_new_disjoint_source_and_controls(self):
        dry = pilot.prereg()
        self.assertFalse(dry["native_execution"])
        self.assertEqual(pilot.ARM, "TP")
        self.assertEqual(pilot.SEED, 27)
        self.assertEqual(pilot.FIXTURE_ID, "Aquila")
        self.assertEqual(len(pilot.VARIANTS), 7)
        self.assertEqual(len(dry["registered"]["fixture_sha256"]), 64)

    def test_private_harness_uses_same_patched_z2_module_and_aquila(self):
        self.assertIs(pilot.z2, pilot.z2b.z2)
        original = pilot.z2.FIXTURES
        self.assertEqual(original[0]["id"], "Kestrel")
        with pilot.pre.configured():
            harness = pilot.z2.harness()
            self.assertIs(pilot.z2.FIXTURES, pilot.pre.corpus.FIXTURES)
            self.assertIs(harness.FIXTURES, pilot.pre.corpus.FIXTURES)
            self.assertEqual(harness.FIXTURES[0]["id"], "Aquila")
            self.assertEqual(harness.FIXTURES[0]["type"], "SPLIT")
        self.assertIs(pilot.z2.FIXTURES, original)
        self.assertEqual(pilot.z2.FIXTURES[0]["id"], "Kestrel")

    def test_missing_installed_home_refuses_before_creating_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            target = base / "evidence"
            with self.assertRaises(ValueError):
                pilot.run(base / "missing", target)
            self.assertFalse(target.exists())

    def synthetic_report(self):
        hashes = {"B1_DETAIL": "a" * 64, "B2_GIST": "b" * 64,
                  "C3_LANGUAGE": "c" * 64}
        rows = [
            {"fixture": "Aquila", "variant": v, "status": "RECORDED",
             "processes_reaped": True, "oracle_visible_to_native": False,
             "native_consumer_metrics": {"status": "FINAL"}}
            for v in pilot.VARIANTS
        ]
        report = {
            "rows": rows,
            "preparations": [{"fixture": "Aquila", "status": "RECORDED",
                              "model_sha256": hashes}],
            "source_unchanged": True,
            "installed_artifacts_unchanged": True,
            "all_structural_checks_passed": True,
            "distinct_bodies": True,
            "canonical_gate_pass": False,
            "phone_measured": False,
            "status": "DIAGNOSTIC_INCOMPLETE",
        }
        return report, hashes

    def test_synthetic_guard_never_promotes_one_fixture(self):
        report, hashes = self.synthetic_report()
        result = pilot.verify_report(report, {"offers": 12, "with_question": 12}, hashes)
        self.assertEqual(result["status"], "PASS_SCOPED_ONE_FIXTURE_NATIVE_NO_UTILITY_GATE")
        for change in (
            lambda r: r["rows"].pop(),
            lambda r: r["rows"][0].update(status="ERROR"),
            lambda r: r["rows"][0].update(processes_reaped=False),
            lambda r: r["rows"][0].update(oracle_visible_to_native=True),
            lambda r: r["rows"][0]["native_consumer_metrics"].update(status="ERROR"),
            lambda r: r.update(canonical_gate_pass=True),
            lambda r: r.update(status="UTILITY_PASS_SCOPED"),
            lambda r: r.update(distinct_bodies=False),
            lambda r: r.update(installed_artifacts_unchanged=False),
        ):
            bad = copy.deepcopy(report)
            change(bad)
            with self.subTest(change=repr(change)):
                with self.assertRaises(ValueError):
                    pilot.verify_report(bad, {"offers": 12, "with_question": 12}, hashes)
        with self.assertRaises(ValueError):
            pilot.verify_report(report, {"offers": 12, "with_question": 11}, hashes)


if __name__ == "__main__":
    unittest.main()
