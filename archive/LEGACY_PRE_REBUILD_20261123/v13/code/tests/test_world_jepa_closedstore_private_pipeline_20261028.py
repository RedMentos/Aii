"""Closed SQLite -> fitted private World-JEPA -> operator probe: software only."""
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import world_jepa_closedstore_private_pipeline as pipe
from scripts import world_jepa_digital_shadow as bridge
from scripts import world_jepa_readonly_store as closed
from scripts import world_jepa_shadow_operator_probe as probe
from tests.test_world_jepa_readonly_store import fixture, sha
from v13 import world_jepa as wj
from v13 import world_jepa_shadow_checkpoint as cp
from v13 import world_model as wm


class ClosedStorePrivateShadowPipeline(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'closed.sqlite'
        self.checkpoint = self.root / 'private-shadow.npz'
        fixture(self.db, n=64)

    def test_actual_closed_sqlite_train_only_checkpoint_probe_no_db_mutation(self):
        original_sha = sha(self.db)
        store = closed.ReadOnlyStore(self.db)
        try:
            data = bridge.make_dataset(wm.transitions(store))
        finally:
            store.close()
        tr, te = data['train'], data['heldout']
        original_fit = wj.WorldJEPA.fit
        seen = []

        def spy(model, X, A, X2, steps, log_every):
            np.testing.assert_array_equal(X, data['X'][tr])
            np.testing.assert_array_equal(A, data['A'][tr])
            np.testing.assert_array_equal(X2, data['X2'][tr])
            seen.append((steps, log_every, len(X)))
            return original_fit(model, X, A, X2, steps=steps,
                                log_every=log_every)

        with patch.object(wj.WorldJEPA, 'fit', spy):
            result = pipe.run_db(self.db, self.checkpoint, steps=5)
        self.assertEqual(seen, [(5, 5, 47)])
        self.assertEqual((result['observed_rows'], result['train_rows'],
                          result['heldout_rows']), (64, 47, 17))
        self.assertEqual(result['source_sha256'], data['source_sha256'])
        self.assertEqual(result['source_digest_kind'],
                         'CANONICAL_OBSERVED_TRANSITIONS_NOT_DB_FILE')
        self.assertEqual(result['checkpoint_sha256'], sha(self.checkpoint))
        self.assertEqual(stat.S_IMODE(self.checkpoint.stat().st_mode) & 0o077, 0)
        self.assertEqual(sha(self.db), original_sha)
        self.assertFalse(any(Path(str(self.db) + s).exists()
                             for s in ('-wal', '-shm', '-journal')))
        restored = cp.load(self.checkpoint, result['source_sha256'],
                           result['checkpoint_sha256'])
        heldout = probe.infer(self.checkpoint, result['source_sha256'],
                              result['checkpoint_sha256'], {
                                  'observations': data['X'][te].tolist(),
                                  'actions': data['A'][te].tolist(),
                              })
        self.assertEqual(heldout['rows'], 17)
        self.assertEqual(result['heldout_label_counts']['MODEL_SIMULATION'] +
                         result['heldout_label_counts']['SIMULATION_UNCERTAIN'], 17)
        self.assertAlmostEqual(result['mean_heldout_confidence'],
                               float(np.mean(heldout['confidence'])))
        self.assertEqual(restored.history, [])
        self.assertTrue(result['checkpoint_inference_only'])
        self.assertFalse(result['optimizer_state_persisted'])
        self.assertFalse(result['runtime_wired'])
        self.assertFalse(result['tool_authority'])
        self.assertEqual(result['age_authority'], 0)
        self.assertFalse(result['utility_proven'])
        self.assertEqual(result['negative_gates_unchanged']['jepa_weight'], 0)
        text = json.dumps(result, allow_nan=False)
        for private in ('synthetic-action-', 'synthetic-event-', str(self.db),
                        str(self.checkpoint), 'predicted_next_latent'):
            self.assertNotIn(private, text)

    def test_cli_requires_closed_store_ack_and_sanitizes_failure(self):
        out = io.StringIO()
        self.assertEqual(pipe.main(['--db', str(self.db),
                                    '--private-checkpoint', str(self.checkpoint)],
                                   stdout=out), 2)
        self.assertEqual(json.loads(out.getvalue())['status'], 'UNAVAILABLE')
        self.assertFalse(self.checkpoint.exists())
        out = io.StringIO()
        self.assertEqual(pipe.main(['--db', str(self.db),
                                    '--private-checkpoint', str(self.checkpoint),
                                    '--ack-closed-store', '--steps', '5'],
                                   stdout=out), 0)
        self.assertEqual(json.loads(out.getvalue())['scope'],
                         'CLOSED_STORE_OBSERVED_DIGITAL_PRIVATE_SHADOW')
        self.assertNotIn(str(self.db), out.getvalue())

    def test_live_sidecar_symlink_existing_checkpoint_and_small_store_rejected(self):
        sidecar = Path(str(self.db) + '-wal')
        sidecar.write_bytes(b'not quiescent')
        with self.assertRaisesRegex(ValueError, 'sidecar'):
            pipe.run_db(self.db, self.checkpoint, steps=5)
        self.assertFalse(self.checkpoint.exists())
        sidecar.unlink()
        alias = self.root / 'alias.sqlite'
        alias.symlink_to(self.db)
        with self.assertRaisesRegex(ValueError, 'regular'):
            pipe.run_db(alias, self.checkpoint, steps=5)
        self.checkpoint.write_bytes(b'keep original')
        with self.assertRaises(ValueError):
            pipe.run_db(self.db, self.checkpoint, steps=5)
        self.assertEqual(self.checkpoint.read_bytes(), b'keep original')
        small = self.root / 'small.sqlite'
        fixture(small, n=16)
        with self.assertRaises(ValueError):
            pipe.run_db(small, self.root / 'new.npz', steps=5)
        self.assertFalse((self.root / 'new.npz').exists())

    def test_invalid_training_steps_refused_without_writes(self):
        for steps in (0, 401, True, 1.5, -1):
            with self.subTest(steps=steps), self.assertRaises(ValueError):
                pipe.run_db(self.db, self.checkpoint, steps=steps)
            self.assertFalse(self.checkpoint.exists())


if __name__ == '__main__':
    unittest.main()
