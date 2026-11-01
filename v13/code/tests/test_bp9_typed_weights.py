import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import bp9_typed_weights as B

POOL = [('q%d' % i, 'Answer %d.' % i, ['a%d' % i], ['p%da' % i, 'p%db' % i], 'n%d' % i) for i in range(24)]

class T(unittest.TestCase):
    def setUp(self):
        self.items, self.facts, self.groups = B.build(POOL, 1)
    def test_groups_and_wrong_targets(self):
        self.assertEqual(self.groups.count('own_wrong'), 4); self.assertEqual(len(self.items), 16)
        for it, f, g in zip(self.items, self.facts, self.groups):
            own = POOL[int(it['memory_id'][4:])]
            self.assertEqual(it['answer_keys'] != own[2], g == 'own_wrong')
    def test_deterministic(self):
        self.assertEqual(B.build(POOL, 1)[0], self.items); self.assertNotEqual(B.build(POOL, 2)[0], self.items)
    def test_arms(self):
        u = B.arm_items('uniform', self.items, self.groups, 1); self.assertTrue(all(i['weight'] == 1.0 for i in u))
        t = B.arm_items('typed', self.items, self.groups, 1); w = {g: [i['weight'] for i, gg in zip(t, self.groups) if gg == g] for g in B.GROUPS}
        self.assertTrue(max(w['own_wrong']) < min(w['human']) < min(w['outcome']) + 1e-9)
        n = B.arm_items('no_own', self.items, self.groups, 1); self.assertEqual(len(n), 8)
        s = B.arm_items('shuffled', self.items, self.groups, 1); self.assertEqual(sorted(i['weight'] for i in s), sorted(i['weight'] for i in t))
        self.assertNotEqual([i['weight'] for i in s], [i['weight'] for i in t])
    def test_by_group(self):
        rows = [{'ok': k % 2 == 0} for k in range(16)]; r = B.by_group(rows, self.groups, {'human', 'outcome', 'own_right', 'own_wrong'})
        self.assertTrue(all(0 <= v <= 1 for v in r.values()))
        self.assertIsNone(B.by_group(rows, self.groups, {'human'})['own_wrong'])
if __name__ == '__main__': unittest.main()
