"""WP-N11 isolated candidate: router-stability gate (B3-H6), pre-router monitor (§16.2.1), §91 order. Synthetic arrays, no model."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import moe_router_monitor as M  # noqa: E402

T, D, E, K = 64, 16, 8, 2


def router(seed=0):
    return np.random.default_rng(seed).normal(size=(E, D))


def capture(x, w, layers=(0, 1), residual_scale=1.0):
    return M.Capture({i: M.LayerCapture(x @ w.T, x, x * residual_scale) for i in layers}, K)


class PrimitiveTests(unittest.TestCase):
    def test_identical_captures_have_zero_shift(self):
        rng = np.random.default_rng(1)
        x, w = rng.normal(size=(T, D)), router()
        c = capture(x, w)
        agg = M.compare(c, c)['aggregate']
        for m in ('router_kl', 'topk_flip_rate', 'router_input_norm_shift', 'residual_norm_shift', 'shared_drift'):
            self.assertAlmostEqual(agg[m], 0.0, places=9, msg=m)

    def test_flip_rate_counts_changed_slots_not_order(self):
        a = np.array([[5., 4., 0., 0.], [5., 4., 0., 0.]])
        b = np.array([[4., 5., 0., 0.], [5., 0., 4.5, 0.]])
        self.assertAlmostEqual(M.topk_flip_rate(a, b, 2), 0.25)

    def test_collision_is_one_for_constant_routing_and_low_for_random(self):
        const = np.tile(np.arange(E, dtype=float), (T, 1))
        self.assertAlmostEqual(M.route_collision(const, K), 1.0)
        rnd = np.random.default_rng(2).normal(size=(4000, E))
        self.assertLess(M.route_collision(rnd, K), 0.06)

    def test_usage_histogram_sums_to_one(self):
        u = M.expert_usage(np.random.default_rng(3).normal(size=(T, E)), K)
        self.assertAlmostEqual(u.sum(), 1.0)

    def test_npz_round_trip(self):
        rng = np.random.default_rng(4)
        c = capture(rng.normal(size=(T, D)), router())
        c.meta['model'] = 'synthetic'
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'c.npz'
            c.to_npz(p)
            r = M.Capture.from_npz(p)
        self.assertEqual(r.meta['model'], 'synthetic')
        self.assertAlmostEqual(M.compare(c, r)['aggregate']['router_kl'], 0.0, places=6)

    def test_native_tap_reader(self):
        rng = np.random.default_rng(6)
        n, il = 5, 3
        logits, rin, an = rng.normal(size=(n, E)), rng.normal(size=(n, D)), rng.normal(size=(n, D))
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for name, a in ((f'ffn_moe_logits-{il}', logits), (f'ffn_norm-{il}', rin), (f'attn_norm-{il}', an)):
                a.astype(np.float32).tofile(d / f'0.{name}.f32')
            (d / 'index.jsonl').write_text('{"row":0,"n_tokens":5,"tensors":{"ffn_moe_logits-3":%d,"ffn_norm-3":%d,"attn_norm-3":%d}}\n' % (E, D, D))
            c = M.load_native_tap(d, 0, K)
        self.assertEqual(list(c.layers), [il])
        self.assertTrue(np.allclose(c.layers[il].logits, logits, atol=1e-6))
        self.assertTrue(np.allclose(c.layers[il].residual, an, atol=1e-6))

    def test_rejects_misaligned_tokens(self):
        rng = np.random.default_rng(5)
        a = capture(rng.normal(size=(T, D)), router())
        b = capture(rng.normal(size=(T + 1, D)), router())
        with self.assertRaises(ValueError):
            M.compare(a, b)
        self.assertEqual(M.compare(a.tail(10), b.tail(10))['layers'], [0, 1])


class GateTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(7)
        self.w = router(7)
        self.x = rng.normal(size=(T, D))
        self.base = capture(self.x, self.w)
        noise = [capture(self.x + 0.01 * rng.normal(size=(T, D)), self.w) for _ in range(12)]
        self.cal = M.calibrate([M.compare(self.base, n)['aggregate'] for n in noise], source='synthetic noise')

    def test_uncalibrated_never_passes(self):
        few = M.calibrate([{'router_kl': 0.0}] * 3)
        self.assertEqual(few['status'], 'UNCALIBRATED')
        self.assertEqual(M.router_stability_gate({'router_kl': 0.0}, few)['verdict'], 'UNCALIBRATED')

    def test_baseline_like_message_passes_large_message_fails(self):
        rng = np.random.default_rng(8)
        small = capture(self.x + 0.005 * rng.normal(size=(T, D)), self.w)
        g = M.router_stability_gate(M.compare(self.base, small)['aggregate'], self.cal)
        self.assertEqual(g['verdict'], 'PASS', g['reasons'])
        m = rng.normal(size=D)
        big = capture(self.x + 2.0 * m, self.w)
        g = M.router_stability_gate(M.compare(self.base, big)['aggregate'], self.cal)
        self.assertEqual(g['verdict'], 'FAIL')
        self.assertTrue(any('router_kl' in r for r in g['reasons']))

    def test_missing_utility_is_not_gain(self):
        agg = M.compare(self.base, self.base)['aggregate']
        g = M.router_stability_gate(agg, self.cal, min_downstream_utility_gain=0.01)
        self.assertEqual(g['verdict'], 'FAIL')
        g = M.router_stability_gate(agg, self.cal, utility_gain=0.05, min_downstream_utility_gain=0.01,
                                    old_task_loss_delta=0.2, max_old_task_loss_delta=0.1)
        self.assertEqual(g['verdict'], 'FAIL')
        self.assertTrue(any('old-task' in r for r in g['reasons']))


class InterferenceTests(unittest.TestCase):
    def test_counterfactual_separates_input_from_router_change(self):
        rng = np.random.default_rng(9)
        x, w = rng.normal(size=(T, D)), router(9)
        r = M.counterfactual_route_shift(x, x + rng.normal(size=(T, D)), w, w, K)
        self.assertGreater(r['input_kl'], 0.01)
        self.assertAlmostEqual(r['router_kl'], 0.0)
        r = M.counterfactual_route_shift(x, x, w, w + rng.normal(size=w.shape), K)
        self.assertAlmostEqual(r['input_kl'], 0.0)
        self.assertGreater(r['router_kl'], 0.01)

    def test_restoration_attribution_and_repair_rule(self):
        rng = np.random.default_rng(10)
        x, w = rng.normal(size=(T, D)), router(10)
        before = capture(x, w)
        after = capture(x + 0.5 * rng.normal(size=(T, D)), w)
        rep = M.interference_report(before, after, 2.0, 2.6,
                                    restore_losses={'shared': 2.05, 'experts': 2.55, 'router': 2.6})
        self.assertEqual(rep['verdict'], 'PRE_ROUTER_BOTTLENECK')
        self.assertIn('shared', rep['allowed_repair'])
        rep = M.interference_report(before, before, 2.0, 2.6,
                                    restore_losses={'shared': 2.6, 'experts': 2.1})
        self.assertEqual(rep['verdict'], 'EXPERT_OR_ROUTER')
        self.assertEqual(M.interference_report(before, before, 2.0, 1.9)['verdict'], 'NO_FORGETTING')
        self.assertEqual(M.interference_report(before, after, 2.0, 2.6)['verdict'], 'UNATTRIBUTED')


class PhaseTests(unittest.TestCase):
    def test_phase_order(self):
        self.assertTrue(M.phase_allowed('A', {})['allowed'])
        self.assertFalse(M.phase_allowed('B', {})['allowed'])
        ok = {'phase_a_retention_ok': True, 'route_monitor_active': True, 'retention_ok': True}
        self.assertTrue(M.phase_allowed('B', ok)['allowed'])
        self.assertEqual(M.phase_allowed('B', ok)['mode'], 'SHADOW')
        self.assertFalse(M.phase_allowed('C', ok)['allowed'])
        self.assertTrue(M.phase_allowed('C', dict(ok, missed_routing=True))['allowed'])
        self.assertFalse(M.phase_allowed('D', dict(ok, pre_router_bottleneck='EXPERT_OR_ROUTER'))['allowed'])
        self.assertTrue(M.phase_allowed('D', dict(ok, pre_router_bottleneck='PRE_ROUTER_BOTTLENECK'))['allowed'])

    def test_hit_expert_alone_never_commits(self):
        self.assertFalse(M.expert_commit_allowed(True, None, None, False, False)['commit'])
        self.assertFalse(M.expert_commit_allowed(True, 0.3, 'surprise', True, False)['commit'])
        self.assertTrue(M.expert_commit_allowed(True, 0.3, 'surprise', True, True)['commit'])


if __name__ == '__main__':
    unittest.main()
