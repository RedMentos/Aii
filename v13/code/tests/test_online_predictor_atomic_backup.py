"""Regression: interrupted rollback-backup copy must not destroy last good backup.

Run: cd v13/code && python -m unittest tests.test_online_predictor_atomic_backup
Synthetic NumPy/filesystem test only; no Android hardware evidence.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.continuous_predictor import OnlinePredictor


class AtomicPreviousBackupTests(unittest.TestCase):
    def test_interrupted_backup_copy_preserves_current_and_previous(self):
        with tempfile.TemporaryDirectory() as home:
            predictor = OnlinePredictor(2, 2, home, replay=4, seed=5)
            predictor.checkpoint()
            predictor.observe([0.1, 0.0], 0, [0.2, 0.0])
            predictor.checkpoint()
            current = Path(predictor.path)
            previous = current.with_suffix('.previous.npz')
            old_current = current.read_bytes()
            old_previous = previous.read_bytes()

            def interrupted_copy(source, destination):
                Path(destination).write_bytes(b'partial rollback backup')
                raise OSError('simulated interrupted backup copy')

            predictor.observe([0.2, 0.0], 1, [0.3, 0.0])
            with patch('v13.continuous_predictor.shutil.copy2',
                       side_effect=interrupted_copy):
                with self.assertRaisesRegex(OSError, 'interrupted backup'):
                    predictor.checkpoint()
            self.assertEqual(current.read_bytes(), old_current)
            self.assertEqual(previous.read_bytes(), old_previous)
            self.assertFalse(current.with_suffix('.previous.tmp.npz').exists())
            self.assertFalse(current.with_name(current.name + '.tmp.npz').exists())

            # Both committed snapshots remain loadable after the failed write.
            predictor.restore()
            predictor.rollback()


if __name__ == '__main__':
    unittest.main()
