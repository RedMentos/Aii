"""Synthetic CPU-only master-vs-adapter retention probe tests; not native proof."""
import unittest
import torch
from v13.body_jepa import anchor_retention_kl

class FixedBody(torch.nn.Module):
    def __init__(self, logits):
        super().__init__()
        self.logits = logits
    def forward(self, input_ids):
        return type('Output', (), {'logits': self.logits})()

class AnchorRetentionTests(unittest.TestCase):
    def test_identical_logits_have_zero_kl(self):
        logits=torch.tensor([[[2.,0.],[0.,2.]]])
        base=torch.log_softmax(logits[0],dim=-1)
        result=anchor_retention_kl(torch,FixedBody(logits),[[1,2]],[base])
        self.assertEqual(len(result),1)
        self.assertAlmostEqual(result[0],0.,places=6)

    def test_changed_logits_show_forgetting_signal(self):
        original=torch.tensor([[2.,0.]])
        shifted=torch.tensor([[[0.,2.]]])
        result=anchor_retention_kl(torch,FixedBody(shifted),[[1]],[torch.log_softmax(original,dim=-1)])
        self.assertGreater(result[0],1.)

    def test_invalid_alignment_and_nan_fail_closed(self):
        with self.assertRaises(ValueError):
            anchor_retention_kl(torch,FixedBody(torch.zeros(1,1,2)),[[1]],[])
        with self.assertRaises(ValueError):
            anchor_retention_kl(torch,FixedBody(torch.tensor([[[float('nan'),0.]]])),[[1]],[torch.zeros(1,2)])

if __name__=='__main__':
    unittest.main()
