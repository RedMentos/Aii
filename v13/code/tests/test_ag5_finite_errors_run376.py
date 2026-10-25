"""Run376 RED-first: AG5 invalid prediction error must not masquerade as success."""
import copy
import math
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi import hub


class FiniteCuriosityErrorsRun376(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.curiosity = hub(self.runtime).curiosity
        self.curiosity.observe("known", 0.9)
        self.before = copy.deepcopy(self.curiosity.box.load()[0])

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def test_nonfinite_and_untyped_errors_never_enter_learning_history(self):
        for bad in (float("nan"), float("inf"), float("-inf"), True, False, "0.2", None):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    self.curiosity.observe("known", bad)
                self.assertEqual(self.curiosity.box.load()[0], self.before)
                with self.assertRaises(ValueError):
                    self.curiosity.observe("new_region", bad)
                self.assertEqual(self.curiosity.box.load()[0], self.before)

    def test_finite_learning_progress_and_age_zero_choice_preserved(self):
        for error in (0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2):
            self.curiosity.observe("known", error)
        values = self.curiosity.values()
        self.assertGreater(values["known"]["learning_progress"], 0)
        self.assertEqual(self.curiosity.choose(origin="USER"), "known")
        self.assertIsNone(self.curiosity.choose(origin="SELF"))
        self.assertTrue(math.isfinite(self.curiosity.modulators("known")["M_progress"]))

    def test_finite_out_of_range_values_keep_original_clamping(self):
        self.curiosity.observe("bounded", -0.5)
        self.curiosity.observe("bounded", 2.0)
        errors = self.curiosity.box.load()[0]["regions"]["bounded"]["errors"]
        self.assertEqual(errors, [0.0, 1.0])


if __name__ == "__main__":
    unittest.main()
