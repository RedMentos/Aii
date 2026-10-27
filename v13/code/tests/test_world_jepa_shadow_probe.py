"""Read-only v2 World-JEPA checkpoint consumer: restart and safety contracts."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from v13.world_jepa_slots import SlotWorldJEPA
from v13.world_jepa_shadow_probe import probe_checkpoint, main
from tests.test_world_jepa_slots import S, world

PROV = {'cohort_sha256': 'c' * 64, 'source_sha256': 'd' * 64}


class WorldShadowProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.ckpt = Path(cls.temp.name) / 'shadow.npz'
        cls.X, cls.A, cls.X2 = world(80, np.random.default_rng(17))
        m = SlotWorldJEPA(S, seed=3, ensemble=2).fit(
            cls.X, cls.A, cls.X2, steps=35, log_every=10)
        m.calibrate(cls.X[60:], cls.A[60:], cls.X2[60:])
        cls.sha = m.save(cls.ckpt, provenance=PROV)['sha256']

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def request(self, with_after=True):
        r = {'before': self.X[0].reshape(S, 2).tolist(),
             'actions': self.A[0].tolist()}
        if with_after:
            r['after'] = self.X2[0].reshape(S, 2).tolist()
        return r

    def probe(self, request):
        return probe_checkpoint(self.ckpt, self.sha, PROV, request)

    def test_restart_byte_identical_and_shadow_only(self):
        a, b = self.probe(self.request()), self.probe(self.request())
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(a['schema'], 'V13_Z12C_SHADOW_PROBE_V1')
        self.assertEqual(a['checkpoint_sha256'], self.sha)
        self.assertEqual(a['authority'], 0)
        self.assertEqual(a['mode'], 'SHADOW_ONLY')
        self.assertIs(a['action_executed'], False)
        self.assertIs(a['learning_performed'], False)
        self.assertTrue(a['after_supplied'])
        self.assertFalse(a['after_verified'])
        self.assertEqual(len(a['predicted_next_latent']), S)
        self.assertEqual(len(a['predicted_next_latent'][0]), 8)
        self.assertEqual(len(a['slot_spread']), S)
        self.assertEqual(len(a['slot_errors']), S)
        self.assertGreaterEqual(a['confidence'], 0.)
        self.assertLessEqual(a['confidence'], 1.)
        self.assertIn(a['simulation_label'], ('MODEL_SIMULATION', 'SIMULATION_UNCERTAIN'))
        self.assertTrue(all(np.isfinite(v) for row in a['predicted_next_latent'] for v in row))

    def test_without_after_is_prediction_not_observation(self):
        a = self.probe(self.request(with_after=False))
        self.assertIsNone(a['slot_errors'])
        self.assertFalse(a['after_supplied'])
        self.assertFalse(a['after_verified'])
        self.assertEqual(len(a['slot_spread']), S)

    def test_wrong_digest_and_provenance_fail_closed(self):
        with self.assertRaises(ValueError):
            probe_checkpoint(self.ckpt, '0' * 64, PROV, self.request())
        with self.assertRaises(ValueError):
            probe_checkpoint(self.ckpt, self.sha, {'source_sha256': 'wrong'}, self.request())

    def test_invalid_rows_types_and_actions_rejected(self):
        bad = []
        r = self.request(); r['before'][0][0] = True; bad.append(r)
        r = self.request(); r['before'][0][0] = '1'; bad.append(r)
        r = self.request(); r['before'][0][0] = float('nan'); bad.append(r)
        r = self.request(); r['before'][0].pop(); bad.append(r)
        r = self.request(); r['actions'][0] = [1., 1., 0.]; bad.append(r)
        r = self.request(); r['actions'][0] = [0., 0., 0.]; bad.append(r)
        r = self.request(); r['actions'][0][0] = 0.5; bad.append(r)
        r = self.request(); r['after'][0][1] = float('inf'); bad.append(r)
        for request in bad:
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.probe(request)

    def test_cli_stdout_and_explicit_atomic_output(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            req = base / 'request.json'; prov = base / 'provenance.json'
            req.write_text(json.dumps(self.request()))
            prov.write_text(json.dumps(PROV))
            args = ['--checkpoint', str(self.ckpt), '--sha256', self.sha,
                    '--provenance', str(prov), '--input', str(req)]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(args), 0)
            self.assertEqual(json.loads(out.getvalue()), self.probe(self.request()))
            dst = base / 'result.json'
            self.assertEqual(main(args + ['--output', str(dst)]), 0)
            self.assertEqual(json.loads(dst.read_text()), self.probe(self.request()))
            req.write_text(json.dumps({'before': [], 'actions': []}))
            before = dst.read_bytes()
            with self.assertRaises(ValueError):
                main(args + ['--output', str(dst)])
            self.assertEqual(dst.read_bytes(), before)
            with self.assertRaises(ValueError):
                main(args + ['--output', str(base / 'not-created.json')])
            self.assertFalse((base / 'not-created.json').exists())

    def test_interrupted_atomic_output_preserves_prior_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d); req = base / 'request.json'; prov = base / 'provenance.json'
            dst = base / 'result.json'; dst.write_bytes(b'previous-good-output')
            req.write_text(json.dumps(self.request())); prov.write_text(json.dumps(PROV))
            args = ['--checkpoint', str(self.ckpt), '--sha256', self.sha,
                    '--provenance', str(prov), '--input', str(req), '--output', str(dst)]
            with patch('v13.world_jepa_shadow_probe.atomic_write', side_effect=OSError('simulated write failure')):
                with self.assertRaises(OSError):
                    main(args)
            self.assertEqual(dst.read_bytes(), b'previous-good-output')


if __name__ == '__main__':
    unittest.main()
