"""QA: cached anchor retention KL must not change dropout or mixed module modes."""
import unittest
import torch
from v13.body_jepa import anchor_retention_kl


class CachedAnchorRetentionTests(unittest.TestCase):
    def setUp(self):
        class Tiny(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.emb=torch.nn.Embedding(8,5)
                self.drop=torch.nn.Dropout(.8)
                self.proj=torch.nn.Linear(5,8)
            def forward(self,input_ids):
                return type('Out',(),{'logits':self.proj(self.drop(self.emb(input_ids)))})()

        torch.manual_seed(3)
        self.model=Tiny().train()
        self.model.emb.eval()  # preserve mixed child mode, not just root.training
        self.flags=[m.training for m in self.model.modules()]
        with torch.no_grad():
            self.model.eval()
            self.ref=torch.log_softmax(
                self.model(input_ids=torch.tensor([[1,2]])).logits[0].float(),dim=-1)
            self.model.train()
            self.model.emb.eval()

    def flags_now(self):
        return [m.training for m in self.model.modules()]

    def test_dropout_stable_zero_kl(self):
        values=[anchor_retention_kl(torch,self.model,[[1,2]],[self.ref])[0] for _ in range(4)]
        self.assertTrue(all(abs(v)<1e-6 for v in values),values)
        self.assertEqual(self.flags_now(),self.flags)

    def test_forward_error_restores_modes(self):
        with self.assertRaises(IndexError):
            anchor_retention_kl(torch,self.model,[[99]],[self.ref])
        self.assertEqual(self.flags_now(),self.flags)

    def test_invalid_second_anchor_restores_modes(self):
        with self.assertRaises(ValueError):
            anchor_retention_kl(torch,self.model,[[1,2],[]],[self.ref,self.ref])
        self.assertEqual(self.flags_now(),self.flags)

    def test_nonzero_adapter_like_drift(self):
        with torch.no_grad():
            self.model.proj.weight.add_(.1)
        value=anchor_retention_kl(torch,self.model,[[1,2]],[self.ref])[0]
        self.assertGreater(value,0)
        self.assertEqual(self.flags_now(),self.flags)


if __name__=='__main__':
    unittest.main()
