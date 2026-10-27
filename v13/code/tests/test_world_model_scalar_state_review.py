"""T8 scalar ndarray input guard: RED expected TypeError before minimal source fix."""
import unittest
import numpy as np
from v13 import world_model as wm


class ScalarStateReview(unittest.TestCase):
    def test_scalar_ndarrays_are_invalid_not_exceptions(self):
        for scalar in (np.array(1.0), np.array(2), np.array(True)):
            with self.subTest(scalar=repr(scalar)):
                self.assertFalse(wm._finite_vector(scalar, 4))

    def test_coverage_scalar_is_invalid(self):
        st = {'states': {'simple': [[.1, .2, .3, .4]]}}
        for scalar in (np.array(1.0), np.array(True)):
            with self.subTest(scalar=repr(scalar)):
                out = wm.coverage(st, scalar, 'simple')
                self.assertTrue(out['invalid'])
                self.assertEqual(out['samples'], 0)
                self.assertFalse(out['in_support'])

    def test_counterfactual_scalar_fails_closed(self):
        st = {'revision': wm.REVISION, 'status': 'FITTED',
              'support_scope': 'TRAIN_SPLIT_ONLY_HELDOUT_EXCLUDED'}
        for scalar in (np.array(1.0), np.array(True)):
            with self.subTest(scalar=repr(scalar)):
                out = wm.counterfactual(None, scalar, 'simple', st=st)
                self.assertEqual(out['confidence'], 0.)
                self.assertIsNone(out['prediction'])
                self.assertEqual(out['reason'], 'INVALID_NUMERIC_EVIDENCE')
                self.assertEqual(out['label'], 'SIMULATION_UNCERTAIN')

    def test_valid_vectors_and_malformed_lists_unchanged(self):
        self.assertTrue(wm._finite_vector(np.array([.1, .2, .3, .4]), 4))
        self.assertTrue(wm._finite_vector([0., 1., 2., 3.], 4))
        self.assertFalse(wm._finite_vector([0., 1., 2.], 4))
        self.assertFalse(wm._finite_vector([0., True, 2., 3.], 4))
        self.assertFalse(wm._finite_vector([0., float('inf'), 2., 3.], 4))


if __name__ == '__main__':
    unittest.main()
