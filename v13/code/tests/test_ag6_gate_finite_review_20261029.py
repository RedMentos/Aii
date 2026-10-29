"""AG6 measured quality must reject malformed numeric evidence before human requests.

Store-only synthetic trainer; no model, learning authority, or Redmi proof.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.weights import WeightConsolidation


class SyntheticGateTrainer:
    method = "synthetic-gate"

    def __init__(self, kl=.01):
        self.kl = kl
        self.cfg = {"anchor_weight": .2, "targets": ("w1",)}

    def fit(self, items, base_generation, cancel=None, deadline=None):
        return {"artifact": "synthetic-gate-candidate", "hash": "a" * 64,
                "method": self.method, "metrics": {"kl_to_base": self.kl}}


class FiniteGateReview(unittest.TestCase):
    def _exercise(self, name, *, base=None, candidate=None, kl=.01,
                  learned=1., delta=.02, drift=None, expected="GATE_FAIL"):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            runtime.sleep.cycle.set_policy("enabled", "off")
            bid = None
            try:
                event = runtime.store.event(runtime.session, "Source-backed project budget?")
                runtime.memory.feedback(event["event_id"], "fact", "120 EUR")
                cfg = runtime.cfg | {"learning_mode": "SHADOW_UPDATE",
                                     "retention_max_delta": delta}
                wc = WeightConsolidation(runtime.store, cfg,
                                         trainer=SyntheticGateTrainer(kl))
                staged = wc.stage(require_replay_pass=False)
                self.assertEqual(staged["status"], "STAGED", name)
                bid = staged["batch_id"]
                self.assertEqual(wc.train(bid)["status"], "TRAINED", name)
                be = {"overall": .8, "unseen": .75, "near_miss_leak": 0.}
                ce = {"overall": .8, "unseen": .75,
                      "forgetting": {"rate": 0.}, "near_miss_leak": 0.}
                if base: be.update(base)
                if candidate: ce.update(candidate)
                result = wc.gate(bid, be, ce, learned, drift=drift)
                self.assertEqual(result["status"], expected, name)
                self.assertEqual(result["request_id"] is None,
                                 expected == "GATE_FAIL", name)
                self.assertEqual(runtime.store.one(
                    "SELECT COUNT(*) AS n FROM requests "
                    "WHERE kind='WEIGHT_CONSOLIDATION'")["n"],
                    0 if expected == "GATE_FAIL" else 1, name)
                if expected == "GATE_FAIL":
                    self.assertFalse(result["gate"]["checks"]["numeric_admission"], name)
                    self.assertTrue(result["gate"]["invalid_numeric_fields"], name)
            finally:
                runtime.close()
            restarted = Runtime(home)
            try:
                self.assertEqual(WeightConsolidation(
                    restarted.store, restarted.cfg,
                    trainer=SyntheticGateTrainer()).batch(bid)["status"],
                    expected, name)
            finally:
                restarted.close()

    def test_malformed_quality_cannot_create_approval_request(self):
        cases = [
            ("boolean_overall", {"base": {"overall": True},
                                 "candidate": {"overall": True}}),
            ("negative_kl", {"kl": -.01}),
            ("negative_forgetting", {"candidate": {"forgetting": {"rate": -.1}}}),
            ("oversized_recall", {"learned": 1.2}),
            ("string_drift_pass", {"drift": {"passed": "false"}}),
            ("negative_infinite_baseline", {"base": {"overall": float("-inf")}}),
            ("nonfinite_delta", {"delta": float("inf")}),
            ("nonfinite_unseen_without_base", {"base": {"unseen": None},
                                               "candidate": {"unseen": float("nan")}}),
            ("boolean_forgetting", {"candidate": {"forgetting": {"rate": False}}}),
        ]
        for name, args in cases:
            with self.subTest(case=name):
                self._exercise(name, **args)

    def test_valid_measured_control_still_requires_human_approval(self):
        self._exercise("valid_control", drift={"passed": True},
                       expected="PENDING_USER")


if __name__ == "__main__":
    unittest.main()
