"""Run132 persisted Age-state read-only quarantine, software-only checks."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from scripts import age_state_quarantine_candidate as candidate
from v13 import age
from v13.config import initialize
from v13.store import Store

GOOD = {"experience": 10000, "competence": .95, "stability": .95,
        "retention": .98, "calibration": .9, "memory_health": .97,
        "safe_self_control": .999, "regression_pass": True}


class Run132AgeStateQuarantine(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.cfg = initialize(self.home) | {"user_stage_cap": 5}
        self.store = Store(self.home)
        self.controller = age.AgeControl(self.store, self.cfg)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def _persist(self, changed):
        _, version = self.controller.state()
        self.store.set_state(age.STATE_KEY, changed, expected=version)

    def test_valid_default_state_and_read_only_view(self):
        original, version = self.controller.state()
        self.assertIs(candidate.verify_state(original), original)
        snap = candidate.snapshot(self.controller)
        self.assertEqual(snap["status"], "VALID_DIAGNOSTIC_ONLY")
        self.assertEqual(snap["effective_stage"], 0)
        self.assertEqual(snap["build_ceiling"], 0)
        self.assertFalse(snap["runtime_enforced"])
        self.assertEqual(candidate.guarded_view(self.controller)["system_stage"], 0)
        self.assertEqual(self.controller.state()[1], version)

    def test_valid_evidence_freeze_and_dynamic_capability(self):
        for i in range(4):
            self.controller.record("system", GOOD, evidence_id="run132-good-" + str(i))
        self.controller.open_window("haptics")
        self.controller.freeze(True)
        state, _ = self.controller.state()
        self.assertIs(candidate.verify_state(state), state)
        self.assertEqual(candidate.snapshot(self.controller)["effective_stage"], 0)
        self.assertFalse(self.controller.allowed("short_dream"))

    def test_all_nonfinite_and_boolean_maturity_refused_in_memory(self):
        for name in ("trust", "retention", "calibration", "stability", "competence"):
            for value in (float("nan"), float("inf"), -float("inf"), True, False, -1, 1.1):
                state = age.default_state()
                state["system"]["maturity"][name] = value
                with self.subTest(metric=name, value=value):
                    with self.assertRaisesRegex(candidate.AgeStateIntegrityError, "AGE_MATURITY_CORRUPT"):
                        candidate.verify_state(state)

    def test_invalid_stages_and_counters_refused(self):
        cases = [
            ("bool_stage", lambda s: s["system"].update(stage=True), "AGE_STAGE_CORRUPT"),
            ("high_stage", lambda s: s["capabilities"]["tool"].update(stage=6), "AGE_STAGE_CORRUPT"),
            ("negative_count", lambda s: s["system"].update(evidence_count=-1), "AGE_COUNT_CORRUPT"),
            ("bool_fail", lambda s: s["system"].update(fail_streak=True), "AGE_FAIL_STREAK_CORRUPT"),
            ("duplicate_pass", lambda s: s["system"].update(pass_streak=["x", "x"]), "AGE_PASS_STREAK_CORRUPT"),
            ("bad_noise", lambda s: s["system"].update(noise={"mad": -0.1, "n": 3}), "AGE_NOISE_CORRUPT"),
            ("bad_hold", lambda s: s["system"].update(plasticity_hold={"stage": 9, "until": 3}), "AGE_PLASTICITY_HOLD_CORRUPT"),
            ("missing_cap", lambda s: s["capabilities"].pop("tool"), "AGE_CAPABILITY_SET_CORRUPT"),
            ("bad_seen", lambda s: s.update(seen_evidence=["x", "x"]), "AGE_SEEN_EVIDENCE_CORRUPT"),
            ("bad_revision", lambda s: s.update(revision="other"), "AGE_STATE_REVISION_CORRUPT"),
        ]
        for label, mutate, reason in cases:
            state = age.default_state()
            mutate(state)
            with self.subTest(case=label):
                with self.assertRaisesRegex(candidate.AgeStateIntegrityError, reason):
                    candidate.verify_state(state)

    def test_persisted_finite_corruption_survives_restart_but_diagnostic_refuses(self):
        state = age.default_state()
        state["system"]["maturity"]["trust"] = 2.0
        self._persist(state)
        before, version = self.controller.state()
        before_telemetry = len(self.store.rows("SELECT * FROM telemetry"))
        self.store.close()
        self.store = Store(self.home)
        self.controller = age.AgeControl(self.store, self.cfg)
        report = candidate.snapshot(self.controller)
        self.assertEqual(report["status"], "QUARANTINED_DIAGNOSTIC_ONLY")
        self.assertEqual(report["reason"], "AGE_MATURITY_CORRUPT:system:trust")
        self.assertEqual(report["granted_rights"], [])
        self.assertIsNone(report["budgets"])
        self.assertIsNone(report["effective_stage"])
        self.assertFalse(report["runtime_enforced"])
        with self.assertRaises(candidate.AgeStateIntegrityError):
            candidate.guarded_view(self.controller)
        after, after_version = self.controller.state()
        self.assertEqual(after, before)
        self.assertEqual(after_version, version)
        self.assertEqual(len(self.store.rows("SELECT * FROM telemetry")), before_telemetry)

    def test_quarantine_does_not_raise_stage_or_repair_state(self):
        state = age.default_state()
        state["system"]["stage"] = True
        self._persist(state)
        before, version = self.controller.state()
        first = candidate.snapshot(self.controller)
        second = candidate.snapshot(self.controller)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "QUARANTINED_DIAGNOSTIC_ONLY")
        self.assertEqual(self.controller.state(), (before, version))
        self.assertEqual(self.controller.system_stage(), 0)
        self.assertFalse(self.controller.allowed("short_dream"))

    def test_falsy_persisted_corruption_not_masked_by_agecontrol_state(self):
        # Original AgeControl.state() uses "st or default_state()"; this must
        # not make an existing corrupt row look like a genuinely absent row.
        for payload in ({}, None, [], 0, False):
            with self.subTest(payload=payload):
                self._persist(payload)
                # The original public reader masks these stored falsy values.
                self.assertEqual(self.controller.state()[0], age.default_state())
                report = candidate.snapshot(self.controller)
                self.assertEqual(report["status"], "QUARANTINED_DIAGNOSTIC_ONLY")
                self.assertEqual(report["granted_rights"], [])
                with self.assertRaises(candidate.AgeStateIntegrityError):
                    candidate.guarded_view(self.controller)

    def test_invalid_shape_rejected_without_mutation(self):
        for invalid in (None, [], {}, {"revision": age.REVISION}):
            with self.subTest(value=invalid):
                with self.assertRaises(candidate.AgeStateIntegrityError):
                    candidate.verify_state(invalid)
        self.assertEqual(candidate.snapshot(self.controller)["status"], "VALID_DIAGNOSTIC_ONLY")


if __name__ == "__main__":
    unittest.main()
