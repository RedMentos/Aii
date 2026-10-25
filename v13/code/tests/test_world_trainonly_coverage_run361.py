"""Run361: World counterfactual support must be TRAIN-only and count independent sources.

Synthetic NumPy fixture only; no causal/native/Redmi claims. Held-out data
may measure error but cannot silently expand the predictor's support.
"""
import math
import unittest
from unittest.mock import patch

from v13 import world_model as W


class Store:
    def __init__(self):
        self.value = None
    def set_state(self, key, value, expected=None):
        self.value = value
    def state(self, key, default=None):
        return self.value if self.value is not None else default, 1
    def log(self, *args, **kwargs):
        pass


def rows():
    out = []
    for i in range(80):
        group = "source-group-" + str(i // 20)
        role = W.ACTIONS[i % 4]
        out.append({"action_id": "action-" + str(i), "event_id": group,
                    "s": W.state_vec(100 + i, "NORMAL", 1 + (i // 20) * 5 + (i % 20) / 100),
                    "a": role,
                    "y": [math.log1p(1 + (i % 4)), 1.0, math.log1p(30 + (i % 5)) / 8],
                    "latent": None})
    return out


class WorldTrainOnlyCoverageRun361(unittest.TestCase):
    def fit(self):
        data = rows()
        store = Store()
        with patch.object(W, "transitions", return_value=data):
            state = W.fit(store, rng_seed=361)
        self.assertEqual(state["status"], "FITTED")
        return store, state, data

    def test_coverage_states_and_groups_exclude_all_heldout_rows(self):
        store, state, data = self.fit()
        groups = [t["event_id"] for t in data]
        train, heldout = W._split(len(data), groups)
        self.assertGreater(len(heldout), 0)
        self.assertTrue(set(groups[i] for i in train).isdisjoint(
            set(groups[i] for i in heldout)))
        for role in W.ACTIONS:
            expected = [data[i]["s"] for i in train if data[i]["a"] == role][-256:]
            expected_groups = [groups[i] for i in train if data[i]["a"] == role][-256:]
            self.assertEqual(state["states"][role], expected)
            self.assertEqual(state["state_groups"][role], expected_groups)
            self.assertEqual(len(state["states"][role]), 15)
        self.assertIsNotNone(W.load(store))

    def test_duplicate_actions_do_not_fake_independent_coverage_confidence(self):
        store, state, data = self.fit()
        point = data[0]["s"]
        cov = W.coverage(state, point, data[0]["a"])
        self.assertEqual(cov["samples"], 15)
        self.assertEqual(cov["independent_sources"], 3)
        cf = W.counterfactual(store, point, data[0]["a"])
        self.assertEqual(cf["authority"], "HYPOTHESIS")
        self.assertLessEqual(cf["confidence"], 1 - math.exp(-3 / W.COVER_N) + 1e-4)
        self.assertEqual(cf["label"], "SIMULATION_UNCERTAIN")

    def test_missing_training_source_group_metadata_never_grants_support(self):
        store, state, data = self.fit()
        broken = dict(state)
        broken.pop("state_groups")
        broken["model_sha256"] = W._state_digest(broken)
        cov = W.coverage(broken, data[0]["s"], data[0]["a"])
        self.assertEqual(cov["independent_sources"], 0)
        self.assertFalse(cov["in_support"])
        cf = W.counterfactual(store, data[0]["s"], data[0]["a"], broken)
        self.assertEqual(cf["label"], "SIMULATION_UNCERTAIN")
        self.assertEqual(cf["confidence"], 0.0)


if __name__ == "__main__":
    unittest.main()
