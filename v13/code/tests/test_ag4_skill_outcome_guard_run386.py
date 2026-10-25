"""Run386 RED-first: only genuine typed outcomes may promote AG4 skills."""
import copy
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi import hub


class SkillOutcomeGuardRun386(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.lib = hub(self.runtime).skills
        self.lib.propose("plan_summary", [{"route": "gist"}], trigger="plan summary")

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def state(self):
        return copy.deepcopy(self.lib.box.load()[0])

    def test_nonboolean_success_is_never_counted_or_persisted(self):
        before = self.state()
        for bad in ("false", "true", "", 0, 1, None, [], {}):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    self.lib.record("plan_summary", bad, parity=1.)
                self.assertEqual(self.state(), before)

    def test_parity_requires_finite_probability_not_bool_or_string(self):
        before = self.state()
        for bad in (-1., 1.0001, 2., float("nan"), float("inf"), float("-inf"), True, False, "1", None if False else "nan", 10**1000):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    self.lib.record("plan_summary", True, parity=bad, family="plan")
                self.assertEqual(self.state(), before)

    def test_untrusted_reports_cannot_promote_shadow_skill(self):
        for _ in range(3):
            self.lib.record("plan_summary", True, parity=1.)
        self.assertEqual(self.lib.get("plan_summary")["stage"], "SHADOW")
        before = self.state()
        for _ in range(8):
            with self.assertRaises(ValueError):
                self.lib.record("plan_summary", "false", parity=2.)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.lib.get("plan_summary")["stage"], "SHADOW")

    def test_real_outcomes_preserve_stage_transitions_and_low_parity_blocks(self):
        for _ in range(3):
            self.lib.record("plan_summary", True, parity=1)
        self.assertEqual(self.lib.get("plan_summary")["stage"], "SHADOW")
        for _ in range(8):
            self.lib.record("plan_summary", True, parity=0)
        self.assertEqual(self.lib.get("plan_summary")["stage"], "SHADOW")
        self.assertEqual(self.lib.get("plan_summary")["uses"], 11)
        # A fresh, distinct skill can still reach TRUSTED with real parity.
        self.lib.propose("second_summary", [{"route": "detail"}], trigger="second summary")
        for _ in range(11):
            self.lib.record("second_summary", True, parity=1.)
        self.assertEqual(self.lib.get("second_summary")["stage"], "TRUSTED")

    def test_self_origin_age0_cannot_auto_promote(self):
        self.lib.propose("self_summary", [{"route": "gist"}], trigger="self summary", origin="SELF")
        for _ in range(11):
            self.lib.record("self_summary", True, parity=1.)
        sk = self.lib.get("self_summary")
        self.assertEqual(sk["stage"], "SHADOW")
        self.assertEqual(sk["pending"], "TRUSTED_NEEDS_AGE_OR_USER")


if __name__ == "__main__":
    unittest.main()
