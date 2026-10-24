"""Run37: executable regression for the full Run28-derived world_model candidate.

Requires sibling scripts/world_model.py; not the lightweight local test seam.
"""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
import numpy as np

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
pkg=types.ModuleType('run37_isolated');pkg.__path__=[str(SCRIPTS)];sys.modules[pkg.__name__]=pkg
common=types.ModuleType('run37_isolated.common');common.now=lambda:0.;sys.modules[common.__name__]=common
spec=importlib.util.spec_from_file_location('run37_isolated.world_model',SCRIPTS/'world_model.py')
W=importlib.util.module_from_spec(spec);sys.modules[spec.name]=W;spec.loader.exec_module(W)

def state(log_duration=.5,success=.8,log_chars=.3):
    mat=np.zeros((W.ENSEMBLE,9,3));mat[:,0,:]=[log_duration,success,log_chars]
    return {'status':'FITTED','forward':mat.tolist(),
            'states':{a:[[0.,0.,0.,0.]]*20 for a in W.ACTIONS}}

class WorldDomainCandidate(unittest.TestCase):
    def cf(self,st):return W.counterfactual(None,[0.,0.,0.,0.],'simple',st)
    def test_negative_duration_is_uncertain(self):
        out=self.cf(state(log_duration=-.3))
        self.assertEqual(out['reason'],'IMPOSSIBLE_PREDICTED_OUTCOME')
        self.assertEqual(out['confidence'],0.)
        self.assertIsNone(out['prediction'])
    def test_success_above_one_is_uncertain(self):
        self.assertEqual(self.cf(state(success=1.2))['reason'],'IMPOSSIBLE_PREDICTED_OUTCOME')
    def test_success_below_zero_is_uncertain(self):
        self.assertEqual(self.cf(state(success=-.1))['reason'],'IMPOSSIBLE_PREDICTED_OUTCOME')
    def test_negative_log_chars_is_uncertain(self):
        self.assertEqual(self.cf(state(log_chars=-.2))['reason'],'IMPOSSIBLE_PREDICTED_OUTCOME')
    def test_valid_supported_prediction_preserved(self):
        out=self.cf(state());self.assertEqual(out['label'],'SIMULATION_SUPPORTED')
        self.assertGreater(out['prediction']['duration_s'],0.)
        self.assertEqual(out['authority'],'HYPOTHESIS')
    def test_zero_boundary_allowed(self):
        out=self.cf(state(log_duration=0.,success=1.,log_chars=0.))
        self.assertEqual(out['label'],'SIMULATION_SUPPORTED')
        self.assertEqual(out['prediction']['duration_s'],0.)
    def test_nan_weights_still_uncertain(self):
        st=state();st['forward'][0][0][0]=float('nan')
        self.assertEqual(self.cf(st)['reason'],'INVALID_MODEL_STATE')
    def test_no_model_still_uncertain(self):
        class EmptyStore:
            def state(self,key,default):return (None,None)
        self.assertEqual(W.counterfactual(EmptyStore(),[0.]*4,'simple',None)['reason'],'NO_WORLD_MODEL')

if __name__=='__main__':unittest.main()
