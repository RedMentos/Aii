"""Independent PR641 cross-review: only exact JSON integer 0..3 route labels.
The word-channel/relative gate must not learn silently coerced human decisions.
"""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from v13 import learning_worker as LW

CFG = {'learning_steps': 4, 'eligibility_decay': .95,
       'learning_rate': .01, 'max_update_norm': .02,
       'retention_max_delta': .02}


class ExactRouteLabelsPR641(unittest.TestCase):
    def setUp(self):
        self.emb = np.random.default_rng(641).normal(size=(20, 8)).tolist()
        self.valid = [0, 1, 2, 3] * 5

    def attempt(self, labels, scaffold=None):
        with tempfile.TemporaryDirectory() as d:
            return LW.train({'config': CFG, 'embeddings': self.emb,
                             'labels': labels,
                             'scaffold_labels': self.valid if scaffold is None else scaffold},
                            Path(d))

    def test_float_label_must_not_truncate_to_integer(self):
        bad = self.valid.copy()
        bad[0] = 0.9
        with self.assertRaises(ValueError):
            self.attempt(bad)

    def test_string_label_must_not_parse_as_human_integer(self):
        bad = self.valid.copy()
        bad[2] = '2'
        with self.assertRaises(ValueError):
            self.attempt(bad)

    def test_boolean_label_must_not_be_accepted_as_integer(self):
        bad = self.valid.copy()
        bad[1] = True
        with self.assertRaises(ValueError):
            self.attempt(bad)

    def test_scaffold_labels_are_also_exact(self):
        bad = self.valid.copy()
        bad[1] = True
        with self.assertRaises(ValueError):
            self.attempt(self.valid, bad)

    def test_valid_json_integer_labels_still_train(self):
        metrics = self.attempt(self.valid)
        self.assertEqual(metrics['n'], 20)
        self.assertTrue(metrics['gradient_check'])
        self.assertTrue(metrics['checkpoint_reload'])


if __name__ == '__main__':
    unittest.main()
