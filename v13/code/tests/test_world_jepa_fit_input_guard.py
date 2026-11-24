"""World-JEPA SHADOW fit input integrity; software-only, no native training."""
import unittest
import numpy as np
from v13 import world_jepa as wj


class WorldJEPAFitInputGuard(unittest.TestCase):
    def setUp(self):
        self.X = np.array([[0., 1.], [1., 0.]])
        self.A = np.eye(2)
        self.X2 = np.array([[1., 0.], [0., 1.]])

    def test_valid_two_row_zero_step_shadow_control_remains_supported(self):
        model = wj.WorldJEPA(seed=0, ensemble=1).fit(
            self.X, self.A, self.X2, steps=0
        )
        self.assertTrue(np.isfinite(model._ztrain).all())
        self.assertEqual(len(model._action_counts), 2)
        # Historical shuffled/zero-action controls remain valid inputs.
        zero = wj.WorldJEPA(seed=0, ensemble=1).fit(
            self.X, np.zeros_like(self.A), self.X2, steps=0
        )
        self.assertEqual(sum(zero._action_counts), 0)

    def test_invalid_transition_shapes_and_nonfinite_values_rejected_before_fit(self):
        cases = {
            "single": (self.X[:1], self.A[:1], self.X2[:1]),
            "rank": (self.X.ravel(), self.A, self.X2),
            "action_rows": (self.X, self.A[:1], self.X2),
            "next_shape": (self.X, self.A, self.X2[:, :1]),
            "no_features": (np.empty((2, 0)), self.A, np.empty((2, 0))),
            "no_actions": (self.X, np.empty((2, 0)), self.X2),
            "too_many_features": (np.zeros((2, 4097)), self.A, np.zeros((2, 4097))),
            "too_many_actions": (self.X, np.zeros((2, 65)), self.X2),
            "nonfinite_input": (np.array([[np.nan, 1.], [1., 0.]]), self.A, self.X2),
            "nonfinite_action": (self.X, np.array([[np.inf, 0.], [0., 1.]]), self.X2),
            "nonfinite_next": (self.X, self.A, np.array([[0., 1.], [0., np.nan]])),
            "object": (self.X.astype(object), self.A, self.X2),
            "complex": (self.X.astype(complex), self.A, self.X2),
        }
        for name, (x, a, x2) in cases.items():
            with self.subTest(name=name):
                model = wj.WorldJEPA(seed=0, ensemble=1)
                with self.assertRaises(ValueError):
                    model.fit(x, a, x2, steps=0)
                self.assertFalse(hasattr(model, "enc"))

    def test_invalid_configuration_rejected_before_fit(self):
        for kwargs in ({"steps": -1}, {"steps": 1.0}, {"steps": True},
                       {"log_every": 0}, {"log_every": False}):
            with self.subTest(kwargs=kwargs):
                model = wj.WorldJEPA(seed=0, ensemble=1)
                with self.assertRaises(ValueError):
                    model.fit(self.X, self.A, self.X2, **kwargs)
                self.assertFalse(hasattr(model, "enc"))
        for seed, ensemble in ((-1, 1), (0, 0), (0, 17), (True, 1), (0, True)):
            with self.subTest(seed=seed, ensemble=ensemble):
                model = wj.WorldJEPA(seed=seed, ensemble=ensemble)
                with self.assertRaises(ValueError):
                    model.fit(self.X, self.A, self.X2, steps=0)
                self.assertFalse(hasattr(model, "enc"))


if __name__ == "__main__":
    unittest.main()
