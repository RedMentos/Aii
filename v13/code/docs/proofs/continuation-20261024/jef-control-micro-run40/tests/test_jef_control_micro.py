from pathlib import Path
import sys
import unittest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import jef_control_micro as J

class JEFControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.metrics,cls.model=J.cohort()
    def test_preregistered_threshold(self):self.assertTrue(self.metrics['synthetic_criterion_pass'],self.metrics)
    def test_four_heads_update(self):self.assertTrue(all(v>0 for v in self.metrics['head_deltas'].values()))
    def test_objective_contract(self):
        self.assertEqual(len(J.OBJECTIVE.__dataclass_fields__),10)
        self.assertEqual(len(J.OBJECTIVE.loss_terms),4)
    def test_deterministic_replay(self):self.assertEqual(self.metrics,J.cohort()[0])
    def test_missing_source_hard_report_gate(self):
        for exact in (0,1):
            p=self.model.propose([exact,1,0,0,0,1]);self.assertFalse(p['report_allowed'])
            self.assertFalse(p['action_authority'])
    def test_conflict_hard_report_gate(self):
        p=self.model.propose([1,1,1,0,1,1]);self.assertFalse(p['report_allowed'])
    def test_pressure_hard_report_gate(self):
        p=self.model.propose([0,1,0,1,1,0]);self.assertFalse(p['report_allowed'])
    def test_eligibility_zero_no_update(self):
        torch.manual_seed(3);m=J.Control();x,y=J.dataset()
        old=[p.detach().clone() for p in m.parameters()]
        self.assertEqual(m.step(x[:16],tuple(v[:16] for v in y),torch.zeros(16)),0.)
        self.assertTrue(all(torch.equal(a,b) for a,b in zip(old,m.parameters())))
    def test_invalid_eligibility_and_no_authority(self):
        m=J.Control();x,y=J.dataset()
        with self.assertRaises(ValueError):m.step(x[:8],tuple(v[:8] for v in y),torch.ones(7))
        with self.assertRaises(PermissionError):J.Control('ACTIVE')
        self.assertFalse(self.metrics['native_jef_gate_pass'])

if __name__=='__main__':unittest.main()
