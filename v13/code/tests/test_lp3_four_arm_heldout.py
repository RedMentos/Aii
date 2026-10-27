"""LP3 all-arm heldout prereg source/controls: software-only tests."""
import tempfile
import unittest
from pathlib import Path

from scripts import lp3_four_arm_heldout as p
from scripts import lp3_lr_norm_ablation as a
from scripts.lp3_heldout_utility import fixture, audit_fixture


class FourArmHeldoutTests(unittest.TestCase):
    def test_new_phrasings_are_exactly_disjoint_and_answer_free(self):
        original = fixture()
        original_copy = fixture()
        fresh = p.fresh_rows(original)
        self.assertEqual(original, original_copy)
        self.assertEqual(len(fresh), 6)
        self.assertEqual(p.FRESH_TEMPLATES, (
            'For the registry key {key}, what marker is recorded?',
            'Read the registry: {key} maps to which marker?'))
        self.assertEqual(len({q for row in fresh for q in row['heldout']}), 12)
        old_questions = {q for row in original
                         for q in [row['train'], *row['heldout']]}
        for row, previous in zip(fresh, original):
            self.assertEqual(row['train'], previous['train'])
            self.assertEqual(row['answer'], previous['answer'])
            for target, wrong in zip(row['heldout'], row['wrong_sources']):
                self.assertNotEqual(target, wrong)
                self.assertNotIn(row['answer'].strip().casefold(),
                                 target.casefold())
                self.assertNotIn(target, old_questions)
                self.assertNotIn(wrong, old_questions)
        self.assertEqual(a.ARMS, (
            ('raw', .005), ('raw', .0005),
            ('layernorm', .005), ('layernorm', .0005)))

    def test_fresh_phrasing_rejects_modified_training_cohort(self):
        rows = fixture()
        rows[0]['answer'] = ' a forged marker'
        with self.assertRaises(ValueError):
            p.fresh_rows(rows)

    def test_paired_gain_signs_and_first_token_counts(self):
        before = {'own_ce': 2., 'wrong_ce': 2.5,
                  'zero_ce': 2.4, 'own_top1': 0,
                  'wrong_top1': 0, 'zero_top1': 0}
        after = {'own_ce': 1., 'wrong_ce': 2.2,
                 'zero_ce': 2.3, 'own_top1': 6,
                 'wrong_top1': 1, 'zero_top1': 0}
        gain = p._gain(before, after)
        self.assertAlmostEqual(gain['own_ce_gain'], 1.)
        self.assertAlmostEqual(gain['own_vs_wrong_ce_after'], 1.2)
        self.assertAlmostEqual(gain['own_vs_zero_ce_after'], 1.3)
        self.assertAlmostEqual(gain['own_gain_over_wrong_gain'], .7)
        self.assertEqual(gain['own_top1_after'], 6)

    def test_no_implicit_model_execution_or_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'receipt.json'
            with self.assertRaisesRegex(ValueError, 'Explicit'):
                p.main(['--master', d, '--out', str(out)])
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
