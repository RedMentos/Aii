"""RED-first AG6 trainer boundary: invalid U5 coefficient must not reach fit."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.agi.weights import WeightConsolidation


class SpyTrainer:
    method = "fake"
    def __init__(self, weight):
        self.cfg = {"anchor_weight": weight, "targets": ("w1", "w2", "w3")}
        self.calls = 0

    def fit(self, items, base, cancel=None, deadline=None):
        self.calls += 1
        return {"artifact": "synthetic.gguf", "hash": "synthetic",
                "method": "fake", "metrics": {}}


class TrainingBoundaryReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        e = self.r.store.event(self.r.session, "Project Aurora budget?")
        self.r.memory.feedback(e["event_id"], "fact", "120 Euro")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def stage(self, trainer):
        w = WeightConsolidation(
            self.r.store, self.r.cfg | {"learning_mode": "SHADOW_UPDATE"},
            trainer=trainer)
        row = w.stage(require_replay_pass=False)
        self.assertIn(row["status"], ("STAGED", "STAGED_SHADOW"))
        return w, row["batch_id"]

    def test_nonfinite_weight_vetoes_fit_and_persists_invalid_status(self):
        trainer = SpyTrainer(float("nan"))
        w, bid = self.stage(trainer)
        result = w.train(bid)
        self.assertEqual(result["status"], "ANCHOR_INVALID")
        self.assertEqual(trainer.calls, 0)
        self.assertEqual(trainer.cfg["targets"], ("w1", "w2", "w3"))
        self.assertNotIn("trainer", result)
        self.assertEqual(w.batch(bid)["status"], "ANCHOR_INVALID")
        with self.assertRaises(ValueError):
            w.train(bid)

    def test_nonfinite_stability_vetoes_fit(self):
        trainer = SpyTrainer(8.)
        w, bid = self.stage(trainer)
        with patch("v13.anchor.stability", return_value=float("nan")):
            result = w.train(bid)
        self.assertEqual(result["status"], "ANCHOR_INVALID")
        self.assertEqual(trainer.calls, 0)

    def test_unrelated_anchor_unavailability_preserves_old_fallback(self):
        trainer = SpyTrainer(8.)
        w, bid = self.stage(trainer)
        with patch("v13.anchor.for_batch", side_effect=RuntimeError("unavailable")):
            result = w.train(bid)
        self.assertEqual(result["status"], "TRAINED")
        self.assertEqual(trainer.calls, 1)
        self.assertEqual(result["anchor"]["error"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()
