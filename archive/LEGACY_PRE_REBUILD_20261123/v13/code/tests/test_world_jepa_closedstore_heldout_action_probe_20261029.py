"""Closed-store fixed-readout action ablation: actual SQLite SELECT and software fit."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import world_jepa_closedstore_heldout_action_probe_20261029 as cli
from scripts import world_jepa_digital_shadow as bridge
from scripts import world_jepa_readonly_store as closed
from tests.test_world_jepa_readonly_store import fixture, sha
from v13 import world_jepa as wj
from v13 import world_model as wm


class ClosedStoreActionAblation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'observed.sqlite'
        fixture(self.db, n=64)

    def test_actual_sqlite_train_only_fit_frozen_heldout_controls_no_mutation(self):
        before = sha(self.db)
        store = closed.ReadOnlyStore(self.db)
        try:
            data = bridge.make_dataset(wm.transitions(store))
        finally:
            store.close()
        tr = data['train']
        original_fit = wj.WorldJEPA.fit
        observed = []

        def spy(model, X, A, X2, steps):
            np.testing.assert_array_equal(X, data['X'][tr])
            np.testing.assert_array_equal(A, data['A'][tr])
            np.testing.assert_array_equal(X2, data['X2'][tr])
            observed.append((model.seed, steps, len(X)))
            return original_fit(model, X, A, X2, steps=steps)

        with patch.object(wj.WorldJEPA, 'fit', spy):
            report = cli.run_db(self.db, steps=3)
        self.assertEqual(observed, [(3, 3, 47), (7, 3, 47)])
        self.assertEqual((report['n'], report['train_n'], report['heldout_n']),
                         (64, 47, 17))
        self.assertEqual(report['source_sha256'], data['source_sha256'])
        self.assertTrue(report['store_readonly'])
        self.assertTrue(report['training_partition_only'])
        self.assertTrue(report['heldout_actions_used_only_for_scoring'])
        self.assertTrue(report['readout_frozen_for_heldout_controls'])
        self.assertTrue(report['heldout_row_marginals_preserved'])
        self.assertEqual(report['scope'], 'CLOSED_STORE_FIXED_READOUT_DIGITAL_SHADOW')
        self.assertEqual(report['source_digest_kind'],
                         'CANONICAL_PARSED_TRANSITIONS_NOT_DB_BYTES')
        self.assertFalse(report['store_bytes_independently_verified'])
        self.assertFalse(report['utility_proven'])
        self.assertFalse(report['tool_authority'])
        self.assertFalse(report['native_executed'])
        self.assertFalse(report['phone_measured'])
        self.assertFalse(report['runtime_wired'])
        self.assertFalse(report['model_weights_persisted'])
        self.assertEqual(report['age_authority'], 0)
        self.assertEqual(report['negative_gates_unchanged']['jepa_weight'], 0)
        self.assertEqual(sha(self.db), before)
        self.assertFalse(any(Path(str(self.db) + s).exists()
                             for s in ('-wal', '-shm', '-journal')))
        text = json.dumps(report, sort_keys=True, allow_nan=False)
        for private in ('synthetic-action-', 'synthetic-event-', str(self.db),
                        'predicted_next_latent'):
            self.assertNotIn(private, text)
        for seed in report['per_seed']:
            self.assertTrue(np.isfinite(seed['gain_vs_direct']))
            self.assertTrue(np.isfinite(seed['gain_vs_heldout_row_mismatch']))
            self.assertTrue(np.isfinite(seed['gain_vs_heldout_column_mismatch']))

    def test_two_operator_acknowledgements_required_before_store_access(self):
        for flags in ([], ['--ack-closed-store'], ['--ack-shadow-fit']):
            with self.subTest(flags=flags):
                out = io.StringIO()
                with patch.object(cli, 'run_db', side_effect=AssertionError('must not read')):
                    rc = cli.main(['--db', str(self.db), *flags], stdout=out)
                self.assertEqual(rc, 2)
                self.assertEqual(json.loads(out.getvalue())['status'], 'UNAVAILABLE')
                self.assertNotIn(str(self.db), out.getvalue())

    def test_operator_cli_returns_aggregate_only_with_explicit_ack(self):
        before = sha(self.db)
        out = io.StringIO()
        rc = cli.main(['--db', str(self.db), '--ack-closed-store',
                       '--ack-shadow-fit', '--steps', '0'], stdout=out)
        self.assertEqual(rc, 0)
        report = json.loads(out.getvalue())
        self.assertEqual(report['steps'], 0)
        self.assertEqual(report['n'], 64)
        self.assertFalse(report['utility_proven'])
        self.assertNotIn(str(self.db), out.getvalue())
        self.assertNotIn('synthetic-action-', out.getvalue())
        self.assertEqual(sha(self.db), before)

    def test_sidecar_symlink_small_store_and_nonfinite_output_fail_closed(self):
        flags = ['--ack-closed-store', '--ack-shadow-fit', '--steps', '0']
        sidecar = Path(str(self.db) + '-wal')
        sidecar.write_bytes(b'live')
        out = io.StringIO()
        self.assertEqual(cli.main(['--db', str(self.db), *flags], stdout=out), 2)
        self.assertEqual(json.loads(out.getvalue())['status'], 'UNAVAILABLE')
        sidecar.unlink()
        alias = self.root / 'alias.sqlite'
        alias.symlink_to(self.db)
        out = io.StringIO()
        self.assertEqual(cli.main(['--db', str(alias), *flags], stdout=out), 2)
        small = self.root / 'small.sqlite'
        fixture(small, n=16)
        out = io.StringIO()
        self.assertEqual(cli.main(['--db', str(small), *flags], stdout=out), 2)
        self.assertEqual(json.loads(out.getvalue())['status'], 'UNAVAILABLE')
        out = io.StringIO()
        with patch.object(cli, 'run_db', return_value={'metric': float('nan')}):
            self.assertEqual(cli.main(['--db', str(self.db), *flags], stdout=out), 2)
        self.assertEqual(json.loads(out.getvalue())['status'], 'UNAVAILABLE')

    def test_invalid_step_values_rejected_before_read(self):
        for steps in (True, -1, 401, 1.5):
            with self.subTest(steps=steps), self.assertRaises(ValueError):
                cli.run_db(self.db, steps=steps)


if __name__ == '__main__':
    unittest.main()
