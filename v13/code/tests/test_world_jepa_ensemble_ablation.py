"""Exact frozen Linux World-JEPA ensemble-mean ablation and tamper counterexamples."""
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.world_jepa_ensemble_ablation import ablate, CHECKPOINT_SHA256


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class FrozenWorldEnsembleAblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.environ.get('V13_FROZEN_WORLD_ROOT')
        if not root or not Path(root).is_dir():
            raise unittest.SkipTest('Exact SHA-bound original Actions artifact not mounted')
        cls.root = Path(root)

    def test_exact_original_checkpoint_and_independent_reference(self):
        result = ablate(self.root)
        self.assertEqual(result['checkpoint_sha256'], CHECKPOINT_SHA256)
        self.assertEqual(result['seeds'], [313, 314, 315])
        self.assertEqual(result['rows'], 480)
        self.assertEqual(result['authority'], 0)
        self.assertFalse(result['training_performed'])
        self.assertFalse(result['redmi_measured'])
        self.assertEqual(result['step2'], 'UTILITY_FAIL')
        self.assertEqual(result['b3'], 'L1_FAIL')
        self.assertEqual(result['jepa_weight'], 0)
        self.assertAlmostEqual(result['weighted_first_mse'], 0.31348980990632647, places=10)
        self.assertAlmostEqual(result['weighted_identity_mse'], 0.27064646738716414, places=10)
        self.assertEqual(result['ensemble_mean_beats_first_seeds'], 0)
        self.assertEqual(result['ensemble_mean_beats_identity_seeds'], 0)
        self.assertGreater(result['weighted_ensemble_mean_mse'], result['weighted_first_mse'])
        self.assertGreater(result['weighted_ensemble_mean_mse'], result['weighted_identity_mse'])

    def test_exact_source_and_all_raw_inputs_remain_unchanged(self):
        paths = sorted(p for p in self.root.rglob('*') if p.is_file())
        before = [(str(p.relative_to(self.root)), digest(p)) for p in paths]
        ablate(self.root)
        after = [(str(p.relative_to(self.root)), digest(p)) for p in paths]
        self.assertEqual(before, after)

    def test_forged_heldout_manifest_denied(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / 'copy'
            shutil.copytree(self.root, dest)
            p = dest / 'heldout314' / 'manifest.json'
            p.write_bytes(p.read_bytes() + b' ')
            with self.assertRaises(ValueError):
                ablate(dest)

    def test_swapped_seed_cohort_denied(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / 'copy'
            shutil.copytree(self.root, dest)
            p = dest / 'heldout315' / 'manifest.json'
            p.write_bytes((dest / 'heldout' / 'manifest.json').read_bytes())
            with self.assertRaises(ValueError):
                ablate(dest)

    def test_wrong_checkpoint_bytes_denied(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / 'copy'
            shutil.copytree(self.root, dest)
            p = dest / 'training' / 'slot-shadow-v2.npz'
            p.write_bytes(p.read_bytes() + b'\x00')
            with self.assertRaises(ValueError):
                ablate(dest)


if __name__ == '__main__':
    unittest.main()
