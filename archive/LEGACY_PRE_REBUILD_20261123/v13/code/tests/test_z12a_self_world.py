from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import z12a_self_world_real as Z  # noqa: E402


class Z12aHelpersTest(unittest.TestCase):
    def test_plan_covers_every_kind_and_is_seeded(self):
        kinds, own, world = Z.plan(7, 14)
        self.assertEqual(sorted(set(kinds)), sorted(Z.KINDS)); self.assertEqual(Z.plan(7, 14), (kinds, own, world))
        self.assertTrue(all(o['approve_after'] > Z.WINDOW for o in own if o['kind'] == 'delayed'))
        self.assertTrue(any(w['op'] == 'block' for w in world))

    def test_truth_comes_from_logs(self):
        res = {'own_log': [{'name': 'e001', 'sha': Z.sha('a'), 'status': 'EXECUTED', 't_done': 10.}],
               'world_log': [{'name': 'e001', 'sha': Z.sha('b')}, {'name': 'e002', 'sha': 'DIR'}]}
        self.assertEqual(Z.truth({'channel': 'file:e001', 'value': Z.sha('a'), 't': 10.1}, res), 'own')
        self.assertEqual(Z.truth({'channel': 'file:e001', 'value': Z.sha('b'), 't': 10.1}, res), 'world')
        self.assertEqual(Z.truth({'channel': 'file:e002', 'value': 'DIR', 't': 10.1}, res), 'world')
        self.assertEqual(Z.truth({'channel': 'file:e001', 'value': Z.sha('c'), 't': 10.1}, res), 'unknown')


if __name__ == '__main__':
    unittest.main()
