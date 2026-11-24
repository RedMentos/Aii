"""SHADOW cross-organ fitted WorldJEPA -> private checkpoint -> heldout fixed readout.

Software/synthetic only; no online training resume, live authority or gate promotion.
"""
import hashlib
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts import world_jepa_action_permutation_control as controls
from scripts import world_jepa_digital_shadow as bridge
from scripts import world_jepa_fair_baseline as fair
from scripts import world_jepa_heldout_action_readout_20261028 as readout
from v13 import world_jepa as wj
from v13 import world_jepa_shadow_checkpoint as cp


class WorldJepaCheckpointHeldoutCrossOrgan(unittest.TestCase):
    def test_fitted_checkpoint_restores_heldout_action_readout_without_retraining(self):
        rows = bridge.synthetic_fixture(n=64, seed=20261027)
        data = bridge.make_dataset(rows)
        tr, te = data['train'], data['heldout']
        X, X2, A, Y = (data[k] for k in ('X', 'X2', 'A', 'Y'))
        self.assertEqual((len(tr), len(te)), (47, 17))
        self.assertEqual(len(data['source_sha256']), 64)

        wrong_row = controls.row_shift_actions(A, tr, te)[1]
        wrong_col = np.roll(A[te], 1, axis=1)
        self.assertFalse(np.array_equal(wrong_row, A[te]))
        np.testing.assert_array_equal(wrong_row.sum(0), A[te].sum(0))
        self.assertFalse(np.array_equal(wrong_col, A[te]))

        # This is a newly fitted synthetic test model, not a registered native
        # cohort and not a proof that JEPA improves direct supervised utility.
        model = wj.WorldJEPA(seed=3, ensemble=2).fit(
            X[tr], A[tr], X2[tr], steps=12, log_every=6)
        direct = np.c_[np.ones(len(X)), X[:, :4], A]
        dtr, dte = fair._scaled_direct(direct[tr], direct[te])

        def observed(m):
            ztr = m.predict(X[tr], A[tr])[0]
            zte = m.predict(X[te], A[te])[0]
            zrow = m.predict(X[te], wrong_row)[0]
            zcol = m.predict(X[te], wrong_col)[0]
            score = readout._frozen_readout(
                dtr, dte, ztr, zte, zrow, zcol, Y[tr], Y[te])
            confidence, labels = m.confidence(X[te], A[te])
            return ztr, zte, zrow, zcol, score, confidence, labels

        before = observed(model)
        self.assertTrue(np.any(np.abs(before[2] - before[1]) > 1e-12))
        self.assertTrue(np.any(np.abs(before[3] - before[1]) > 1e-12))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'private-fitted-shadow.npz'
            record = cp.save(model, path, data['source_sha256'])
            self.assertEqual(record['sha256'],
                             hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(record['age_authority'], 0)
            self.assertFalse(record['optimizer_state_persisted'])
            with self.assertRaises(ValueError):
                cp.load(path, '0' * 64, record['sha256'])
            restored = cp.load(path, data['source_sha256'], record['sha256'])
            self.assertEqual(restored.history, [])
            np.testing.assert_array_equal(restored.latent(X[te], target=True),
                                          model.latent(X[te], target=True))
            np.testing.assert_array_equal(restored.latent(X[te], target=False),
                                          model.latent(X[te], target=False))
            np.testing.assert_array_equal(restored.ood(X[te]), model.ood(X[te]))
            after = observed(restored)
            for index in range(4):
                np.testing.assert_array_equal(after[index], before[index])
            self.assertEqual(after[4], before[4])
            np.testing.assert_array_equal(after[5], before[5])
            self.assertEqual(after[6], before[6])


if __name__ == '__main__':
    unittest.main()
