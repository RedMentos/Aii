"""Historical committed T8 IDs must outlive the bounded retrieval window."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from v13 import world_model
from v13.online_world import OnlineWorld


class HistoricalT8LedgerTests(unittest.TestCase):
    def test_evicted_retrieval_id_is_not_relearned_after_restart(self):
        class Runtime:
            def __init__(self, home):
                self.home = Path(home)
                self.store = object()
        def row(identifier):
            return {'action_id': identifier, 's': [0., 0., 0., 0.],
                    'y': [1., 0., 0.], 'a': world_model.ACTIONS[0]}
        with tempfile.TemporaryDirectory() as home:
            runtime = Runtime(home)
            # The source window is artificially narrowed; historical IDs
            # must survive across both updates and restart.
            with patch.object(world_model, 'MAX_ROWS', 2):
                with patch.object(world_model, 'transitions', side_effect=[
                    [row('a'), row('b')], [row('b'), row('c')],
                    [row('a'), row('c')]]):
                    first = OnlineWorld(runtime)
                    self.assertEqual(first.update(limit=2)['learned'], 2)
                    self.assertEqual(first.update(limit=2)['learned'], 1)
                    restarted = OnlineWorld(runtime)
                    self.assertEqual(restarted.update(limit=2)['learned'], 0)
                    self.assertEqual(restarted.model.seen, 3)
                    self.assertEqual(restarted.processed, ['a', 'b', 'c'])
                    with self.assertRaises(ValueError):
                        restarted.evaluate_disjoint_holdout([row('a')])

    def test_ledger_exhaustion_fails_before_weight_mutation(self):
        class Runtime:
            def __init__(self, home):
                self.home = Path(home)
                self.store = object()
        with tempfile.TemporaryDirectory() as home:
            runtime = Runtime(home)
            world = OnlineWorld(runtime)
            world.processed = [str(i) for i in range(100000)]
            row = {'action_id': 'fresh', 's': [0., 0., 0., 0.],
                   'y': [1., 0., 0.], 'a': world_model.ACTIONS[0]}
            with patch.object(world_model, 'transitions', return_value=[row]):
                with self.assertRaisesRegex(ValueError, 'capacity exhausted'):
                    world.update(limit=1)
            self.assertEqual(world.model.seen, 0)


if __name__ == '__main__':
    unittest.main()
