"""Run46 synthetic architecture/ablation invariants; not native V13 proof."""
import sys
import unittest
from pathlib import Path
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import key_binding as R


class BindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.rows=R.data_builder()(R.SEED,32,'test')

    def test_staged_examples_have_consistent_targets(self):
        for keys,values,q,t in self.rows:
            self.assertEqual(values[keys.index(q)],t)

    def test_query_target_not_encoded_as_extra_input(self):
        keys,values,query,target=R.tensorize(self.rows)
        self.assertEqual(tuple(keys.shape),(32,3))
        self.assertEqual(tuple(values.shape),(32,3))
        self.assertEqual(tuple(query.shape),(32,))
        self.assertEqual(tuple(target.shape),(32,))

    def test_model_trainable_not_hardcoded_lookup(self):
        m=R.KeyBinding()
        self.assertGreater(sum(p.numel() for p in m.parameters()),1000)
        self.assertTrue(all(p.requires_grad for p in m.parameters()))

    def test_output_and_attention_modes_shapes(self):
        m=R.KeyBinding();keys,values,query,_=R.tensorize(self.rows)
        for kw in ({},{'uniform':True},{'no_context':True}):
            self.assertEqual(tuple(m(keys,values,query,**kw).shape),(32,8))

    def test_no_context_logits_independent_of_mappings(self):
        m=R.KeyBinding();keys,values,query,_=R.tensorize(self.rows)
        a=m(keys,values,query,no_context=True)
        b=m(keys.flip(1),values.flip(1),query,no_context=True)
        self.assertTrue(torch.allclose(a,b))

    def test_uniform_attention_independent_of_query(self):
        m=R.KeyBinding();keys,values,query,_=R.tensorize(self.rows)
        a=m(keys,values,query,uniform=True)
        b=m(keys,values,(query+1)%8,uniform=True)
        self.assertTrue(torch.allclose(a,b))

    def test_seed_constants_preserved(self):
        self.assertEqual((R.SEED,R.HELDOUT,R.STEPS,R.LR,R.BATCH),(20261024,20261025,300,.005,64))


if __name__=='__main__':unittest.main()
