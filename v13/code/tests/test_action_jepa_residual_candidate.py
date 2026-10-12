"""Round-2 residual action-JEPA candidate on explicit synthetic test data only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_jepa_residual_candidate as rc
import tests.test_action_jepa_objective as objective_tests


class ResidualCandidateTests(unittest.TestCase):
    def base(self):
        return {'dim': 3, 'seed': 13, 'lr': .05, 'max_update_norm': .1, 'ema_decay': .99, 'retention_max_delta': 0.}

    def test_untrained_candidate_equals_mean_delta_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, _ = objective_tests.ActionObjectiveTests().fixture(root)
            report = rc.train(path, root / 'out', self.base(), [1, 40])
            for part, scores in report['before'].items():
                self.assertAlmostEqual(scores['fixed_target_prediction_mse'], scores['mean_delta_mse'], places=12)

    def test_calibration_only_selection_and_no_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, doc = objective_tests.ActionObjectiveTests().fixture(root)
            report = rc.train(path, root / 'out', self.base(), [1, 40])
            calib = report['calibration_selection_mse']
            self.assertEqual(report['chosen_steps'], min((1, 40), key=lambda s: (calib[str(s)], s)))
            self.assertEqual(report['selection_partition'], 'calibration')
            self.assertEqual(len(report['unchosen_arms']), 1)
            self.assertFalse(report['gates']['observed_input_declared'])
            self.assertFalse(report['candidate_gate_pass'])
            self.assertEqual(report['receiver_authority'], 0)
            again = rc.train(path, root / 'again', self.base(), [1, 40])
            self.assertEqual(report['after'], again['after'])
            out = rc.predict(root / 'out/candidate.npz', root / 'out/metrics.json', [doc['rows'][0]['context_state']], '1')
            self.assertEqual(np.asarray(out['predicted_future_latents']).shape, (1, 3))
            self.assertFalse(out['receiver_injection'])
            with (root / 'out/candidate.npz').open('ab') as f:
                f.write(b'x')
            with self.assertRaisesRegex(ValueError, 'Candidate bytes'):
                rc.predict(root / 'out/candidate.npz', root / 'out/metrics.json', [[0, 0, 0, 0]], '1')


if __name__ == '__main__':
    unittest.main()
