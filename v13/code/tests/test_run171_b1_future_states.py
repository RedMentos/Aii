import copy
import pathlib
import sys
import unittest
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import run171_b1_future_states as M

class FakeTap:
    def __init__(self):self.calls=[]
    def tap(self,text,cancel,deadline,max_tokens):
        self.calls.append(text)
        seed=abs(hash(text)) % (2**32)
        v=np.random.default_rng(seed).normal(size=(27,M.DIM)).tolist()
        return {'token_ids':list(range(27)),'vectors':v,'metrics':{
            'tap_id':'lfm2.result_norm.final.v1','CAN_TRAIN_BODY':False,'CAN_LATENT_INJECT':False}}

class Run171Tests(unittest.TestCase):
    def test_fixed_source_hash_and_pairs(self):
        self.assertEqual(len(M.TEXTS),16)
        self.assertEqual(len(M.text_sha()),64)
        rows=M.collect(FakeTap())
        x,y,g=M.temporal_pairs(rows)
        self.assertEqual(x.shape[1],2048)
        self.assertEqual(len(set(g)),16)
        self.assertEqual(len(x),len(y))
        self.assertEqual(len(x),16*8)
    def test_training_receives_group_bound_pairs_only(self):
        rows=M.collect(FakeTap())
        calls=[]
        def train(inp,out):
            calls.append(inp)
            return {'commit_eligible':False,'held_out_pairs':32}
        r=M.run_shadow(rows,train,{'seed':M.SEED},'/tmp/unused')
        self.assertEqual(len(calls),1)
        self.assertEqual(len(set(calls[0]['source_groups'])),16)
        self.assertFalse(r['body_jepa_gate_pass'])
        self.assertEqual(r['gates']['STEP2'],'UTILITY_FAIL')
    def test_rejects_unauthorized_native_tap(self):
        class Wrong(FakeTap):
            def tap(self,*args,**kwargs):
                v=super().tap(*args,**kwargs);v['metrics']['CAN_TRAIN_BODY']=True;return v
        with self.assertRaisesRegex(ValueError,'invalid_native_tap'):M.collect(Wrong())
    def test_rejects_nonfinite_vector(self):
        rows=M.collect(FakeTap());rows[0]['vectors'][0,0]=np.nan
        with self.assertRaisesRegex(ValueError,'run171_vectors'):M.temporal_pairs(rows)
    def test_rejects_duplicate_group(self):
        rows=M.collect(FakeTap());rows[1]['group']=0
        with self.assertRaisesRegex(ValueError,'run171_group_order'):M.temporal_pairs(rows)

if __name__=='__main__':unittest.main()
