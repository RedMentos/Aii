import pathlib,sys,unittest
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
import run178_b2_native_tap as M

class Fake:
    def __init__(self,mode='ok'):self.mode=mode
    def tap(self,text,cancel,deadline,max_tokens):
        seed=sum(text.encode())
        v=np.random.default_rng(seed).normal(size=(10,M.DIM))
        if self.mode=='zero':v[:]=0
        m={'tap_id':M.TAP_ID,'embedding_dim':M.DIM,'CAN_TRAIN_BODY':False,'CAN_LATENT_INJECT':False}
        if self.mode=='wrong':m['tap_id']='lfm2.result_norm.final.v1'
        return {'token_ids':list(range(10)),'vectors':v.tolist(),'metrics':m}

class Tests(unittest.TestCase):
    def test_fixed_texts_and_native_shape_contract(self):
        self.assertEqual(len(M.TEXTS),12);self.assertEqual(len(M.text_sha()),64)
        r=M.probe(Fake());self.assertEqual(r['embedding_dim'],1024)
        self.assertTrue(r['repeat_pass']);self.assertTrue(r['distinct_source_pass'])
        self.assertFalse(r['body_jepa_gate_pass'])
    def test_rejects_lfm2_mislabel(self):
        with self.assertRaisesRegex(ValueError,'native_b2_tap_invalid'):M.one(Fake('wrong'),M.TEXTS[0])
    def test_rejects_zero_vector(self):
        with self.assertRaisesRegex(ValueError,'native_b2_tap_invalid'):M.one(Fake('zero'),M.TEXTS[0])

if __name__=='__main__':unittest.main()
