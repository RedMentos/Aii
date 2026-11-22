"""Sleep A/B/C replay policy must reject nonfinite and bool-typed weights."""
import math
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import sleep as S


class SleepMixFinitePolicyTests(unittest.TestCase):
    def policy(self, **weights):
        p = S.default_policy()
        p["mix"].update(weights)
        return p

    def test_nan_and_infinity_mix_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=str(value)), self.assertRaises(ValueError):
                S.validate_policy(self.policy(recent=value))

    def test_nonfinite_total_and_huge_integer_rejected(self):
        for weights in (
            {"recent": 1e308, "protected_old": 1e308, "failure": 1e308},
            {"recent": 10**1000},
        ):
            with self.subTest(case=str(list(weights)[:2])), self.assertRaises(ValueError):
                S.validate_policy(self.policy(**weights))

    def test_boolean_negative_and_nonnumeric_weights_rejected(self):
        for value in (True, False, -0.1, "0.5", None):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                S.validate_policy(self.policy(recent=value))

    def test_bad_mix_shape_raises_valueerror(self):
        for value in (None, [], ["recent", "protected_old", "failure"], "bad"):
            p = S.default_policy()
            p["mix"] = value
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                S.validate_policy(p)

    def test_bool_quiet_hours_rejected(self):
        for hours in ([True, False], [22, True], [False, 7]):
            p = S.default_policy()
            p["quiet_hours"] = hours
            with self.subTest(hours=hours), self.assertRaises(ValueError):
                S.validate_policy(p)

    def test_valid_zero_component_and_overnight_hours(self):
        p = self.policy(recent=0., protected_old=0.75, failure=0.25)
        p["quiet_hours"] = [22, 7]
        self.assertEqual(S.validate_policy(p), p)
        self.assertTrue(S.in_quiet_hours(p, 0) in (True, False))
        self.assertEqual(S.validate_policy(S.default_policy()), S.default_policy())

    def test_invalid_operator_policy_does_not_mutate_store(self):
        with tempfile.TemporaryDirectory() as d:
            r = Runtime(Path(d))
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                before = r.store.state(S.POLICY_KEY, None)
                with self.assertRaises(ValueError):
                    r.sleep.cycle.set_policy("mix.recent", "nan")
                self.assertEqual(r.store.state(S.POLICY_KEY, None), before)
                with self.assertRaises(ValueError):
                    r.sleep.cycle.set_policy("mix.recent", "inf")
                self.assertEqual(r.store.state(S.POLICY_KEY, None), before)
                valid = r.sleep.cycle.set_policy("mix.recent", "0.4")
                self.assertEqual(valid["mix"]["recent"], 0.4)
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
