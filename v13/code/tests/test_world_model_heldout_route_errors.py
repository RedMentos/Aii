"""T8 per-route heldout MAE and evidence scope, software-only."""
import unittest
import numpy as np
from v13.world_model import ACTIONS, TARGETS, heldout_route_errors


class RouteErrors(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {'a':'simple','y':[0.,0.,0.]},
            {'a':'gist','y':[1.,1.,1.]},
            {'a':'simple','y':[2.,2.,2.]},
            {'a':'both','y':[3.,3.,3.]},
        ]

    def test_unseen_train_route_is_disclosed_not_claimed_supported(self):
        out=heldout_route_errors(self.rows,[0,1],[2,3],
                                  [[1.,1.,1.],[2.,2.,2.]],
                                  [[0.,0.,0.],[0.,0.,0.]])
        self.assertEqual(out['simple']['status'],'MEASURED_TRAIN_SUPPORTED')
        self.assertEqual(out['both']['status'],'MEASURED_UNSEEN_TRAIN_ACTION')
        self.assertEqual(out['both']['n'],1)
        self.assertEqual(out['both']['mae'],dict.fromkeys(TARGETS,1.0))
        self.assertEqual(out['both']['baseline_mae'],dict.fromkeys(TARGETS,3.0))
        self.assertEqual(out['gist']['status'],'UNMEASURED')
        self.assertIsNone(out['gist']['mae'])
        self.assertEqual(tuple(out),ACTIONS)

    def test_prediction_shape_and_nonfinite_rejected(self):
        for pred in ([[1.,1.,1.]], [[float('nan')]*3]*2, [[float('inf')]*3]*2):
            with self.subTest(pred=pred),self.assertRaises(ValueError):
                heldout_route_errors(self.rows,[0,1],[2,3],pred,np.zeros((2,3)))
        with self.assertRaises(ValueError):
            heldout_route_errors(self.rows,[0,1],[2,3],np.zeros((2,3)),np.zeros((3,3)))

    def test_invalid_split_and_target_rejected(self):
        with self.assertRaises(ValueError):
            heldout_route_errors(self.rows,[0,1],[1,3],np.zeros((2,3)),np.zeros((2,3)))
        bad=list(self.rows)
        bad[3]={'a':'both','y':[float('nan'),0.,0.]}
        with self.assertRaises(ValueError):
            heldout_route_errors(bad,[0,1],[2,3],np.zeros((2,3)),np.zeros((2,3)))


if __name__=='__main__':
    unittest.main()
