"""Run131 software-only finite Age evidence fail-closed counterexamples."""
from __future__ import annotations
from copy import deepcopy
import math
from pathlib import Path
import tempfile
import unittest

from scripts import age_evidence_finite_candidate as candidate
from v13 import age
from v13.config import initialize
from v13.store import Store

GOOD = {"experience": 10000, "competence": .95, "stability": .95,
        "retention": .98, "calibration": .9, "memory_health": .97,
        "safe_self_control": .999, "regression_pass": True}


class Run131FiniteAgeEvidence(unittest.TestCase):
    def test_original_gate_accepts_infinity_candidate_refuses(self):
        bad = dict(GOOD, competence=float("inf"))
        self.assertTrue(age.gate_pass(bad, 1))
        with self.assertRaisesRegex(ValueError, "AGE_METRIC_INVALID"):
            candidate.gate_pass(bad, 1)

    def test_original_gate_accepts_boolean_metric_candidate_refuses(self):
        bad = dict(GOOD, stability=True)
        self.assertTrue(age.gate_pass(bad, 1))
        with self.assertRaisesRegex(ValueError, "AGE_METRIC_INVALID"):
            candidate.gate_pass(bad, 1)

    def test_all_metrics_reject_nan_inf_bool_out_of_bounds_missing(self):
        for name in age.METRICS:
            for value in (float("nan"), float("inf"), -float("inf"), True, False, -0.1, 1.1, None):
                bad = dict(GOOD, **{name: value})
                with self.subTest(metric=name, value=value), self.assertRaisesRegex(ValueError, "AGE_METRIC_INVALID"):
                    candidate.validate(bad)

    def test_experience_rejects_invalid_types_and_negative(self):
        for value in (True, False, -1, 1.0, float("inf"), None, "100"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "AGE_EXPERIENCE_INVALID"):
                candidate.validate(dict(GOOD, experience=value))

    def test_regression_flag_requires_actual_bool(self):
        for value in (1, 0, "true", None, float("nan")):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "AGE_REGRESSION_FLAG_INVALID"):
                candidate.validate(dict(GOOD, regression_pass=value))

    def test_stage_and_band_are_finite_typed_and_bounded(self):
        for value in (True, -1, 6, 1.0, None):
            with self.subTest(stage=value), self.assertRaisesRegex(ValueError, "AGE_STAGE_INVALID"):
                candidate.gate_pass(GOOD, value)
        for value in (True, float("nan"), float("inf"), -0.01, 1.1):
            with self.subTest(band=value), self.assertRaisesRegex(ValueError, "AGE_BAND_INVALID"):
                candidate.gate_pass(GOOD, 1, value)

    def test_valid_evidence_keeps_original_gate_semantics(self):
        for stage in range(6):
            self.assertEqual(candidate.gate_pass(GOOD, stage), age.gate_pass(GOOD, stage))
        self.assertEqual(candidate.gate_pass(dict(GOOD, competence=0.), 1),
                         age.gate_pass(dict(GOOD, competence=0.), 1))
        self.assertEqual(candidate.validate(GOOD), GOOD)

    def test_invalid_evidence_does_not_mutate_store_or_telemetry(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cfg = initialize(home) | {"user_stage_cap": 5}
            store = Store(home)
            try:
                ctl = age.AgeControl(store, cfg, build_ceiling=5)
                candidate.record(ctl, "system", GOOD, evidence_id="good-1")
                before = deepcopy(ctl.state()[0])
                before_version = ctl.state()[1]
                before_telemetry = len(store.rows("SELECT * FROM telemetry"))
                for bad in (dict(GOOD, competence=float("inf")),
                            dict(GOOD, memory_health=True),
                            dict(GOOD, experience=-1),
                            dict(GOOD, regression_pass=1)):
                    with self.assertRaises(ValueError):
                        candidate.record(ctl, "system", bad)
                self.assertEqual(ctl.state()[0], before)
                self.assertEqual(ctl.state()[1], before_version)
                self.assertEqual(len(store.rows("SELECT * FROM telemetry")), before_telemetry)
            finally:
                store.close()

    def test_default_build_ceiling_stays_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cfg = initialize(home) | {"user_stage_cap": 5}
            store = Store(home)
            try:
                ctl = age.AgeControl(store, cfg)
                for i in range(5):
                    candidate.record(ctl, "system", GOOD, evidence_id="good-" + str(i))
                self.assertEqual(ctl.system_stage(), 0)
                self.assertFalse(ctl.allowed("short_dream"))
            finally:
                store.close()

    def test_simulated_stage_hysteresis_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cfg = initialize(home) | {"user_stage_cap": 5}
            store = Store(home)
            try:
                ctl = age.AgeControl(store, cfg, build_ceiling=5)
                candidate.record(ctl, "system", GOOD, evidence_id="good-1")
                candidate.record(ctl, "system", GOOD, evidence_id="good-2")
                self.assertEqual(ctl.system_stage(), 0)
                with self.assertRaises(ValueError):
                    candidate.record(ctl, "system", dict(GOOD, competence=float("nan")))
                self.assertEqual(ctl.system_stage(), 0)
                candidate.record(ctl, "system", GOOD, evidence_id="good-3")
                self.assertEqual(ctl.system_stage(), 1)
                ctl.freeze(True)
                for i in range(4, 8):
                    candidate.record(ctl, "system", GOOD, evidence_id="good-" + str(i))
                self.assertEqual(ctl.system_stage(), 1)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
