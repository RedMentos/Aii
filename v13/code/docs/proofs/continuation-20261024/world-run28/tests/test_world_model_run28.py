"""Run28 adversarial world-model input/state checks, no live model calls."""
import json
import math
from pathlib import Path
import importlib.util
import sys
import types
import unittest

# Load the isolated candidate without importing or modifying production v13.
SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
pkg=types.ModuleType('run28_isolated')
pkg.__path__=[str(SCRIPTS)]
sys.modules[pkg.__name__]=pkg
common=types.ModuleType('run28_isolated.common')
common.now=lambda:0.
sys.modules[common.__name__]=common
spec=importlib.util.spec_from_file_location('run28_isolated.world_model',SCRIPTS/'world_model.py')
W=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=W
spec.loader.exec_module(W)

class FakeStore:
    def __init__(self, rows=None, packet=None):
        self._rows=rows or [];self.packet=packet;self.saved={}
    def rows(self,sql,args):return self._rows
    def one(self,sql,args):return {'payload':json.dumps(self.packet)} if self.packet is not None else None
    def set_state(self,key,value):self.saved[key]=value
    def state(self,key,default):return (self.saved.get(key,default),None)
    def log(self,*args):pass

def row(duration=1.0,input_chars=100,characters=40,latent=None,created=1000):
    return {'id':'a','event_id':'e','status':'FINAL',
            'expected':json.dumps({'forecast':{'input_chars':input_chars,'resource_state':'NORMAL',
                                               'learned_latent_prediction':{'latent':latent}}}),
            'outcome':json.dumps({'action_duration_s':duration,'characters':characters}),
            'created':created}

class Run28World(unittest.TestCase):
    def test_negative_duration_does_not_crash_training_extraction(self):
        self.assertEqual(W.transitions(FakeStore([row(duration=-2)],{'route_hint':'detail'})),[])
    def test_nonfinite_input_does_not_enter_training(self):
        self.assertEqual(W.transitions(FakeStore([row(input_chars=float('nan'))],{'route_hint':'detail'})),[])
    def test_negative_output_characters_does_not_crash(self):
        self.assertEqual(W.transitions(FakeStore([row(characters=-20)],{'route_hint':'detail'})),[])
    def test_malformed_json_does_not_crash_extraction(self):
        r=row();r['expected']='{bad json'
        self.assertEqual(W.transitions(FakeStore([r],{'route_hint':'detail'})),[])
    def test_invalid_latent_does_not_poison_align(self):
        t=W.transitions(FakeStore([row(latent=[1,float('nan')])],{'route_hint':'detail'}))
        self.assertEqual(len(t),1)
        self.assertIsNone(t[0]['latent'])
    def test_nan_counterfactual_fails_closed(self):
        s={'status':'FITTED','forward':[[[0.]*3 for _ in range(9)] for _ in range(5)],
           'states':{'detail':[[0.,0.,0.,0.]]*12}}
        r=W.counterfactual(FakeStore(),[float('nan'),0.,0.,0.],'detail',s)
        self.assertEqual(r['label'],'SIMULATION_UNCERTAIN')
        self.assertEqual(r['confidence'],0.)
        self.assertIsNone(r['prediction'])
    def test_nonfinite_weights_fail_closed(self):
        s={'status':'FITTED','forward':[[[float('nan')]*3 for _ in range(9)] for _ in range(5)],
           'states':{'detail':[[0.,0.,0.,0.]]*12}}
        r=W.counterfactual(FakeStore(),[0.,0.,0.,0.],'detail',s)
        self.assertEqual(r['label'],'SIMULATION_UNCERTAIN')
        self.assertEqual(r['confidence'],0.)
        self.assertIsNone(r['prediction'])

    def test_for_event_invalid_state_fails_closed(self):
        store=FakeStore()
        store.one=lambda sql,args:{'expected':'{"forecast":{"input_chars":-10}}','created':1000}
        from unittest import mock
        with mock.patch.object(W,'counterfactual',side_effect=AssertionError('invalid state reached predictor')):
            r=W.for_event(store,'event','detail')
        self.assertEqual(r['label'],'SIMULATION_UNCERTAIN')
        self.assertEqual(r['reason'],'INVALID_OBSERVED_STATE')
        self.assertEqual(r['confidence'],0.)

    def test_finite_valid_transitions_and_fit_still_work(self):
        data=[]
        for i in range(80):
            a=W.ACTIONS[i%4]
            s=W.state_vec(50+i,'NORMAL',i%24)
            y=[math.log1p(1.+i%4),1.,math.log1p(20+i)/8]
            data.append({'action_id':str(i),'s':s,'a':a,'y':y,'latent':None})
        store=FakeStore()
        from unittest import mock
        with mock.patch.object(W,'transitions',return_value=data):
            st=W.fit(store)
        self.assertEqual(st['status'],'FITTED')
        r=W.counterfactual(store,W.state_vec(65,'NORMAL',12),'detail')
        self.assertEqual(r['authority'],'HYPOTHESIS')
        self.assertTrue(math.isfinite(r['confidence']))
        self.assertIsNotNone(r['prediction'])

    def test_malformed_selection_skipped(self):
        store=FakeStore([row()],{'route_hint':'detail'})
        store.one=lambda sql,args:{'payload':'{invalid'}
        self.assertEqual(W.transitions(store),[])

if __name__=='__main__':unittest.main()
