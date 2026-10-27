"""Independent software-only tests for registered World-JEPA support audit."""
import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scripts import world_jepa_support_calibration as audit
from scripts import world_jepa_heldout_ablation as source
from v13 import world_jepa as wj


class WorldJEPASupportCalibrationTests(unittest.TestCase):
    def test_registered_source_partitions_and_hashes(self):
        tr, seen, unseen = audit.verified_cohorts()
        self.assertEqual((len(tr), len(seen), len(unseen)), (761, 193, 47))
        self.assertEqual(source.raw_hash(tr), audit.TRAIN_SEEN_SHA)
        self.assertEqual(source.raw_hash(seen), audit.TEST_SEEN_SHA)
        self.assertEqual(source.raw_hash(unseen), audit.TEST_WITHHELD_SHA)
        self.assertTrue(all(r['action'] != 3 for r in tr + seen))
        self.assertTrue(all(r['action'] == 3 for r in unseen))

    def test_source_tamper_is_rejected(self):
        tr, _, _ = audit.verified_cohorts()
        changed = copy.deepcopy(tr)
        changed[0]['bits'][0] ^= 1
        with self.assertRaisesRegex(ValueError, 'SHA/size'):
            source.verify_rows(changed, audit.TRAIN_SEEN_N, audit.TRAIN_SEEN_SHA)
        with self.assertRaisesRegex(ValueError, 'SHA/size'):
            source.verify_rows(tr[:-1], audit.TRAIN_SEEN_N, audit.TRAIN_SEEN_SHA)

    def test_calibration_bins_boundaries_and_empty_bins(self):
        conf = np.array([0., .2, .4, .6, .8, 1.])
        err = np.array([0., 1., 0., 1., 0., 1.])
        out = audit.calibration_bins(conf, err, .5)
        self.assertEqual([x['n'] for x in out['bins']], [1, 1, 1, 1, 2])
        self.assertEqual(out['success'], [True, False, True, False, True, False])
        self.assertAlmostEqual(out['heldout_success_fraction'], .5)
        with self.assertRaisesRegex(ValueError, 'Invalid calibration'):
            audit.calibration_bins([float('nan')], [0.], .5)
        with self.assertRaisesRegex(ValueError, 'Invalid calibration'):
            audit.calibration_bins([1.1], [0.], .5)
        with self.assertRaisesRegex(ValueError, 'Invalid calibration'):
            audit.calibration_bins([.5], [float('inf')], .5)

    def test_rank_ties_and_undefined_are_not_fabricated(self):
        self.assertEqual(audit._rank([2., 2., 4., 1.]).tolist(), [1.5, 1.5, 3., 0.])
        self.assertIsNone(audit.spearman_confidence_vs_negative_error([.5]*4, [0., 1., 2., 3.]))
        self.assertAlmostEqual(
            audit.spearman_confidence_vs_negative_error([.1, .2, .3], [3., 2., 1.]), 1.)
        with self.assertRaisesRegex(ValueError, 'Invalid rank'):
            audit._rank([float('nan')])

    def test_heldout_action_zero_and_ood_scores_are_measured_without_native_model(self):
        # Tiny unfrozen software-only smoke, NOT registered 1000-step measurement.
        train = [r for r in source.make_rows(100, 501) if r['action'] != 3]
        seen = [r for r in source.make_rows(30, 502) if r['action'] != 3]
        unseen = [r for r in source.make_rows(30, 502) if r['action'] == 3]
        X, A, X2, _ = source.arrays(train)
        model = wj.WorldJEPA(seed=1, ensemble=2).fit(X, A, X2, steps=0)
        Xe, Ae, X2e, _ = source.arrays(seen)
        Xu, Au, X2u, _ = source.arrays(unseen)
        err, conf, labels = audit._checked_score(model, Xe, Ae, X2e)
        self.assertEqual(err.shape, (len(seen),))
        self.assertTrue(np.isfinite(conf).all())
        self.assertEqual(len(labels), len(seen))
        _, unseen_conf, unseen_labels = audit._checked_score(model, Xu, Au, X2u)
        self.assertTrue(np.array_equal(unseen_conf, np.zeros(len(unseen))))
        self.assertEqual(set(unseen_labels), {'SIMULATION_UNCERTAIN'})
        with self.assertRaisesRegex(ValueError, 'Invalid score'):
            audit._checked_score(model, Xe, Ae[:, :3], X2e)
        with self.assertRaisesRegex(ValueError, 'Invalid score'):
            bad = Xe.copy()
            bad[0, 0] = np.nan
            audit._checked_score(model, bad, Ae, X2e)

    def test_registered_seed_set_and_no_promotion(self):
        good = [{'seed': seed, 'withheld_action_zero_confidence': 'PASS',
                 'state_ood_half_confidence': 'PASS'} for seed in audit.MODEL_SEEDS]
        self.assertEqual(audit.summarize(good)['withheld_action_gate'], 'PASS')
        self.assertEqual(audit.summarize(good)['state_ood_gate'], 'PASS')
        self.assertTrue(audit.summarize(good)['no_runtime_or_age_promotion'])
        bad = copy.deepcopy(good)
        bad[1]['state_ood_half_confidence'] = 'FAIL'
        self.assertEqual(audit.summarize(bad)['state_ood_gate'], 'FAIL')
        with self.assertRaisesRegex(ValueError, 'seeds'):
            audit.summarize(good[:-1])
        self.assertEqual(audit.NEGATIVE_GATES['jepa_weight'], 0)
        self.assertFalse(audit.NEGATIVE_GATES['whole_system_complete'])

    def test_explicit_run_required(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'receipt.json'
            with self.assertRaisesRegex(ValueError, 'Explicit'):
                audit.main(['--out', str(p)])
            self.assertFalse(p.exists())


if __name__ == '__main__':
    unittest.main()
