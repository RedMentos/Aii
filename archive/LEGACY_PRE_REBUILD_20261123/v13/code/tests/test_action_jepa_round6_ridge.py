"""Round-6 mean-delta + ridge residual candidate on explicit synthetic test data only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_jepa_objective as aj
import action_jepa_round6_ridge as r6
import tests.test_action_jepa_objective as objective_tests


def fixture(root, gain):
    """future = x + action offset + gain * context-dependent term; 40 rows per partition."""
    encoder = root / 'encoder.json'
    encoder.write_text('{"test_fixture_encoder": true}')
    bindings = {'encoder': {'path': encoder.name, 'sha256': aj.digest(encoder)}}
    rows, rng = [], np.random.default_rng(5)
    mix = rng.normal(size=(2, 6, 6))
    for part in aj.PARTITIONS:
        source = root / (part + '.txt')
        source.write_text('Explicit synthetic test source: ' + part)
        bindings[part] = {'path': source.name, 'sha256': aj.digest(source)}
        for i in range(40):
            x, a = rng.normal(size=6), i % 2
            y = x + (a * 2 - 1) + gain * np.tanh(x @ mix[a]) + .01 * rng.normal(size=6)
            rows.append({'row_id': part + str(i), 'episode_id': part + str(i), 'source_ids': [part],
                         'partition': part, 'action': str(a), 'context_state': x.tolist(), 'future_state': y.tolist()})
    doc = {'schema': aj.SCHEMA, 'provenance_kind': 'test_fixture', 'bindings': bindings, 'rows': rows}
    path = root / 'dataset.json'
    path.write_text(json.dumps(doc))
    return path, doc


class Round6RidgeTests(unittest.TestCase):
    def cfg(self, arm):
        return {'dim': 3, 'seed': 13, 'arm': arm, 'scales': r6.SCALES, 'retention_max_delta': 0.}

    def test_scores_match_objective_evaluate_for_mean_delta_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = objective_tests.ActionObjectiveTests().fixture(Path(tmp))
            _, x, y, a, actions, masks = aj.load_dataset(path)
            state, control, *_ = r6.fit(x, y, a, masks, len(actions), self.cfg('proj'))
            p, md = control['p'], control['mean_delta']
            affine = (p, np.repeat(np.eye(3)[None], len(actions), 0), md, p)
            m = masks['test']
            ours = r6.score(x[m], y[m], a[m], r6.predict_state(x[m], a[m], control), p, md, len(actions))
            theirs = aj.evaluate(x[m], y[m], a[m], affine, p, md)
            for key in ('fixed_target_prediction_mse', 'copy_mse', 'mean_delta_mse', 'shuffled_target_mse', 'per_action'):
                self.assertEqual(json.dumps(ours[key]), json.dumps(theirs[key]))

    def test_context_dependent_effect_beats_mean_delta_and_passes_gates_except_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, doc = fixture(root, 1.)
            report = r6.train(path, root / 'out', self.cfg('full'))
            for part in ('calibration', 'test'):
                self.assertLess(report['after'][part]['fixed_target_prediction_mse'], .9 * report['after'][part]['mean_delta_mse'])
            self.assertTrue(all(v for k, v in report['gates'].items() if k != 'observed_input_declared'))
            self.assertFalse(report['candidate_gate_pass'])
            self.assertNotIn('inf', report['chosen_lambda_scale'].values())
            for part, s in report['before'].items():
                self.assertAlmostEqual(s['fixed_target_prediction_mse'], s['mean_delta_mse'], places=12)
            again = r6.train(path, root / 'again', self.cfg('full'))
            self.assertEqual(report['after'], again['after'])
            out = r6.predict(root / 'out/candidate.npz', root / 'out/metrics.json', [doc['rows'][0]['context_state']], '1')
            self.assertEqual(np.asarray(out['predicted_future_latents']).shape, (1, 3))
            self.assertFalse(out['receiver_injection'])
            with (root / 'out/candidate.npz').open('ab') as f:
                f.write(b'x')
            with self.assertRaisesRegex(ValueError, 'Candidate bytes'):
                r6.predict(root / 'out/candidate.npz', root / 'out/metrics.json', [[0] * 6], '1')

    def test_constant_effect_cannot_pass_predictive_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, _ = fixture(root, 0.)
            for arm in ('full', 'proj'):
                report = r6.train(path, root / arm, self.cfg(arm))
                self.assertFalse(report['gates']['predictive_gain_over_controls'])
                self.assertEqual(report['receiver_authority'], 0)

    def test_holdout_targets_do_not_change_fit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = fixture(Path(tmp), 1.)
            _, x, y, a, actions, masks = aj.load_dataset(path)
            y2 = y.copy()
            y2[masks['test']] += 7.
            s1 = r6.fit(x, y, a, masks, len(actions), self.cfg('full'))[0]
            s2 = r6.fit(x, y2, a, masks, len(actions), self.cfg('full'))[0]
            for k in ('mean_delta', 'centre', 'weight'):
                self.assertTrue(np.array_equal(s1[k], s2[k]))

    def test_bad_configuration_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, _ = fixture(root, 1.)
            with self.assertRaisesRegex(ValueError, 'Preregistered'):
                r6.train(path, root / 'x', dict(self.cfg('full'), retention_max_delta=.1))
            with self.assertRaisesRegex(ValueError, 'Preregistered'):
                r6.train(path, root / 'y', dict(self.cfg('other')))


if __name__ == '__main__':
    unittest.main()
