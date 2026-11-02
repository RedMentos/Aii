import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import numpy as np
import bp8_real_age as R

POOL = [('q%d' % i, 'Answer %d.' % i, ['a%d' % i], ['p%d' % i, 'x%d' % i], 'n%d' % i) for i in range(30)]

class T(unittest.TestCase):
    def test_stream_disjoint_and_changed(self):
        s = R.build_stream(POOL, 1); qs = [f[0] for f in s['A']]; self.assertEqual(len(set(qs)), 6); self.assertFalse(set(qs) & set(s['B']))
        self.assertTrue(all(a[1] != n[1] for a, n in zip(s['A'], s['A_new'])))
        self.assertEqual(R.build_stream(POOL, 1)['A'], s['A']); self.assertNotEqual(R.build_stream(POOL, 2)['A'], s['A'])
    def test_probes_and_items(self):
        s = R.build_stream(POOL, 1); self.assertEqual(len(R.probes_for(s['A'])), 12)
        rng = np.random.default_rng(0)
        self.assertEqual(len(R.window_items('learn', s, rng, 0)), 6); n = R.window_items('noisy', s, rng, 0); self.assertEqual(len(n), 12)
        self.assertTrue(all(i['target'] in s['wrong_pool'] for i in n[6:]))
        sh = R.window_items('shift', s, rng, 0); self.assertEqual([i['target'] for i in sh], [f[1] for f in s['A_new']])
    def test_contradiction_on_same_questions(self):
        s = R.build_stream(POOL, 1); rng = np.random.default_rng(0)
        fr = [sum(i['target'] != f[1] for i, f in zip(R.window_items('noisy', s, rng, w, .4), s['A'])) / 6 for w in range(200)]
        self.assertAlmostEqual(sum(fr) / 200, .4, delta=.06)
        it = R.window_items('noisy', s, rng, 0, .4); self.assertEqual([i['prompt'] for i in it], [f[0] for f in s['A']])
        self.assertEqual([i['target'] for i in R.window_items('noisy', s, rng, 0, 0.0)][:0], [])
    def test_summarize(self):
        tr = [('learn', .5, .2)] * 2 + [('noisy', .3, .2)] * 2 + [('shift', .6, .3), ('shift', .1, .5)]
        r = R.summarize(tr, 2); self.assertEqual(r['recovery_windows'], 2); self.assertAlmostEqual(r['shift_err'], .35)
        self.assertEqual(R.summarize([('learn', 0, 1)] * 1 + [('noisy', 0, 1)] + [('shift', .9, 1)] * 2, 2)['recovery_windows'], 3)
if __name__ == '__main__': unittest.main()
