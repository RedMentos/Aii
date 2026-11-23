"""Run49 single-predictor confidence provenance; synthetic software only."""
import unittest

import numpy as np

from v13 import world_jepa as wj


class SinglePredictorConfidenceGuard(unittest.TestCase):
    def setUp(self):
        self.x = np.zeros((16, 2), dtype=float)
        self.a = np.eye(2)[np.arange(16) % 2]
        self.x2 = self.x + self.a

    def test_one_optimizer_step_cannot_invent_ensemble_certainty(self):
        model = wj.WorldJEPA(seed=7, ensemble=1).fit(
            self.x, self.a, self.x2, steps=1, log_every=1)
        # 8 observed rows/action and 1 member => spread is exactly zero,
        # which is missing uncertainty evidence, not certainty.
        conf, labels = model.confidence(self.x[:2], self.a[:2])
        np.testing.assert_array_equal(conf, np.zeros(2))
        self.assertEqual(labels, ['SIMULATION_UNCERTAIN'] * 2)
        self.assertEqual(model._fit_steps, 1)
        self.assertEqual(len(model.preds), 1)

    def test_single_predictor_latent_and_numeric_prediction_still_work(self):
        model = wj.WorldJEPA(seed=7, ensemble=1).fit(
            self.x, self.a, self.x2, steps=1, log_every=1)
        z = model.latent(self.x[:2])
        prediction, spread = model.predict(self.x[:2], self.a[:2])
        self.assertEqual(z.shape, (2, wj.Z))
        self.assertEqual(prediction.shape, (2, wj.Z))
        self.assertTrue(np.isfinite(prediction).all())
        np.testing.assert_array_equal(spread, np.zeros(2))

    def test_two_predictors_keep_bounded_heuristic_path(self):
        model = wj.WorldJEPA(seed=7, ensemble=2).fit(
            self.x, self.a, self.x2, steps=2, log_every=1)
        conf, labels = model.confidence(self.x[:2], self.a[:2])
        self.assertEqual(conf.shape, (2,))
        self.assertTrue(np.isfinite(conf).all())
        self.assertTrue(((0 <= conf) & (conf <= 1)).all())
        self.assertTrue(all(label in ('MODEL_SIMULATION', 'SIMULATION_UNCERTAIN')
                            for label in labels))
        # This is only a coverage/spread/OOD heuristic, not learned utility.


if __name__ == '__main__':
    unittest.main()
