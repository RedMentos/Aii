import json
from pathlib import Path
import sys
import tempfile
import unittest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import body_jepa_micro as B

class MicroJEPA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result,cls.learner,cls.holdout=B.cohort()
    def test_objective_adapter_complete(self):
        self.assertEqual(len(B.OBJECTIVE.__dataclass_fields__),10)
        self.assertEqual(B.OBJECTIVE.stop_gradient_policy,'DETACH_TARGET')
        self.assertEqual(B.OBJECTIVE.update_scope,('STUDENT_PROJECTOR','PREDICTOR'))
    def test_pre_registered_synthetic_threshold(self):
        self.assertTrue(self.result['synthetic_criterion_pass'],self.result)
    def test_gradient_and_ema_scope(self):
        self.assertTrue(self.result['target_gradients_absent'])
        self.assertGreater(self.result['student_delta'],0)
        self.assertGreater(self.result['predictor_delta'],0)
        self.assertGreater(self.result['ema_delta'],0)
    def test_credit_map_local_only(self):
        self.assertEqual(B.credit_map(2.,.5)['credit'],.5)
        self.assertEqual(B.credit_map(1.,0.)['credit'],0.)
        with self.assertRaises(ValueError):B.credit_map(1.,1.,'B2_GIST_PRODUCTION')
        with self.assertRaises(ValueError):B.credit_map(float('nan'),1.)
    def test_deterministic_replay(self):
        second,_,_=B.cohort()
        self.assertEqual(self.result,second)
    def test_zero_eligibility_no_update(self):
        torch.manual_seed(5);m=B.MicroLearner();x,a,y=B.pairs()
        old=[p.detach().clone() for p in m.parameters()]
        self.assertEqual(m.step(x[:8],a[:8],y[:8],torch.zeros(8)),0.)
        self.assertTrue(all(torch.equal(before,after) for before,after in zip(old,m.parameters())))
    def test_invalid_eligibility_reject(self):
        m=B.MicroLearner();x,a,y=B.pairs()
        with self.assertRaises(ValueError):m.step(x[:8],a[:8],y[:8],torch.ones(7))
        with self.assertRaises(ValueError):m.step(x[:8],a[:8],y[:8],torch.full((8,),float('nan')))
    def test_checkpoint_roundtrip_and_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            B.save(self.learner,d)
            restored=B.load(d)
            self.assertAlmostEqual(restored.mse(*self.holdout),self.learner.mse(*self.holdout),places=6)
            with self.assertRaises(FileExistsError):B.save(self.learner,d)
            p=Path(d)/'weights.npz';raw=bytearray(p.read_bytes());raw[-3]^=0x80;p.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'hash'):B.load(d)
    def test_no_production_or_age_authority(self):
        with self.assertRaises(PermissionError):B.MicroLearner('ACTIVE')
        self.assertFalse(self.result['body_jepa_gate_pass'])
        self.assertEqual(self.result['jepa_weight_production'],0)
        self.assertEqual(self.result['authority'],'SYNTHETIC_SANDBOX_NO_AGE_ACTION')

if __name__=='__main__':unittest.main()
