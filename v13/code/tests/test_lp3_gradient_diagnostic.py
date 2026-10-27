"""No-model preregistered LP3 native gradient diagnostic source contract."""
import unittest

from scripts.lp3_gradient_diagnostic import SMOKE, _sum_grad, main
from scripts.lp3_heldout_utility import fixture, SEED


class LP3GradientDiagnosticTests(unittest.TestCase):
    def test_fixed_six_plus_two_prompts_and_seed(self):
        self.assertEqual(SEED, 109)
        self.assertEqual(len(fixture()), 6)
        self.assertEqual(SMOKE, (
            ('What is the name of my cat?', 'Brombeer'),
            ('What is the name of my dog?', 'Tromso'),
        ))
        self.assertEqual(len({r['train'] for r in fixture()}), 6)

    def test_absent_gradients_are_recorded_as_zero_not_fake_pass(self):
        class P:
            grad = None
        self.assertEqual(_sum_grad([P(), P()]), 0)

    def test_native_requires_explicit_opt_in(self):
        with self.assertRaisesRegex(ValueError, 'Explicit --execute-native'):
            main(['--master', '/not/needed', '--out', '/not/needed'])


if __name__ == '__main__':
    unittest.main()
