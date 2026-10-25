import pathlib,sys,tempfile,unittest
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
import run174_topic_holdout as M

class FakeTap:
    def tap(self,text,cancel,deadline,max_tokens):
        v=np.ones((24,2048),dtype=float)
        for j in range(24):v[j,j]=2
        return {'token_ids':list(range(24)),'vectors':v.tolist(),
                'metrics':{'tap_id':'lfm2.result_norm.final.v1','CAN_TRAIN_BODY':False,'CAN_LATENT_INJECT':False}}

class Run174Tests(unittest.TestCase):
    def test_precommitted_topic_partition_and_pairing(self):
        self.assertEqual(len(M.TOPICS),20);self.assertEqual(len(M.TEXTS),120)
        rows=M.collect(FakeTap());x,y,g=M.pairs(rows)
        self.assertEqual(x.shape[1],2048)
        self.assertEqual(len(set(g)),20)
        self.assertEqual(len(x),120*7)
    def test_shadow_no_fake_gain_on_identity_baseline(self):
        rows=M.collect(FakeTap());calls=[]
        def fake_train(inp,out):
            calls.append(inp)
            p=np.zeros((2048,16));p[:16,:]=np.eye(16)
            np.savez(pathlib.Path(out)/'candidate.npz',projector=p,predictor=np.eye(16),target=p,anchor=p)
            return {'commit_eligible':True}
        with tempfile.TemporaryDirectory() as folder:
            result=M.run_shadow(rows,fake_train,lambda x:np.asarray(x,dtype=float),folder,{'seed':M.SEED})
        self.assertEqual(len(calls),1)
        self.assertEqual(len(set(calls[0]['source_groups'])),17)
        self.assertEqual(result['independent_test']['test_topics'],[17,18,19])
        self.assertFalse(result['fixed_target_control_pass'])
        self.assertFalse(result['shadow_commit_eligible'])
        self.assertFalse(result['body_jepa_gate_pass'])
    def test_rejects_swapped_source_topic(self):
        rows=M.collect(FakeTap());rows[6]['topic']=0
        with self.assertRaisesRegex(ValueError,'source_order'):M.pairs(rows)
    def test_rejects_unauthorized_tap(self):
        class Wrong(FakeTap):
            def tap(self,*args,**kwargs):
                d=super().tap(*args,**kwargs);d['metrics']['CAN_TRAIN_BODY']=True;return d
        with self.assertRaisesRegex(ValueError,'native_tap_invalid'):M.collect(Wrong())

if __name__=='__main__':unittest.main()
