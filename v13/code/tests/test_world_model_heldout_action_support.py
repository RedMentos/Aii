"""T8 heldout action support diagnostics; no model/native execution."""
import unittest
from v13.world_model import ACTIONS, heldout_action_support


class HeldoutActionSupportTests(unittest.TestCase):
    def test_unseen_holdout_route_disclosed(self):
        rows = [{'a': 'simple'} for _ in range(8)] + [{'a': 'gist'}]
        out = heldout_action_support(rows, list(range(8)), [8])
        self.assertEqual(out['unseen_holdout_actions'], ['gist'])
        self.assertFalse(out['heldout_actions_supported'])
        self.assertEqual(out['train_action_counts']['simple'], 8)
        self.assertEqual(out['holdout_action_counts']['gist'], 1)

    def test_supported_holdout_route(self):
        rows = [{'a': 'simple'}, {'a': 'gist'}, {'a': 'simple'}]
        out = heldout_action_support(rows, [0, 1], [2])
        self.assertTrue(out['heldout_actions_supported'])
        self.assertEqual(out['unseen_holdout_actions'], [])
        self.assertEqual(tuple(out['train_action_counts']), ACTIONS)

    def test_invalid_split_rejected(self):
        rows = [{'a': 'simple'}, {'a': 'gist'}, {'a': 'detail'}]
        for train, holdout in (([0, 1], [1]), ([0, 1], []),
                               ([0, 3], [1]), ([0, True], [2]),
                               ([0], [2])):
            with self.subTest(train=train, holdout=holdout):
                with self.assertRaises(ValueError):
                    heldout_action_support(rows, train, holdout)

    def test_invalid_action_rejected(self):
        with self.assertRaises(ValueError):
            heldout_action_support([{'a': 'simple'}, {'a': 'not-a-route'}], [0], [1])


if __name__ == '__main__':
    unittest.main()
