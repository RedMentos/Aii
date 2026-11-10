import copy
import importlib.util
from pathlib import Path
import unittest

import numpy as np

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'jepa_bounded_replay_ablation_20261110.py'
spec = importlib.util.spec_from_file_location('jepa_bounded_replay_research', SCRIPT)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class ReplayAblationTests(unittest.TestCase):
    def test_train_and_holdout_are_disjoint_even_with_forged_ids(self):
        train = bench.generate(13, 1, 32, 'A')
        held = bench.generate(13, 101, 64, 'A')
        bench.verify_disjoint([train], [held])
        forged = copy.deepcopy(held)
        forged['x'][0] = train['x'][0]
        forged['a'][0] = train['a'][0]
        with self.assertRaisesRegex(ValueError, 'overlap'):
            bench.verify_disjoint([train], [forged])
        forged = copy.deepcopy(held)
        forged['ids'] = (train['ids'][0],) + forged['ids'][1:]
        with self.assertRaisesRegex(ValueError, 'overlap'):
            bench.verify_disjoint([train], [forged])

    def test_replay_mixing_preserves_equal_rows_and_bounded_history(self):
        a = bench.generate(21, 1, 32, 'A')
        b = bench.generate(21, 2, 32, 'B')
        c = bench.generate(21, 3, 32, 'A')
        mixed = bench.mixed(c, [a, b])
        self.assertEqual(len(mixed[0]), 32)
        np.testing.assert_array_equal(mixed[0][:16], c['x'][:16])
        np.testing.assert_array_equal(mixed[0][16:24], a['x'][:8])
        np.testing.assert_array_equal(mixed[0][24:], b['x'][:8])

    def test_real_world_jepa_updates_matched_and_frozen_control_unchanged(self):
        result = bench.run_seed(13, steps=2)
        arms = result['arms']
        self.assertEqual([p['fit_steps'] for p in arms['frozen']], [2, 2, 2])
        self.assertEqual([p['fit_steps'] for p in arms['current']], [2, 4, 6])
        self.assertEqual([p['fit_steps'] for p in arms['replay']], [2, 4, 6])
        self.assertEqual(arms['frozen'][0]['old_A'], arms['frozen'][2]['old_A'])
        self.assertNotEqual(arms['current'][0]['old_A'], arms['current'][1]['old_A'])
        self.assertEqual([p['stored_rows'] for p in arms['replay']], [0, 16, 32])
        self.assertGreater(arms['replay'][2]['nominal_stored_array_bytes'], 0)
        self.assertEqual(len(result['source_sha256']), 64)

    def test_seed_reproducibility_and_input_guards(self):
        self.assertEqual(bench.run_seed(21, steps=1), bench.run_seed(21, steps=1))
        with self.assertRaises(ValueError):
            bench.run(seeds=(13, 13), steps=1)
        with self.assertRaises(ValueError):
            bench.run_seed(13, steps=0)


if __name__ == '__main__':
    unittest.main()
