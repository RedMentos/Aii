"""Model-free and optional pinned real-native tests for Run615; no inference."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run615_crosscohort_shadow as R


def fixture(seed=0):
    rng = np.random.default_rng(seed)
    # 40 source-disjoint fact pairs; train 30 facts and test 10 facts.
    ids = [f'topic-{i}-{variant}' for i in range(1, 41) for variant in 'AB']
    base = rng.normal(size=(40, 32))
    x = np.zeros((80, 2048)); y = np.zeros((80, 1024))
    for i in range(40):
        for v in range(2):
            x[2*i+v, :32] = base[i] + rng.normal(scale=.03, size=32)
            y[2*i+v, :32] = base[i] + rng.normal(scale=.03, size=32)
    return x, y, ids, np.arange(60), np.arange(60, 80)


class Run615ContractTests(unittest.TestCase):
    def test_valid_pairing_and_split(self):
        x, y, ids, tr, te = fixture()
        a = R.validate(x, y, ids, tr, te)
        self.assertEqual(a[0].shape, (80, 2048))
        self.assertEqual(len(a[4]), 20)

    def test_nonfinite_and_zero_rejected(self):
        x, y, ids, tr, te = fixture()
        x[0, 0] = float('nan')
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            R.validate(x, y, ids, tr, te)
        x, y, ids, tr, te = fixture()
        y[0] = 0
        with self.assertRaisesRegex(ValueError, 'zero'):
            R.validate(x, y, ids, tr, te)

    def test_fact_leakage_and_overlap_rejected(self):
        x, y, ids, tr, te = fixture()
        te = te.copy(); te[0] = 59
        with self.assertRaisesRegex(ValueError, 'overlap'):
            R.validate(x, y, ids, tr, te)
        tr, te = np.arange(60), np.arange(60, 80)
        tr = tr.copy(); te = te.copy(); tr[-1], te[0] = te[0], tr[-1]
        with self.assertRaisesRegex(ValueError, 'fact leakage'):
            R.validate(x, y, ids, tr, te)

    def test_missing_opposite_and_duplicate_rejected(self):
        x, y, ids, tr, te = fixture()
        ids[1] = 'topic-1-C'
        with self.assertRaisesRegex(ValueError, 'invalid prompt'):
            R.validate(x, y, ids, tr, te)
        ids = fixture()[2]; ids[1] = ids[0]
        with self.assertRaisesRegex(ValueError, 'invalid prompt'):
            R.validate(x, y, ids, tr, te)

    def test_score_excludes_self_and_ties_deterministically(self):
        x = np.eye(4)
        ids = ['topic-1-A', 'topic-1-B', 'topic-2-A', 'topic-2-B']
        result = R.score(x, x, ids)
        self.assertEqual(result['top1'], .5)  # first nonself candidate wins on zero ties
        self.assertTrue(0 < result['mrr'] <= 1)

    def test_trainonly_predictions_and_shuffle_determinism(self):
        a = fixture(1)
        p = R.fit_ridge(a[0][a[3]], a[1][a[3]])
        self.assertEqual(R.predict_ridge(p, a[0][a[4]]).shape, (20, 1024))
        f = R.fit_procrustes(a[0][a[3]], a[1][a[3]])
        q, c = R.predict_procrustes(f, a[0][a[4]], a[1][a[4]])
        self.assertEqual((q.shape, c.shape), ((20, 32), (20, 32)))
        b = R.evaluate(a, a, shuffles=3)
        self.assertEqual(b, R.evaluate(a, a, shuffles=3))
        self.assertEqual(b['shuffled']['n'], 3)

    def test_hash_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'RUN608_STATES.npz'
            np.savez(p, x_b1=np.ones((80, 2048)))
            (Path(tmp) / 'RUN608_NATIVE_REPORT.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                R.load(tmp, '608')

    def test_pins_and_gates_not_promoted(self):
        self.assertEqual(R.GATES['STEP2'], 'UTILITY_FAIL')
        self.assertEqual(R.GATES['B3_L1'], 'FAIL')
        self.assertEqual(R.GATES['Body_JEPA'], 'UNAVAILABLE')
        self.assertEqual(R.GATES['jepa_weight'], 0)
        self.assertEqual(R.GATES['Redmi'], 'UNMEASURED')

    @unittest.skipUnless(os.getenv('RUN615_NATIVE608') and os.getenv('RUN615_NATIVE614'),
                         'original native artifact paths not provided')
    def test_actual_pinned_native_artifacts(self):
        result = R.run(os.environ['RUN615_NATIVE608'], os.environ['RUN615_NATIVE614'])
        self.assertEqual(result['baseline']['b2_only']['top1'], .85)
        self.assertEqual(result['status'], 'NO_CROSS_BODY_GAIN')
        self.assertFalse(result['native_body_training'])
        self.assertFalse(result['receiver_injection'])


if __name__ == '__main__':
    unittest.main()