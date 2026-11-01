"""Affine action-JEPA: gradient, disjoint authority and real saved consumer checks."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_jepa_objective as aj


class ActionObjectiveTests(unittest.TestCase):
    def arrays(self):
        rng = np.random.default_rng(8)
        x, y = rng.normal(size=(10, 5)), rng.normal(size=(10, 5))
        a = np.arange(10) % 2
        p = rng.normal(size=(5, 3)) * .03  # exercise the variance floor too
        q = rng.normal(size=(2, 3, 3))
        b = rng.normal(size=(2, 3))
        return x, y, a, p, q, b, p + .1, p.copy()

    def test_analytic_all_parameter_gradients_and_stop_gradient(self):
        args = self.arrays()
        copies = [v.copy() for v in args]
        self.assertLess(aj.gradient_check(*args), 1e-7)
        for left, right in zip(args, copies):
            np.testing.assert_array_equal(left, right)

    def test_bias_learns_constant_action_effect_without_target_gradient(self):
        rng = np.random.default_rng(19)
        x = rng.normal(size=(80, 3))
        a = np.arange(80) % 2
        offsets = np.asarray([[2., 0, 0], [-2., 0, 0]])
        y = x + offsets[a]
        p = np.eye(3)
        initial = (p, np.repeat(p[None], 2, 0), np.zeros((2, 3)), p.copy())
        cfg = self.config() | {'dim': 3, 'steps': 300, 'lr': .1, 'ema_decay': .999}
        bias, _ = aj.optimize(x, y, a, initial, cfg)
        linear, _ = aj.optimize(x, y, a, initial, cfg, use_bias=False)
        mean_delta = offsets
        b = aj.evaluate(x, y, a, bias, p, mean_delta)
        n = aj.evaluate(x, y, a, linear, p, mean_delta)
        self.assertLess(b['fixed_target_prediction_mse'], n['fixed_target_prediction_mse'] / 4)
        self.assertGreater(np.linalg.norm(bias[2]), 1)
        np.testing.assert_array_equal(initial[3], p)

    def config(self):
        return {'dim': 3, 'steps': 80, 'lr': .05, 'max_update_norm': .1,
                'ema_decay': .99, 'retention_max_delta': 0., 'seed': 13}

    def fixture(self, root):
        encoder = root / 'encoder.json'
        encoder.write_text('{"test_fixture_encoder": true}')
        bindings = {'encoder': {'path': encoder.name, 'sha256': aj.digest(encoder)}}
        rows = []
        rng = np.random.default_rng(13)
        for part in aj.PARTITIONS:
            source = root / (part + '.txt')
            source.write_text('Explicit synthetic test source: ' + part)
            bindings[part] = {'path': source.name, 'sha256': aj.digest(source)}
            for i in range(16):
                x = rng.normal(size=4)
                a = i % 2
                rows.append({'row_id': part + str(i), 'episode_id': part + str(i),
                             'source_ids': [part], 'partition': part, 'action': str(a),
                             'context_state': x.tolist(), 'future_state': (x + (a * 2 - 1)).tolist()})
        doc = {'schema': aj.SCHEMA, 'provenance_kind': 'test_fixture', 'bindings': bindings, 'rows': rows}
        path = root / 'dataset.json'
        path.write_text(json.dumps(doc))
        return path, doc

    def test_full_training_saved_hypothesis_consumer_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, doc = self.fixture(root)
            one = aj.train(path, root / 'one', self.config())
            two = aj.train(path, root / 'two', self.config())
            self.assertTrue(one['gates']['analytic_gradient'])
            self.assertTrue(one['gates']['deterministic'])
            self.assertTrue(one['gates']['checkpoint_reload'])
            self.assertFalse(one['candidate_gate_pass'])
            self.assertFalse(one['gates']['observed_input_declared'])
            self.assertEqual(one['after'], two['after'])
            result = aj.predict(root / 'one/candidate.npz', root / 'one/metrics.json',
                                [doc['rows'][0]['context_state']], '0')
            self.assertFalse(result['receiver_injection'])
            self.assertFalse(result['future_observed'])
            self.assertEqual(np.asarray(result['predicted_future_latents']).shape, (1, 3))
            with self.assertRaisesRegex(ValueError, 'Unknown'):
                aj.predict(root / 'one/candidate.npz', root / 'one/metrics.json', [[0, 0, 0, 0]], 'unknown')
            with (root / 'one/candidate.npz').open('ab') as f:
                f.write(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'Candidate bytes'):
                aj.predict(root / 'one/candidate.npz', root / 'one/metrics.json', [[0, 0, 0, 0]], '0')

    def test_source_alias_same_bytes_cannot_enter_holdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, doc = self.fixture(Path(tmp))
            doc['bindings']['calibration'] = copy.deepcopy(doc['bindings']['train'])
            path.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, 'overlap'):
                aj.load_dataset(path)

    def test_corrupt_input_bindings_and_missing_action_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, doc = self.fixture(root)
            (root / 'train.txt').write_text('Changed after capture')
            with self.assertRaisesRegex(ValueError, 'binding mismatch'):
                aj.load_dataset(path)
            path, doc = self.fixture(root)
            doc['rows'] = [r for r in doc['rows'] if not (r['partition'] == 'test' and r['action'] == '1')]
            path.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, 'two pairs'):
                aj.load_dataset(path)

    def test_fixed_metric_detects_collapsed_moving_target(self):
        x, y, a, p, q, b, target, anchor = self.arrays()
        zero = np.zeros_like(p)
        state = (zero, q, np.zeros_like(b), zero)
        out = aj.evaluate(x, y, a, state, anchor, np.zeros_like(b))
        self.assertEqual(out['ema_training_space_mse'], 0.)
        self.assertGreater(out['fixed_target_prediction_mse'], 0.)
        self.assertEqual(out['target_std_ratio'], 0.)

    def test_holdout_targets_do_not_change_fit_or_mean_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, doc = self.fixture(root)
            aj.train(path, root / 'one', self.config())
            for row in doc['rows']:
                if row['partition'] != 'train':
                    row['future_state'] = [v + 100 for v in row['future_state']]
            path.write_text(json.dumps(doc))
            aj.train(path, root / 'two', self.config())
            with np.load(root / 'one/candidate.npz', allow_pickle=False) as one, np.load(root / 'two/candidate.npz', allow_pickle=False) as two:
                for name in ('projector', 'predictor', 'bias', 'target'):
                    np.testing.assert_array_equal(one[name], two[name])


if __name__ == '__main__':
    unittest.main()
