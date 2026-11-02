import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import bp9d_partial_own as D

POOL = [('q%d' % i, 'Answer %d.' % i, ['a%d' % i], ['p%d' % i, 'x%d' % i], 'n%d' % i) for i in range(30)]

class T(unittest.TestCase):
    def test_build(self):
        it, f, g = D.build(POOL, 1); self.assertEqual(len(it), 16)
        self.assertEqual({k: g.count(k) for k in D.GROUPS}, D.SIZES)
        for i, gg in zip(it, g):
            own = POOL[int(i['memory_id'][5:])]; self.assertEqual(i['answer_keys'] != own[2], gg == 'own_wrong')
        self.assertEqual(D.build(POOL, 1)[0], it)
    def test_weights(self):
        g = ['human', 'outcome', 'own_right', 'own_wrong']
        self.assertEqual(D.weights_for('uniform_sgd', g), [1.0] * 4); self.assertEqual(D.weights_for('own030_sgd', g), [.45, 1.0, .3, .3])
    def test_by_group(self):
        _, _, g = D.build(POOL, 1); r = D.by_group([{'ok': True}] * 16, g); self.assertTrue(all(v == 1 for v in r.values()))
if __name__ == '__main__': unittest.main()
