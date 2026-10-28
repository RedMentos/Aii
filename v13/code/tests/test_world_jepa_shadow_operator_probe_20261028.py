"""Offline private World-JEPA SHADOW operator probe: input contract and no authority."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts import world_jepa_shadow_operator_probe as cli
from v13 import world_jepa as wj
from v13 import world_jepa_shadow_checkpoint as cp


class WorldJepaOperatorProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(20261028)
        cls.X = rng.normal(size=(80, 8))
        cls.A = np.eye(4)[rng.integers(0, 4, size=80)]
        cls.X2 = cls.X.copy()
        cls.X2[:, :4] += .2 * cls.A
        cls.model = wj.WorldJEPA(seed=7, ensemble=2).fit(
            cls.X, cls.A, cls.X2, steps=20, log_every=10)
        cls.source = hashlib.sha256(b'operator synthetic source').hexdigest()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checkpoint = self.root / 'fitted.npz'
        self.record = cp.save(self.model, self.checkpoint, self.source)
        self.input = self.root / 'input.json'
        self.payload = {
            'observations': self.X[:3].tolist(),
            'actions': self.A[:3].tolist(),
        }
        self.input.write_text(json.dumps(self.payload), encoding='utf-8')

    def test_cli_exact_predictions_confidence_and_zero_authority(self):
        output = io.StringIO()
        rc = cli.main([
            '--checkpoint', str(self.checkpoint),
            '--source-sha256', self.source,
            '--checkpoint-sha256', self.record['sha256'],
            '--input-json', str(self.input)], stdout=output)
        self.assertEqual(rc, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report['scope'], 'PRIVATE_READ_ONLY_SHADOW_INFERENCE')
        self.assertFalse(report['source_bytes_verified_by_cli'])
        self.assertTrue(report['checkpoint_bytes_verified'])
        self.assertFalse(report['runtime_wired'])
        self.assertFalse(report['training_resume'])
        self.assertFalse(report['tool_authority'])
        self.assertEqual(report['age_authority'], 0)
        self.assertEqual(report['rows'], 3)
        expected, spread = self.model.predict(self.X[:3], self.A[:3])
        np.testing.assert_array_equal(report['predicted_next_latent'], expected)
        np.testing.assert_array_equal(report['ensemble_spread'], spread)
        np.testing.assert_array_equal(report['ood'], self.model.ood(self.X[:3]))
        conf, labels = self.model.confidence(self.X[:3], self.A[:3])
        np.testing.assert_array_equal(report['confidence'], conf)
        self.assertEqual(report['labels'], labels)
        self.assertNotIn('observations', report)
        self.assertNotIn('actions', report)

    def test_wrong_pins_and_bad_shapes_are_refused(self):
        with self.assertRaises(ValueError):
            cli.infer(self.checkpoint, '0'*64, self.record['sha256'], self.payload)
        with self.assertRaises(ValueError):
            cli.infer(self.checkpoint, self.source, 'f'*64, self.payload)
        for payload in (
            {'observations': [], 'actions': []},
            {'observations': [[1.]], 'actions': [[1., 0., 0., 0.]]},
            {'observations': self.X[:3].tolist(), 'actions': self.A[:2].tolist()},
            {'observations': self.X[:3].tolist(), 'actions': [[.5,.5,0.,0.]]*3},
            {'observations': self.X[:3].tolist(), 'actions': [[0.,0.,0.,0.]]*3},
            {'observations': self.X[:3].tolist(), 'actions': [[1.,0.,0.,0.]]*3,
             'extra': True},
        ):
            with self.subTest(payload=str(payload)[:30]), self.assertRaises(ValueError):
                cli.infer(self.checkpoint, self.source, self.record['sha256'], payload)

    def test_nonfinite_boolean_huge_integer_and_duplicate_json_rejected(self):
        for bad in (float('nan'), float('inf'), True, 10**400):
            payload = dict(self.payload)
            payload['observations'] = [list(self.payload['observations'][0])]
            payload['actions'] = [list(self.payload['actions'][0])]
            payload['observations'][0][0] = bad
            with self.subTest(bad=str(bad)[:12]), self.assertRaises(ValueError):
                cli.infer(self.checkpoint, self.source, self.record['sha256'], payload)
        self.input.write_text('{"observations":[],"observations":[],"actions":[]}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            cli._read_private_json(self.input)
        self.input.write_text('{"observations":[[NaN]],"actions":[[1]]}')
        with self.assertRaisesRegex(ValueError, 'Nonfinite'):
            cli._read_private_json(self.input)

    def test_oversized_and_symlink_input_rejected(self):
        self.input.write_bytes(b' ' * (cli.MAX_INPUT_BYTES + 1))
        with self.assertRaises(ValueError):
            cli._read_private_json(self.input)
        alias = self.root / 'alias.json'
        alias.symlink_to(self.input)
        with self.assertRaises(OSError):
            cli._read_private_json(alias)


if __name__ == '__main__':
    unittest.main()
