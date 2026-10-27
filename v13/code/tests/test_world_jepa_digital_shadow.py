"""Software-only digital World-JEPA SHADOW bridge contracts."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scripts import world_jepa_digital_shadow as d
from v13 import world_model as wm
from v13 import world_jepa as wj


class DigitalShadowTests(unittest.TestCase):
    def setUp(self):
        self.rows = d.synthetic_fixture(64)

    def test_observed_pre_post_packet_and_train_only_partition(self):
        data = d.make_dataset(self.rows)
        self.assertEqual(data['X'].shape, (64, 8))
        self.assertEqual(data['X2'].shape, (64, 8))
        self.assertEqual(data['A'].shape, (64, 4))
        self.assertEqual(data['Y'].shape, (64, 3))
        self.assertTrue(np.array_equal(data['X'][:, 4:], np.zeros((64, 4))))
        self.assertTrue(np.array_equal(data['X2'][:, :4], data['X'][:, :4]))
        self.assertTrue(np.array_equal(data['X2'][:, 4:7], data['Y']))
        self.assertTrue(np.array_equal(data['X2'][:, 7], np.ones(64)))
        self.assertTrue(np.array_equal(data['A'].sum(1), np.ones(64)))
        self.assertTrue(np.array_equal(np.argmax(data['A'], axis=1), data['action_index']))
        self.assertEqual((len(data['train']), len(data['heldout'])), (47, 17))
        self.assertFalse(set(data['train']) & set(data['heldout']))
        self.assertEqual(data['counts'], {a: 16 for a in wm.ACTIONS})
        self.assertEqual(data['source_sha256'], d.make_dataset(d.synthetic_fixture(64))['source_sha256'])

    def test_malformed_or_duplicate_observations_fail_closed(self):
        def invalid(mutator):
            rows = copy.deepcopy(self.rows)
            mutator(rows)
            with self.assertRaisesRegex(ValueError, 'Invalid|Duplicate|Out-of-domain'):
                d.make_dataset(rows)
        invalid(lambda r: r[1].update(action_id=r[0]['action_id']))
        invalid(lambda r: r[0].update(a='other'))
        invalid(lambda r: r[0]['s'].__setitem__(0, float('nan')))
        invalid(lambda r: r[0]['s'].__setitem__(1, 1.5))
        invalid(lambda r: r[0]['y'].__setitem__(0, -1.))
        invalid(lambda r: r[0]['y'].__setitem__(1, .5))
        invalid(lambda r: r[0]['y'].__setitem__(1, True))
        invalid(lambda r: r[0].update(s=np.array(1.)))
        invalid(lambda r: r[0].update(action_id=''))
        with self.assertRaisesRegex(ValueError, 'count'):
            d.make_dataset(self.rows[:31])

    def test_readout_uses_only_training_targets_and_wrong_action(self):
        data = d.make_dataset(self.rows)
        class Fake:
            def __init__(self):
                self.latent_inputs = []
                self.predict_inputs = []
            def latent(self, X, target=True):
                self.latent_inputs.append((X.copy(), target))
                return np.zeros((len(X), wj.Z))
            def predict(self, X, A):
                self.predict_inputs.append((X.copy(), A.copy()))
                return np.zeros((len(X), wj.Z)), np.zeros(len(X))
        model = Fake()
        score = d.score_fitted(model, data)
        self.assertEqual(len(model.latent_inputs), 1)
        self.assertTrue(model.latent_inputs[0][1])
        self.assertTrue(np.array_equal(model.latent_inputs[0][0],
                                       data['X2'][data['train']]))
        self.assertEqual(len(model.predict_inputs), 2)
        self.assertTrue(np.array_equal(model.predict_inputs[0][0],
                                       data['X'][data['heldout']]))
        wrong = np.eye(4)[(data['action_index'][data['heldout']]+1) % 4]
        self.assertTrue(np.array_equal(model.predict_inputs[1][1], wrong))
        self.assertIn('jepa_readout_mae', score)
        self.assertTrue(np.isfinite(score['heldout_mean_spread']))

    def test_ridge_and_metrics_reject_nonfinite(self):
        X = np.c_[np.ones(4), np.arange(4)]
        Y = np.c_[np.arange(4), np.arange(4), np.arange(4)]
        W = d._ridge(X, Y, .1)
        self.assertEqual(W.shape, (2, 3))
        self.assertTrue(np.isfinite(W).all())
        metrics = d._mae(Y, Y)
        self.assertEqual(metrics['pooled'], 0.)
        self.assertEqual(set(metrics), {'log_duration', 'success', 'log_output_chars', 'pooled'})
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            d._ridge(X, np.full((4, 3), np.nan), .1)
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            d._mae(Y, Y[:, :2])

    def test_store_adapter_reads_only_existing_world_model_transitions(self):
        class Store:
            def set_state(self, *args): raise AssertionError('must not write')
            def log(self, *args): raise AssertionError('must not write')
        store = Store()
        sentinel = {'scope': 'mock-only'}
        with patch.object(wm, 'transitions', return_value=self.rows) as read:
            with patch.object(d, 'run_transitions', return_value=sentinel) as run:
                self.assertIs(d.run_store(store), sentinel)
                read.assert_called_once_with(store)
                run.assert_called_once_with(self.rows)

    def test_run_trains_only_on_frozen_training_partition(self):
        data = d.make_dataset(self.rows)
        with patch.object(wj.WorldJEPA, 'fit', autospec=True) as fit:
            fit.side_effect = lambda model, X, A, X2, steps: model
            with patch.object(d, 'score_fitted', return_value={'software_only': True}):
                result = d.run_transitions(self.rows)
        self.assertEqual(len(fit.call_args_list), len(d.SEEDS))
        for call in fit.call_args_list:
            self.assertEqual(call.kwargs['steps'], d.STEPS)
            np.testing.assert_array_equal(call.args[1], data['X'][data['train']])
            np.testing.assert_array_equal(call.args[2], data['A'][data['train']])
            np.testing.assert_array_equal(call.args[3], data['X2'][data['train']])
        self.assertEqual(result['heldout_n'], len(data['heldout']))

    def test_synthetic_smoke_uses_real_model_without_training_or_authority(self):
        # steps=0 only in this software test; not a registered 400-step measurement.
        with patch.object(d, 'STEPS', 0):
            report = d.run_transitions(self.rows)
        self.assertEqual(report['n'], 64)
        self.assertEqual(report['train_n'], 47)
        self.assertEqual(report['heldout_n'], 17)
        self.assertEqual(len(report['per_seed']), 2)
        self.assertFalse(report['utility_proven'])
        self.assertFalse(report['runtime_wired'])
        self.assertFalse(report['model_weights_persisted'])
        self.assertEqual(report['negative_gates_unchanged']['jepa_weight'], 0)
        self.assertNotIn('synthetic-0', json.dumps(report))
        self.assertNotIn('action_id', json.dumps(report))
        for arm in report['per_seed']:
            self.assertTrue(np.isfinite(arm['jepa_readout_mae']['pooled']))
            self.assertTrue(np.isfinite(arm['wrong_action_mae']['pooled']))

    def test_public_cli_requires_explicit_synthetic_mode_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'report.json'
            with self.assertRaisesRegex(ValueError, 'Only explicit'):
                d.main(['--out', str(p)])
            self.assertFalse(p.exists())
            p.write_text('existing')
            with self.assertRaisesRegex(ValueError, 'Refusing'):
                d.main(['--synthetic-smoke', '--out', str(p)])
            self.assertEqual(p.read_text(), 'existing')


if __name__ == '__main__':
    unittest.main()
