"""T8 held-out route errors: arithmetic overflow and integer wrap controls."""
import unittest
import numpy as np
from v13.world_model import heldout_route_errors


class FiniteHeldoutErrors(unittest.TestCase):
    def setUp(self):
        self.rows=[{'a':'simple','y':[0.,0.,0.]},{'a':'gist','y':[0.,0.,0.]}]

    def test_large_opposite_finite_inputs_cannot_emit_infinity(self):
        huge=np.finfo(float).max
        with self.assertRaisesRegex(ValueError,'T8_NONFINITE_HELDOUT_ERROR'):
            heldout_route_errors(self.rows,[0],[1],
                                 [[huge,huge,huge]],[[-huge,-huge,-huge]])

    def test_integer_subtraction_cannot_wrap_to_small_error(self):
        # Without float conversion, int64 max - int64 min wraps to -1.
        self.rows[1]['y']=[float(-(2**63)),0.,0.]
        pred=np.array([[2**63-1,0,0]],dtype=np.int64)
        baseline=np.zeros((1,3),dtype=np.int64)
        out=heldout_route_errors(self.rows,[0],[1],pred,baseline)
        self.assertGreater(out['gist']['mae']['log_duration'],1e18)

    def test_normal_values_remain_unchanged(self):
        self.rows[1]['y']=[2.,2.,2.]
        out=heldout_route_errors(self.rows,[0],[1],[[1.,1.,1.]],[[0.,0.,0.]])
        self.assertEqual(out['gist']['mae'],{'log_duration':1.,'success':1.,'log_chars':1.})
        self.assertEqual(out['gist']['status'],'MEASURED_UNSEEN_TRAIN_ACTION')


if __name__=='__main__':
    unittest.main()
