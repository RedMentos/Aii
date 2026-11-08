"""Pooled held-out metrics must fail closed before model state persistence."""
import unittest
import numpy as np
from v13 import world_model as wm


class TestPooledHeldoutErrors(unittest.TestCase):
    def test_finite_values(self):
        p=np.array([[2., 1., 3.]])
        y=np.array([[1., 0., 2.]])
        tr=np.array([[0., 0., 0.], [2., 0., 2.]])
        mae,base,mean=wm.pooled_heldout_errors(p,y,tr)
        np.testing.assert_allclose(mae,[1.,1.,1.])
        np.testing.assert_allclose(base,[0.,0.,1.])
        np.testing.assert_allclose(mean,[1.,0.,1.])

    def test_finite_inputs_can_overflow_difference(self):
        p=np.array([[1e308,0.,0.]])
        y=np.array([[-1e308,0.,0.]])
        with self.assertRaisesRegex(ValueError,'T8_NONFINITE_POOLED_HELDOUT_ERROR'):
            wm.pooled_heldout_errors(p,y,np.zeros((2,3)))

    def test_finite_inputs_can_overflow_baseline(self):
        p=np.zeros((1,3))
        y=np.zeros((1,3))
        tr=np.array([[1e308,0.,0.],[1e308,0.,0.]])
        with self.assertRaisesRegex(ValueError,'T8_NONFINITE_POOLED_HELDOUT_ERROR'):
            wm.pooled_heldout_errors(p,y,tr)

    def test_nonfinite_and_bad_shapes_refused(self):
        p=np.zeros((1,3))
        y=np.zeros((1,3))
        tr=np.zeros((2,3))
        for bad in (np.array([[np.nan,0.,0.]]),np.zeros((1,2))):
            with self.assertRaisesRegex(ValueError,'T8_INVALID_POOLED_HELDOUT_INPUT'):
                wm.pooled_heldout_errors(bad,y,tr)


if __name__=='__main__':
    unittest.main()
