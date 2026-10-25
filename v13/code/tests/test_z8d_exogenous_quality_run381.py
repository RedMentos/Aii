"""Run381 source-only controls for synthetic exogenous-quality Age reopening."""
import random
import tempfile
import unittest
from pathlib import Path

from scripts import z8d_exogenous_quality_probe as Q
from scripts import z8_age_reopen as Z


class Z8DQualityControls(unittest.TestCase):
    def test_quality_signal_is_seeded_and_phase_correlated_by_construction(self):
        stream = Z.stream(301)
        before = [(e["t"], e["phase"], e["y"]) for e in stream]
        a = Q.quality_flags(stream, 301)
        b = Q.quality_flags(stream, 301)
        self.assertEqual(a, b)
        self.assertEqual(len(a), len(stream))
        self.assertEqual(set(a), {Q.QUALITY_LOW, Q.QUALITY_HIGH})
        self.assertEqual(before, [(e["t"], e["phase"], e["y"]) for e in stream])
        # This is a synthetic *upper-bound* signal, not measured source quality.
        noisy = [v for v, e in zip(a, stream) if e["phase"] == "noisy"]
        clean = [v for v, e in zip(a, stream) if e["phase"] != "noisy"]
        self.assertGreater(noisy.count(Q.QUALITY_LOW) / len(noisy), .7)
        self.assertLess(clean.count(Q.QUALITY_LOW) / len(clean), .2)

    def test_quality_policy_only_consumes_prior_window_and_error_streak(self):
        self.assertEqual(Q.quality_policy(.8, .4, 4), .5)
        self.assertEqual(Q.quality_policy(.3, .9, 2), .9)
        self.assertEqual(Q.quality_policy(.3, .9, 2, allow_reopen=False), .3)
        self.assertEqual(Q.quality_policy(.4, .9, 0), .4)

    def test_real_age_sqlite_restart_and_no_current_window_lookahead(self):
        stream = Z.stream(302)
        flags = Q.quality_flags(stream, 302)
        with tempfile.TemporaryDirectory() as home:
            a = Q.run(stream, flags, "quality", Path(home) / "quality")
            b = Q.run(stream, flags, "quality_restart", Path(home) / "restart")
        self.assertEqual(a, b)
        self.assertEqual(a["quality_prior_every_25"][0], Q.QUALITY_HIGH)
        self.assertEqual(a["quality_prior_every_25"][1], Q.QUALITY_HIGH)
        self.assertEqual(a["quality_prior_every_25"][2],
                         round(sum(flags[:Z.WINDOW]) / Z.WINDOW, 6))

    def test_identical_arms_cannot_fake_a_quality_utility_pass(self):
        stream = Z.stream(303)
        flags = Q.quality_flags(stream, 303)
        with tempfile.TemporaryDirectory() as home:
            a = Q.run(stream, flags, "quality", Path(home) / "quality")
        raw = {arm: [a] for arm in Q.ARMS}
        verdict, criteria = Q.verdict(raw, [303])
        self.assertEqual(verdict, "Z8D_SYNTHETIC_QUALITY_FAIL")
        self.assertFalse(criteria["K2_reopen_helps"]["pass"])
        self.assertFalse(criteria["K8_quality_specificity"]["pass"])


if __name__ == "__main__":
    unittest.main()
