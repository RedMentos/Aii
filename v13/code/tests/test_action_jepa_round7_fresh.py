"""Round-7 fresh tool world: new start values only, explicit synthetic previous world."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_jepa_round7_fresh as r7


class Round7FreshTests(unittest.TestCase):
    def test_fresh_values_never_reuse_previous_world(self):
        with tempfile.TemporaryDirectory() as tmp:
            prev = Path(tmp) / 'world.json'
            prev.write_text(json.dumps({'episodes': [{'value': v} for v in range(1, 600)]}))
            values, order, used = r7.fresh_values(prev, 300, 7)
            self.assertEqual(len(set(values)), 300)
            self.assertFalse(set(values) & set(used))
            self.assertEqual(sorted(order), values)
            self.assertEqual(r7.fresh_values(prev, 300, 7)[0], values)
            with self.assertRaisesRegex(ValueError, 'Not enough'):
                r7.fresh_values(prev, 401, 7)

    def test_world_runs_real_calc_tool_on_fresh_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prev = root / 'prev.json'
            prev.write_text(json.dumps({'episodes': [{'value': v} for v in range(1, 990)]}))
            args = type('A', (), {'previous_world': str(prev), 'states': 8, 'seed': 3, 'out': str(root / 'w')})
            report = r7.world(args)
            doc = json.loads((root / 'w/world.json').read_text())
            self.assertEqual(report['states'], 8)
            self.assertTrue(all(e['value'] >= 990 for e in doc['episodes']))
            e = doc['episodes'][0]
            self.assertEqual(e['outcomes']['double'], 'After doubling, the counter shows %s.' % (e['value'] * 2))
            tx = json.loads((root / 'w' / e['tx']['add_15']['path']).read_text())
            self.assertEqual(tx['status'], 'EXECUTED')
            self.assertEqual(tx['intent'], 'round7:add_15')


if __name__ == '__main__':
    unittest.main()
