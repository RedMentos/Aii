"""Run375 RED-first: B3 human rating and channel probabilities fail closed on nonfinite."""
import copy
import math
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.callosum import Callosum


class FiniteCallosumRatingRun375(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.callosum = Callosum(self.runtime.store)
        self.callosum.note("run375_event", "run375_msg", "B1_DETAIL", "B2_GIST",
                           "CONTROL", "CONTROL", False, 0.0)
        self.before = copy.deepcopy(self.callosum._load()[0])

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def test_bad_human_ratings_never_mutate_channel_utility(self):
        for bad in (float("nan"), float("inf"), float("-inf"), True, False, "0.8", None):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    self.callosum.on_rating("run375_event", bad)
                self.assertEqual(self.callosum._load()[0], self.before)

    def test_valid_human_rating_and_clamp_preserved(self):
        self.assertEqual(self.callosum.on_rating("run375_event", 0.7)["updated"], 1)
        state = self.callosum._load()[0]
        channel = state["dirs"]["B1_TO_B2"]["u"]["CONTROL"]
        self.assertEqual(channel["n"], 1)
        self.assertAlmostEqual(channel["v"], 0.7)
        self.callosum.on_rating("run375_event", 2.0)
        self.assertGreaterEqual(self.callosum._load()[0]["dirs"]["B1_TO_B2"]["u"]["CONTROL"]["v"], 0.7)

    def test_corrupted_nonfinite_utility_cannot_produce_probability_vector(self):
        for bad in (float("nan"), float("inf"), float("-inf"), True, "0.5", None):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    Callosum.probabilities({"u": {"CONTROL": {"v": bad, "n": 5}}})

    def test_finite_softmax_preserves_floor_and_latent_unavailable(self):
        p = Callosum.probabilities({"u": {
            "NO_MESSAGE": {"v": 0.0, "n": 5},
            "CONTROL": {"v": 0.5, "n": 5},
            "SOURCE_EXACT": {"v": -0.2, "n": 5},
        }})
        self.assertEqual(p["LATENT"], 0.0)
        self.assertAlmostEqual(sum(p.values()), 1.0, places=3)
        self.assertTrue(all(math.isfinite(x) and x > 0 for k, x in p.items() if k != "LATENT"))


if __name__ == "__main__":
    unittest.main()
