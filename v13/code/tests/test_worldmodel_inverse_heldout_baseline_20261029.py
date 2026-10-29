"""Preregistered inverse majority baseline must train on train split only.

Synthetic software witness; no native or whole-system utility claim.
"""
import unittest
from unittest import mock
from v13 import world_model as WM


class StoreStub:
    def __init__(self):
        self.saved = None
        self.logs = []
    def set_state(self, key, state):
        self.saved = (key, state)
    def log(self, *args):
        self.logs.append(args)


def cohort(heldout_actions):
    n = 48
    tr, te = WM._split(n)
    assert len(te) == len(heldout_actions)
    held = dict(zip(te, heldout_actions))
    rows = []
    for i in range(n):
        a = held.get(i, "simple")
        s = WM.state_vec(25 + 13 * i, "NORMAL", (i * 7) % 24)
        rows.append({"action_id": "w%d" % i, "s": s, "a": a,
                     "y": [0.3 + i / 100, 1., 0.1 + i / 200],
                     "latent": None})
    return rows, tr, te


class InverseTrainOnlyMajorityBaseline(unittest.TestCase):
    def fit(self, rows):
        store = StoreStub()
        with mock.patch.object(WM, "transitions", return_value=rows):
            state = WM.fit(store, rng_seed=23)
        self.assertEqual(state["status"], "FITTED")
        self.assertEqual(store.saved, (WM.KEY, state))
        return state

    def test_heldout_only_other_action_cannot_raise_baseline(self):
        _, te = WM._split(48)
        rows, tr, held = cohort(["both"] * len(te))
        self.assertEqual(held, te)
        state = self.fit(rows)
        self.assertEqual(state["train_counts"]["simple"], len(tr))
        self.assertEqual(state["counts"]["both"], len(te))
        self.assertEqual(state["metrics"]["held_out"], len(te))
        self.assertEqual(state["metrics"]["inverse_majority_baseline"], 0.0)

    def test_uniform_action_control_keeps_one(self):
        _, te = WM._split(48)
        rows, _, _ = cohort(["simple"] * len(te))
        state = self.fit(rows)
        self.assertEqual(state["metrics"]["inverse_majority_baseline"], 1.0)

    def test_mixed_heldout_uses_frozen_train_majority(self):
        _, te = WM._split(48)
        labels = ["simple" if i % 2 == 0 else "both" for i in range(len(te))]
        rows, _, _ = cohort(labels)
        state = self.fit(rows)
        expected = round(labels.count("simple") / len(labels), 4)
        self.assertEqual(state["metrics"]["inverse_majority_baseline"], expected)


if __name__ == "__main__":
    unittest.main()
