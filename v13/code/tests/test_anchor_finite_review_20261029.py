"""U5 anchor numeric admission RED-first review (software-only, no training)."""
import math
import unittest
from unittest.mock import patch

from v13 import anchor as AN


class Trainer:
    def __init__(self, weight):
        self.cfg = {"targets": ("w1",), "anchor_weight": weight}


class AnchorFiniteReview(unittest.TestCase):
    def test_policy_refuses_unbounded_or_nonfinite_signals(self):
        invalid = (float("nan"), float("inf"), -float("inf"),
                   -0.01, 1.01, True, False, "0.5")
        for bad in invalid:
            with self.subTest(signal=repr(bad)):
                with self.assertRaises(ValueError):
                    AN.policy(bad, .5)
                with self.assertRaises(ValueError):
                    AN.policy(.5, bad)

    def test_active_and_shadow_refuse_invalid_base_weight(self):
        invalid = (float("nan"), float("inf"), -float("inf"),
                   -1.0, True, False, "8")
        for mode in ("ACTIVE", "SHADOW"):
            for bad in invalid:
                with self.subTest(mode=mode, weight=repr(bad)):
                    with patch.object(AN, "novelty", return_value=.5), \
                         patch.object(AN, "stability", return_value=.5), \
                         patch.object(AN, "mode", return_value=mode):
                        with self.assertRaises(ValueError):
                            AN.for_batch(object(), [], Trainer(bad))

    def test_valid_weight_behavior_and_unmeasured_sentinel(self):
        with patch.object(AN, "novelty", return_value=.5), \
             patch.object(AN, "stability", return_value=.5):
            for mode in ("ACTIVE", "SHADOW"):
                with patch.object(AN, "mode", return_value=mode):
                    row, override = AN.for_batch(object(), [], Trainer(8.))
                    self.assertTrue(math.isfinite(row["proposed_anchor_weight"]))
                    self.assertGreaterEqual(row["proposed_anchor_weight"], 0.)
                    self.assertEqual(row["applied"], mode == "ACTIVE")
                    if mode == "ACTIVE":
                        self.assertEqual(override, {"anchor_weight": row["proposed_anchor_weight"]})
                    else:
                        self.assertIsNone(override)
                    missing, missing_override = AN.for_batch(object(), [], Trainer(None))
                    self.assertFalse(missing["applied"])
                    self.assertIsNone(missing_override)

    def test_existing_finite_policy_bounds_preserved(self):
        for novelty in (0., .5, 1.):
            for stability in (0., .5, 1.):
                for shared in (True, False):
                    result = AN.policy(novelty, stability, shared)
                    self.assertTrue(math.isfinite(result["multiplier"]))
                    self.assertGreaterEqual(result["multiplier"], result["floor"])
                    self.assertLessEqual(result["multiplier"], AN.MAX_MULT)


if __name__ == "__main__":
    unittest.main()
