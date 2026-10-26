"""Run618 frozen prospective cohort, synthetic model-free and real SQLite replay tests."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import run618_prospective_b2_native as R

COHORT = Path(__file__).resolve().parents[1] / 'docs/proofs/continuation-20261026/run618-prospective-b2-native/RUN618_COHORT.json'


class ProspectiveTests(unittest.TestCase):
    def test_registered_source_disjoint_cohort_exact(self):
        # Local original cohort is optional in the source ZIP, but required in GitHub CI.
        if not COHORT.exists():
            self.skipTest('Run618 new registered cohort not in historical Run601 ZIP')
        rows = R.load_cohort(COHORT)
        self.assertEqual(len(rows), 80)
        self.assertEqual(len({r['text'] for r in rows}), 80)
        self.assertEqual(sum(r['topic'] in R.TEST for r in rows), 20)
        self.assertEqual(sum(r['topic'] in R.TRAIN for r in rows), 60)

    def test_wrong_source_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'cohort.json'
            p.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'preregistered cohort changed'):
                R.load_cohort(p)

    def test_rank_excludes_self_and_rejects_nonfinite(self):
        m = np.array([[1., .9, .1], [.9, 1., .2], [.1, .2, 1.]])
        out = R.ranking(m, [1, 0, 1])
        self.assertEqual(out['top1'], 1.)
        m[0, 1] = float('nan')
        with self.assertRaises(ValueError):
            R.ranking(m, [1, 0, 1])

    def test_synthetic_full_replay_is_source_bound_and_deterministic(self):
        if not COHORT.exists():
            self.skipTest('Run618 new registered cohort not in historical Run601 ZIP')
        rows = R.load_cohort(COHORT)
        rng = np.random.default_rng(618)
        facts = rng.normal(size=(40, 1024))
        states = np.vstack([facts[i] + rng.normal(scale=.005, size=1024)
                            for i in range(40) for _ in 'AB'])
        result = R.evaluate(rows, states)
        self.assertEqual(result['replay_queries'], 20)
        self.assertEqual(result['replay_top5_order_mismatches'], 0)
        self.assertEqual(result['replay_operator_top1'], result['metrics']['b2_raw']['top1'])
        self.assertGreaterEqual(result['metrics']['b2_raw']['top1'], .9)
        self.assertEqual(result['controls'], 200)

    def test_native_dimensions_and_gates(self):
        self.assertEqual(R.GATES['STEP2'], 'UTILITY_FAIL')
        self.assertEqual(R.GATES['Body_JEPA'], 'UNAVAILABLE')
        self.assertEqual(R.GATES['jepa_weight'], 0)
        with self.assertRaisesRegex(ValueError, 'shape'):
            R.evaluate([], np.zeros((3, 1024)))


if __name__ == '__main__':
    unittest.main()
