"""LP3 trajectory source/decision tests; no master or native model required."""
import tempfile
import unittest
from pathlib import Path

from scripts import lp3_optimizer_trajectory as d
from scripts.lp3_heldout_utility import SEED, STEPS, LR, fixture, audit_fixture


def row(step, pred=1., proj=1., finite=True):
    return {'step': step, 'loss_finite': finite,
            'pred_finite': finite, 'proj_finite': finite,
            'pred_abs_sum': pred if finite else None,
            'proj_abs_sum': proj if finite else None}


class LP3OptimizerTrajectoryTests(unittest.TestCase):
    def test_frozen_original_training_constants(self):
        self.assertEqual((SEED, STEPS, LR), (109, 24, .005))
        self.assertTrue(audit_fixture(fixture()))
        self.assertEqual(len(fixture()), 6)

    def test_first_zero_gradient_not_hidden_by_later_recovery(self):
        trace = [row(0), row(1, pred=0.), row(2), row(3, proj=0.)]
        self.assertEqual(d.first_issue(trace), {'step': 1, 'kind': 'ZERO_GRADIENT'})

    def test_first_nonfinite_gradient_is_explicit(self):
        trace = [row(0), row(1, finite=False), row(2, pred=0.)]
        self.assertEqual(d.first_issue(trace), {'step': 1, 'kind': 'NONFINITE'})

    def test_all_positive_trace_has_no_issue(self):
        self.assertIsNone(d.first_issue([row(i) for i in range(24)]))

    def test_optimizer_nonfinite_is_a_reported_issue(self):
        trace = [row(0), {**row(1), 'optimizer_moments_finite': False,
                          'update_abs_sum': 1.}]
        self.assertEqual(d.first_issue(trace), {'step': 1, 'kind': 'OPTIMIZER_NONFINITE'})

    def test_execution_requires_opt_in_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'result.json'
            with self.assertRaisesRegex(ValueError, 'Explicit'):
                d.main(['--master', tmp, '--out', str(out)])
            self.assertFalse(out.exists())

    def test_hash_binds_trainable_parameter_bytes(self):
        import torch
        from torch import nn
        class Fake:
            def __init__(self):
                self.predictor = nn.Linear(3, 2)
                self.prefix_projector = nn.Linear(2, 3)
        m = Fake()
        before = d._param_hash(m)
        with torch.no_grad():
            m.predictor.weight[0, 0] += 1.
        self.assertNotEqual(d._param_hash(m), before)

    def test_gradient_stat_reports_missing_and_nonfinite(self):
        import torch
        from torch import nn
        m = nn.Linear(2, 1)
        self.assertEqual(d._grad_stat(m, torch)['missing_tensors'], 2)
        (m(torch.ones(1, 2)).sum()).backward()
        good = d._grad_stat(m, torch)
        self.assertTrue(good['finite'])
        self.assertGreater(good['abs_sum'], 0.)
        m.weight.grad[0, 0] = float('nan')
        bad = d._grad_stat(m, torch)
        self.assertFalse(bad['finite'])
        self.assertEqual(bad['nonfinite_elements'], 1)

    def test_mixed_missing_and_nonfinite_gradients_are_not_reported_safe(self):
        import torch
        from torch import nn
        m = nn.Linear(2, 1)
        for bad in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(nonfinite=repr(bad)):
                m.weight.grad = None
                m.bias.grad = torch.tensor([bad], dtype=m.bias.dtype)
                stat = d._grad_stat(m, torch)
                self.assertFalse(stat['finite'])
                self.assertIsNone(stat['abs_sum'])
                self.assertEqual(stat['missing_tensors'], 1)
                self.assertEqual(stat['nonfinite_elements'], 1)
        m.bias.grad = torch.ones_like(m.bias)
        stat = d._grad_stat(m, torch)
        self.assertTrue(stat['finite'])
        self.assertEqual(stat['missing_tensors'], 1)
        self.assertEqual(stat['nonfinite_elements'], 0)
        self.assertEqual(stat['abs_sum'], 0.)

    def test_finite_large_gradients_do_not_overflow_float32_sum(self):
        import torch
        from torch import nn
        m = nn.Linear(10, 10)
        m.weight.grad = torch.full_like(m.weight, 1e38)
        m.bias.grad = torch.full_like(m.bias, 1e38)
        result = d._grad_stat(m, torch)
        self.assertTrue(result['finite'])
        self.assertGreater(result['abs_sum'], 1e39)


if __name__ == '__main__':
    unittest.main()
