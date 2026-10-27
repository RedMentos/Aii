"""Synthetic unit contracts for real-file-world SHADOW training/export lifecycle."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts import z12b_world_jepa as z12b
from scripts.world_jepa_shadow_lifecycle import export_from_rows, source_manifest
from v13.world_jepa_shadow_probe import probe_checkpoint


def rows_fixture(n=160):
    rng = np.random.default_rng(24)
    out = []
    for i in range(n):
        x = rng.normal(size=(z12b.SLOTS, 10))
        a = i % len(z12b.ACTIONS)
        op, slot = z12b.ACTIONS[a]
        y = x.copy()
        if slot is not None:
            if op.startswith('write'):
                y[slot, 0] = 1.
            elif op == 'remove':
                y[slot, 0] = 0.
            else:
                y[slot, 0] += .1
        out.append({'x': x.reshape(-1), 'a': a, 'x2': y.reshape(-1),
                    'world': False, 'world_changed': False})
    return out


class WorldRealfileLifecycleTests(unittest.TestCase):
    def test_source_manifest_is_byte_bound(self):
        a = source_manifest()
        self.assertEqual(len(a['sha256']), 64)
        self.assertTrue(a['files'])
        for row in a['files']:
            p = Path(__file__).resolve().parents[1] / row['path']
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), row['sha256'])
        self.assertEqual(a, source_manifest())

    def test_export_restart_probe_and_actual_cohort_digest(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'fresh-export'
            result = export_from_rows(rows_fixture(), target, seed=212, steps=20)
            self.assertEqual(result['schema'], 'V13_WORLD_SHADOW_LIFECYCLE_V1')
            self.assertEqual(result['mode'], 'SHADOW_ONLY')
            self.assertEqual(result['train_rows'], 128)
            self.assertEqual(result['calibration_rows'], 32)
            self.assertEqual(result['seed'], 212)
            self.assertEqual(result['checkpoint_revision'], 'z12c-slot-world-jepa-inference-npz-v2')
            self.assertFalse(result['redmi_measured'])
            self.assertFalse(result['native_body_training'])
            ckpt = target / 'slot-shadow-v2.npz'
            self.assertEqual(hashlib.sha256(ckpt.read_bytes()).hexdigest(), result['checkpoint_sha256'])
            provenance = json.loads((target / 'provenance.json').read_text())
            request = json.loads((target / 'request.json').read_text())
            probe = json.loads((target / 'probe.json').read_text())
            self.assertEqual(provenance['cohort_sha256'], result['cohort_sha256'])
            self.assertEqual(provenance['source_sha256'], result['source_sha256'])
            self.assertEqual(probe_checkpoint(ckpt, result['checkpoint_sha256'], provenance, request), probe)
            self.assertTrue(probe['after_supplied'])
            self.assertFalse(probe['after_verified'])
            self.assertEqual(probe['authority'], 0)
            self.assertEqual(json.loads((target / 'manifest.json').read_text()), result)

    def test_existing_output_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'exists'
            target.mkdir()
            marker = target / 'keep.txt'; marker.write_text('original')
            with self.assertRaises(FileExistsError):
                export_from_rows(rows_fixture(), target, seed=212, steps=10)
            self.assertEqual(marker.read_text(), 'original')

    def test_missing_clean_calibration_class_fails_before_checkpoint(self):
        rows = rows_fixture()
        for row in rows[-32:]:
            row['a'] = z12b.NOOP
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'missing-class'
            with self.assertRaises(ValueError):
                export_from_rows(rows, target, seed=212, steps=10)
            self.assertFalse((target / 'slot-shadow-v2.npz').exists())

    def test_invalid_transition_rejected_without_output(self):
        rows = rows_fixture()
        rows[0]['x'][0] = float('nan')
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'invalid'
            with self.assertRaises(ValueError):
                export_from_rows(rows, target, seed=212, steps=10)
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
