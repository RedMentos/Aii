from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import world_counterfactual_domain as W

def state(log_duration=.5,success=.8,log_chars=.3):
    mat=np.zeros((W.ENSEMBLE,9,3))
    mat[:,0,:]=[log_duration,success,log_chars]
    return {'status':'FITTED','forward':mat.tolist(),
            'states':{a:[[0.,0.,0.,0.]]*20 for a in W.ACTIONS}}

class OutcomeDomain(unittest.TestCase):
    def test_original_negative_duration_supported_red(self):
        out=W.counterfactual([0.,0.,0.,0.],'simple',state(log_duration=-.3))
        self.assertEqual(out['label'],'SIMULATION_SUPPORTED')
        self.assertLess(out['prediction']['duration_s'],0)
    def test_guard_negative_duration_uncertain(self):
        out=W.counterfactual([0.,0.,0.,0.],'simple',state(log_duration=-.3),True)
        self.assertEqual(out['label'],'SIMULATION_UNCERTAIN')
        self.assertEqual(out['reason'],'IMPOSSIBLE_PREDICTED_OUTCOME')
        self.assertEqual(out['confidence'],0)
        self.assertIsNone(out['prediction'])
    def test_guard_success_above_one_uncertain(self):
        self.assertEqual(W.counterfactual([0]*4,'simple',state(success=1.2),True)['reason'],
                         'IMPOSSIBLE_PREDICTED_OUTCOME')
    def test_guard_success_below_zero_uncertain(self):
        self.assertEqual(W.counterfactual([0]*4,'simple',state(success=-.1),True)['reason'],
                         'IMPOSSIBLE_PREDICTED_OUTCOME')
    def test_guard_negative_log_chars_uncertain(self):
        self.assertEqual(W.counterfactual([0]*4,'simple',state(log_chars=-.2),True)['reason'],
                         'IMPOSSIBLE_PREDICTED_OUTCOME')
    def test_valid_prediction_unchanged(self):
        before=W.counterfactual([0]*4,'simple',state())
        after=W.counterfactual([0]*4,'simple',state(),True)
        self.assertEqual(before,after)
        self.assertEqual(after['label'],'SIMULATION_SUPPORTED')
    def test_bounds_zero_and_one_allowed(self):
        out=W.counterfactual([0]*4,'simple',state(log_duration=0,success=1,log_chars=0),True)
        self.assertEqual(out['label'],'SIMULATION_SUPPORTED')
        self.assertEqual(out['prediction']['duration_s'],0)
    def test_invalid_action_rejected(self):
        with self.assertRaises(ValueError):W.counterfactual([0]*4,'wrong',state(),True)
    def test_nonfinite_input_already_rejected(self):
        self.assertEqual(W.counterfactual([float('nan')]*4,'simple',state(),True)['reason'],'INVALID_STATE')
    def test_no_model_stays_uncertain(self):
        self.assertEqual(W.counterfactual([0]*4,'simple',None,True)['reason'],'NO_WORLD_MODEL')

if __name__=='__main__':unittest.main()
