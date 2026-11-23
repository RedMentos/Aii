"""Run137 source-observed Age evidence-ID corruption and opt-in preflight tests."""
from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest

from scripts import age_evidence_finite_candidate as finite
from scripts import age_evidence_id_preflight_candidate as candidate
from scripts import age_state_quarantine_candidate as quarantine
from v13 import age
from v13.config import initialize
from v13.store import Store

GOOD = {"experience": 10000, "competence": .95, "stability": .95,
        "retention": .98, "calibration": .9, "memory_health": .97,
        "safe_self_control": .999, "regression_pass": True}


class Run137AgeEvidenceIdPreflight(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.cfg = initialize(self.home) | {"user_stage_cap": 5}
        self.store = Store(self.home)
        self.controller = age.AgeControl(self.store, self.cfg)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_original_bool_id_corruption_is_blocked_by_direct_age_record(self):
        # Run137's original RED remains in PR #1037 and its raw artifacts.
        # The later direct AgeControl.record candidate closes that historical
        # bypass even when the original finite-only wrapper is called.
        before = self.controller.state()
        with self.assertRaisesRegex(ValueError, "AGE_EVIDENCE_ID_INVALID"):
            finite.record(self.controller, "system", GOOD, evidence_id=True)
        self.assertEqual(self.controller.state(), before)
        self.assertEqual(quarantine.snapshot(self.controller)["status"],
                         "VALID_DIAGNOSTIC_ONLY")
        self.assertFalse(quarantine.snapshot(self.controller)["runtime_enforced"])
        self.assertEqual(self.controller.system_stage(), 0)

    def test_invalid_explicit_ids_refused_before_durable_mutation(self):
        invalid = (True, False, 1, 1.0, 0, "", b"id", [], {}, float("nan"))
        for bad in invalid:
            with self.subTest(evidence_id=repr(bad)):
                before = self.controller.state()
                telemetry = len(self.store.rows("SELECT * FROM telemetry"))
                with self.assertRaisesRegex(ValueError, "AGE_EVIDENCE_ID_INVALID"):
                    candidate.record(self.controller, "system", GOOD, evidence_id=bad)
                self.assertEqual(self.controller.state(), before)
                self.assertEqual(len(self.store.rows("SELECT * FROM telemetry")),
                                 telemetry)
                self.assertEqual(quarantine.snapshot(self.controller)["status"],
                                 "VALID_DIAGNOSTIC_ONLY")

    def test_valid_id_none_and_duplicate_preserve_original_semantics(self):
        candidate.record(self.controller, "system", GOOD, evidence_id=None)
        candidate.record(self.controller, "system", GOOD, evidence_id="run137-id-1")
        before = self.controller.state()
        self.assertEqual(len(before[0]["seen_evidence"]), 2)
        self.assertEqual(quarantine.snapshot(self.controller)["status"],
                         "VALID_DIAGNOSTIC_ONLY")
        with self.assertRaises(ValueError):
            candidate.record(self.controller, "system", GOOD,
                             evidence_id="run137-id-1")
        self.assertEqual(self.controller.state(), before)
        self.assertEqual(self.controller.system_stage(), 0)
        self.assertFalse(self.controller.allowed("short_dream"))

    def test_valid_state_survives_restart_and_freeze(self):
        candidate.record(self.controller, "system", GOOD, evidence_id="run137-a")
        self.controller.freeze(True)
        candidate.record(self.controller, "system", GOOD, evidence_id="run137-b")
        before = self.controller.state()
        self.store.close()
        self.store = Store(self.home)
        self.controller = age.AgeControl(self.store, self.cfg)
        self.assertEqual(self.controller.state(), before)
        self.assertEqual(quarantine.snapshot(self.controller)["status"],
                         "VALID_DIAGNOSTIC_ONLY")
        self.assertEqual(quarantine.guarded_view(self.controller)["system_stage"], 0)
        self.assertFalse(self.controller.allowed("short_dream"))

    def test_metric_validation_still_delegates_to_finite_candidate(self):
        bad = dict(GOOD, competence=float("inf"))
        before = self.controller.state()
        with self.assertRaisesRegex(ValueError, "AGE_METRIC_INVALID:competence"):
            candidate.record(self.controller, "system", bad, evidence_id="valid-id")
        self.assertEqual(self.controller.state(), before)
        self.assertEqual(quarantine.snapshot(self.controller)["status"],
                         "VALID_DIAGNOSTIC_ONLY")


if __name__ == "__main__":
    unittest.main()
