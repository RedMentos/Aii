"""Exact-context guards with synthetic ports; these are not model quality proofs."""
import math
import threading
import unittest

from v13.common import Limits, Unavailable
from v13.output_adapter_worker import native_context


class SyntheticRunner:
    def __init__(self, prompt='exact production template', count=300, ids=None, truncated=False):
        self.cfg={'answer_tokens':16}
        self.prompt=prompt
        self.count=count
        self.ids=list(range(count)) if ids is None else ids
        self.truncated=truncated
        self.tap_calls=0

    def load(self, *args):
        pass

    def _prompt(self, *args):
        return self.prompt, self.count, self.truncated

    def _json(self, method, path, payload, deadline):
        assert path=='/tokenize' and payload['content']==self.prompt and payload['add_special'] is True
        return {'tokens':self.ids}

    def completion_one(self, payload, *args):
        assert payload['prompt']==self.prompt and payload['n_probs']==65536
        return {'completion_probabilities':[{'top_logprobs':[{'id':i,'logprob':-math.log(65536)} for i in range(65536)]}], 'tokens':[7]}

    def tap(self, prompt, *args, max_tokens):
        assert prompt==self.prompt and max_tokens==512
        self.tap_calls+=1
        vector=[1.]+[0.]*1023
        return {'token_ids':self.ids,'vectors':[vector]*len(self.ids),
                'metrics':{'physical_batch_tokens':512,'whole_sequence_prefill':True}}


class SyntheticPool:
    def __init__(self, baseline=None, tap=None):
        self.baseline=baseline or SyntheticRunner()
        self.tap_runner=tap or SyntheticRunner()
        self.unloads=0

    def get(self, role):
        assert role=='C3_LANGUAGE'
        return self.baseline

    def get_tap(self, role):
        assert role=='C3_LANGUAGE'
        return self.tap_runner

    def unload(self):
        self.unloads+=1


class NativeContextBindingTests(unittest.TestCase):
    def observe(self, pool, tokens=(1,2)):
        return native_context(pool,[{'role':'user','content':'Recorded query'}],threading.Event(),999999999.,tokens)

    def test_full_context_above_old_batch_bound_is_bound_exactly(self):
        pool=SyntheticPool()
        result=self.observe(pool)
        self.assertEqual(len(result['native_prompt_token_ids']),300)
        self.assertEqual(len(result['feature']),1024)
        self.assertEqual(result['native_baseline']['vocabulary_size'],65536)
        self.assertAlmostEqual(sum(math.exp(v) for v in result['base_log_probabilities']),1.)
        binding=result['native_context_binding']
        self.assertEqual(binding['baseline_prompt_sha256'],binding['tap_prompt_sha256'])
        self.assertTrue(binding['baseline_token_ids_match'])
        self.assertFalse(binding['live_generation_kv_tap'])
        self.assertEqual(pool.unloads,2)

    def test_different_template_rejected_before_feature_collection(self):
        pool=SyntheticPool(tap=SyntheticRunner(prompt='changed template'))
        with self.assertRaisesRegex(Unavailable,'templates differ'):
            self.observe(pool)
        self.assertEqual(pool.tap_runner.tap_calls,0)
        self.assertEqual(pool.unloads,2)

    def test_runtime_feature_count_mismatch_rejected_without_baseline(self):
        pool=SyntheticPool(tap=SyntheticRunner(ids=list(range(299))))
        with self.assertRaisesRegex(Unavailable,'tap token count differs'):
            self.observe(pool,None)
        self.assertEqual(pool.unloads,1)

    def test_same_count_but_different_actual_token_ids_rejected(self):
        ids=list(range(300));ids[-1]=999
        pool=SyntheticPool(tap=SyntheticRunner(ids=ids))
        with self.assertRaisesRegex(Unavailable,'token IDs differ'):
            self.observe(pool)
        self.assertEqual(pool.unloads,2)

    def test_truncated_or_oversize_context_rejected_and_port_unloaded(self):
        for runner in (SyntheticRunner(truncated=True),SyntheticRunner(count=513)):
            with self.subTest(truncated=runner.truncated,count=runner.count):
                pool=SyntheticPool(baseline=runner)
                with self.assertRaises(Limits):
                    self.observe(pool)
                self.assertEqual(pool.tap_runner.tap_calls,0)
                self.assertEqual(pool.unloads,1)


if __name__=='__main__':
    unittest.main()
