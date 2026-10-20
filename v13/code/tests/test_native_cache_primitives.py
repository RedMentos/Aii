"""WP-N7 rest (§8.6, G6B): capability manifest + selection policy of the isolated native cache candidate."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import native_cache_primitives as P  # noqa: E402

LOG = """0.02.189.390 I print_info: arch                  = qwen35
0.02.189.396 I print_info: n_layer               = 24
0.02.189.412 I print_info: n_swa                 = 0
0.01.590.321 I print_info: file size   = 526.50 MiB (5.87 BPW)
0.05.059.933 I llama_kv_cache: size =   48.00 MiB (  4096 cells,   6 layers,  1/1 seqs), K (f16):   24.00 MiB, V (f16):   24.00 MiB
0.05.239.227 I llama_memory_recurrent: size =   19.27 MiB (     1 cells,  24 layers,  1 seqs  0 rs_seq), R (f32):    1.27 MiB, S (f32):   18.00 MiB
0.05.538.989 I srv    load_model: prompt cache is enabled, size limit: 8192 MiB
0.05.538.990 I srv    load_model: context checkpoints enabled, max = 32, min spacing = 8192
0.08.490.240 I slot create_check: id  0 | task 0 | created context checkpoint 1 of 32 (pos_min = 300, pos_max = 300, n_tokens = 301, size = 19.266 MiB)
0.08.685.334 I slot   operator(): id  0 | task 4 | restored context checkpoint (pos_min = 300, pos_max = 300, n_tokens = 301, n_past = 301, size = 19.266 MiB)
"""


def exp(usable, cls):
    return {'usable': usable, 'exactness': {'class': cls}, 'summary': 's', 'cost': {}}


class NativeCacheTests(unittest.TestCase):
    def test_parse_log(self):
        f = P.parse_server_log(LOG)
        self.assertEqual((f['arch'], f['n_layer'], f['kv_layers'], f['kv_cells']), ('qwen35', 24, 6, 4096))
        self.assertEqual((f['kv_mib'], f['recurrent_mib'], f['checkpoint_mib']), (48.0, 19.27, 19.266))
        self.assertEqual((f['checkpoints_enabled'], f['checkpoint_min_spacing'], f['prompt_cache_limit_mib']), (32, 8192, 8192))
        self.assertEqual((len(f['checkpoints_created']), f['checkpoints_restored'], f['kv_types']), (1, 1, 'f16'))

    def test_parse_log_missing_facts_stay_none(self):
        f = P.parse_server_log('nothing useful')
        self.assertIsNone(f['arch']); self.assertIsNone(f['kv_mib']); self.assertIsNone(f['checkpoint_mib'])

    def test_exactness_classes(self):
        a = {'tokens': [1, 2, 3], 'logprobs': [-.1, -.2, -.3]}
        self.assertEqual(P.classify_exactness(a, dict(a))['class'], 'EXACT')
        self.assertEqual(P.classify_exactness(a, {'tokens': [1, 2, 3], 'logprobs': [-.12, -.2, -.3]})['class'], 'NUMERIC_CLOSE')
        self.assertEqual(P.classify_exactness(a, {'tokens': [1, 2, 3], 'logprobs': [-.2, -.2, -.3]})['class'], 'DIVERGENT')
        self.assertEqual(P.classify_exactness(a, {'tokens': [1, 2, 3], 'logprobs': [-.2, -.2, -.3]}, tol_close=.2)['class'], 'NUMERIC_CLOSE')
        self.assertEqual(P.classify_exactness(a, {'tokens': [1, 9, 3], 'logprobs': [-.1, -.2, -.3]})['class'], 'DIVERGENT')
        self.assertEqual(P.classify_exactness(None, a)['class'], 'UNMEASURED')

    def manifest(self, **over):
        e = {'prefix': exp(True, 'EXACT'), 'edit_replay': exp(True, 'NUMERIC_CLOSE'), 'switch': exp(True, 'EXACT'),
             'persist': exp(True, 'EXACT'), 'shift': exp(False, 'EXACT'), 'kvquant': exp(True, 'NUMERIC_CLOSE')}
        e.update(over)
        return P.build_manifest('B2_GIST', 'b2.gguf', P.parse_server_log(LOG), e)

    def test_manifest_never_fakes_architecture_primitives(self):
        caps = self.manifest()['capabilities']
        for cap in P.ARCH_ONLY:
            self.assertEqual(caps[cap]['status'], P.ABSENT, cap)
        self.assertEqual(caps['HYBRID_COMPACT_STATE_PLUS_GLOBAL_ATTENTION']['status'], P.EXACT)
        self.assertIn('not sparse', caps['HYBRID_COMPACT_STATE_PLUS_GLOBAL_ATTENTION']['evidence']['global_attention'])
        self.assertEqual(caps['CAN_PARTIAL_ROLLBACK_WITHOUT_CHECKPOINT']['status'], P.UNSUPPORTED)

    def test_manifest_measured_statuses(self):
        caps = self.manifest(switch={'status': 'ERROR'}, persist=exp(True, 'DIVERGENT'))['capabilities']
        self.assertEqual(caps['CAN_PREFIX_CACHE_REUSE']['status'], P.EXACT)
        self.assertEqual(caps['CAN_BOUNDED_CACHE_REPLAY']['status'], P.APPROX)
        self.assertEqual(caps['CAN_HOST_PROMPT_CACHE']['status'], P.UNMEASURED)
        self.assertEqual(caps['CAN_SLOT_PERSIST_RESTORE']['status'], P.UNSUPPORTED)
        self.assertEqual(caps['CAN_KV_SHIFT_REUSE']['status'], P.UNSUPPORTED)
        unstable = self.manifest(prefix=exp(True, 'BASELINE_SPLIT_UNSTABLE'))['capabilities']['CAN_PREFIX_CACHE_REUSE']
        self.assertEqual(unstable['status'], P.UNMEASURED)  # undecidable when the cold baseline itself flips tokens
        self.assertNotIn('CAN_KV_SHIFT_REUSE', [c for c, v in caps.items() if v['status'] in P.USABLE])

    def test_selection_exact_restore_only_takes_exact(self):
        m = self.manifest()
        self.assertEqual(P.select_mechanism(m, 'continue_same_conversation')['mechanism'], 'CAN_PREFIX_CACHE_REUSE')
        r = P.select_mechanism(m, 'edit_earlier_turn', exact_required=True)
        self.assertEqual((r['mechanism'], r['status']), ('FULL_REPREFILL_FROM_EXACT_SOURCE', 'BASELINE'))
        self.assertEqual(P.select_mechanism(m, 'edit_earlier_turn', exact_required=False)['mechanism'], 'CAN_BOUNDED_CACHE_REPLAY')
        for sit in P.SITUATIONS:
            self.assertEqual(P.select_mechanism(m, sit)['fallback'], 'FULL_REPREFILL_FROM_EXACT_SOURCE')

    def test_selection_cost_order_and_quant_never_exact(self):
        m = self.manifest()
        self.assertEqual(P.select_mechanism(m, 'return_to_other_conversation')['mechanism'], 'CAN_HOST_PROMPT_CACHE')
        cost = {'CAN_HOST_PROMPT_CACHE': 80., 'CAN_SLOT_PERSIST_RESTORE': 5.}
        self.assertEqual(P.select_mechanism(m, 'return_to_other_conversation', prefer_cost=cost)['mechanism'], 'CAN_SLOT_PERSIST_RESTORE')
        m['capabilities']['CAN_KV_QUANT_Q8']['status'] = P.EXACT
        self.assertEqual(P.select_mechanism(m, 'shrink_kv_memory', exact_required=True)['status'], 'BASELINE')
        self.assertEqual(P.select_mechanism(m, 'shrink_kv_memory', exact_required=False)['mechanism'], 'CAN_KV_QUANT_Q8')
        with self.assertRaises(ValueError):
            P.select_mechanism(m, 'teleport')

    def test_runner_flags_bounded_by_budget(self):
        m = self.manifest()
        r = P.runner_flags(m, 128)  # 19.3 MiB checkpoints: half of 128 MiB -> 3 checkpoints
        self.assertEqual(r['ctx_checkpoints'], 3)
        self.assertLessEqual(r['worst_case_extra_mib'], 128)
        self.assertEqual(r['flags'][:2], ['--cache-ram', str(r['cache_ram_mib'])])
        self.assertEqual(P.runner_flags(m, 30)['ctx_checkpoints'], 0)  # one would fit, below the minimum of two -> none
        self.assertIn('--checkpoint-min-step', P.runner_flags(m, 256, checkpoint_spacing=256)['flags'])


if __name__ == '__main__':
    unittest.main()
