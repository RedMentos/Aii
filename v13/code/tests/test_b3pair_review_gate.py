"""Regression checks for the review-only BP5 paired-state precheck."""
import math
import unittest

import numpy as np

from v13 import b3pair


class PairedPrecheckReviewTests(unittest.TestCase):
    def setUp(self):
        self.acc = {'NO_MESSAGE': .69, 'SCALAR': .90, 'L1': .94, 'L2': .82}
        self.manifest = {'rows': 3000}

    def test_valid_signal_has_go(self):
        result = b3pair.precheck(self.acc, self.manifest)
        self.assertEqual(result['verdict'], 'GO')
        self.assertAlmostEqual(result['headroom'], .12)

    def test_invalid_accuracy_is_never_go(self):
        for key in self.acc:
            for value in (math.nan, math.inf, -math.inf, -0.01, 1.01, True, None, '0.9'):
                with self.subTest(key=key, value=value):
                    values = dict(self.acc, **{key: value})
                    self.assertEqual(b3pair.precheck(values, self.manifest)['verdict'], 'NO_GO')

    def test_missing_accuracy_is_never_go(self):
        for key in self.acc:
            with self.subTest(key=key):
                values = dict(self.acc)
                del values[key]
                self.assertEqual(b3pair.precheck(values, self.manifest)['verdict'], 'NO_GO')

    def test_rows_must_be_a_sufficient_integer(self):
        for rows in (math.nan, math.inf, 3000.5, True, -1, None, '3000'):
            with self.subTest(rows=rows):
                self.assertEqual(b3pair.precheck(self.acc, {'rows': rows})['verdict'], 'NO_GO')
        self.assertEqual(b3pair.precheck(self.acc, {})['verdict'], 'NO_GO')

    def test_scalar_baseline_must_be_beaten(self):
        for scalar in (.94, .99):
            with self.subTest(scalar=scalar):
                values = dict(self.acc, SCALAR=scalar)
                self.assertEqual(b3pair.precheck(values, self.manifest)['verdict'], 'NO_GO')

    def test_row_digests_used_for_disjointness_must_be_verified(self):
        sender = np.array([[1.0, 2.0], [3.0, 4.0]])
        receiver = np.array([[5.0], [6.0]])
        labels = np.array([0, 1])
        manifest = b3pair.build_manifest(sender, receiver, labels, 'sender', 'receiver', 1, 'task')
        self.assertTrue(b3pair.verify(manifest, sender, receiver, labels)[0])
        changed = dict(manifest, row_sha256=['0' * 16, '1' * 16])
        self.assertFalse(b3pair.verify(changed, sender, receiver, labels)[0])
        missing = dict(manifest)
        del missing['row_sha256']
        self.assertFalse(b3pair.verify(missing, sender, receiver, labels)[0])
        wrong_revision = dict(manifest, revision='different')
        self.assertFalse(b3pair.verify(wrong_revision, sender, receiver, labels)[0])


if __name__ == '__main__':
    unittest.main()
