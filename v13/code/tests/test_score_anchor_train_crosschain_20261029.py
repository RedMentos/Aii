"""STEP2 score admission and U5/AG6 trainer veto coexist on a real Store.

Source-only synthetic fixtures, no native training or gate promotion.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.utility import paired_utility
from v13.agi.weights import WeightConsolidation


class FitSpy:
    method = "synthetic-spy"

    def __init__(self):
        self.cfg = {"anchor_weight": float("nan"), "targets": ("w1", "w2", "w3")}
        self.calls = 0

    def fit(self, items, base, cancel=None, deadline=None):
        self.calls += 1
        raise AssertionError("invalid anchor must veto trainer.fit")


class ScoreAnchorTrainCrossOrgan(unittest.TestCase):
    def test_invalid_score_and_anchor_never_create_weight_authority(self):
        variants = ("b1_only", "b2_only", "both_none", "both_exact",
                    "both_control", "same_policy_dual", "prompt_only_dual")
        fixtures = ("one", "two")
        rows = [
            {"variant": variant, "fixture": fixture,
             "score": {"utility": float("nan") if
                       variant == "both_exact" and fixture == "one" else .5}}
            for variant in variants for fixture in fixtures
        ]
        report = paired_utility(rows, fixtures)
        self.assertFalse(report["complete"])
        self.assertFalse(report["scoped_utility_gate_pass"])
        self.assertIn("both_exact", report["coverage_errors"])

        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            runtime.sleep.cycle.set_policy("enabled", "off")
            try:
                event = runtime.store.event(runtime.session, "Project Aurora budget?")
                runtime.memory.feedback(event["event_id"], "fact", "120 Euro")
                spy = FitSpy()
                wc = WeightConsolidation(
                    runtime.store,
                    runtime.cfg | {"learning_mode": "SHADOW_UPDATE"},
                    trainer=spy)
                staged = wc.stage(require_replay_pass=False)
                self.assertIn(staged["status"], ("STAGED", "STAGED_SHADOW"))
                bid = staged["batch_id"]
                result = wc.train(bid)
                self.assertEqual(result["status"], "ANCHOR_INVALID")
                self.assertEqual(spy.calls, 0)
                self.assertIsNone(result["trainer"])
                self.assertEqual(wc.batch(bid)["status"], "ANCHOR_INVALID")
            finally:
                runtime.close()

            restarted = Runtime(home)
            try:
                wc2 = WeightConsolidation(
                    restarted.store,
                    restarted.cfg | {"learning_mode": "SHADOW_UPDATE"},
                    trainer=FitSpy())
                self.assertEqual(wc2.batch(bid)["status"], "ANCHOR_INVALID")
                self.assertEqual(wc2.batch(bid).get("trainer"), None)
            finally:
                restarted.close()


if __name__ == "__main__":
    unittest.main()
