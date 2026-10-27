"""Actual V13 Operator.run explicit SHADOW probe bridge, never auto-invoked."""
import hashlib
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

from v13.operator import Operator
from v13.world_jepa_shadow_probe import probe_checkpoint
from v13.world_jepa_slots import SlotWorldJEPA
from tests.test_world_jepa_slots import world, S

PROV = {'cohort_sha256': 'e' * 64, 'source_sha256': 'f' * 64}


class WorldConsoleShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        X, A, X2 = world(80, np.random.default_rng(33))
        cls.request = {'before': X[0].reshape(S, 2).tolist(),
                       'actions': A[0].tolist(),
                       'after': X2[0].reshape(S, 2).tolist()}
        m = SlotWorldJEPA(S, seed=9, ensemble=2).fit(X, A, X2, steps=35)
        m.calibrate(X[60:], A[60:], X2[60:])
        cls.ckpt = cls.base / 'slot.npz'
        cls.sha = m.save(cls.ckpt, provenance=PROV)['sha256']
        cls.prov_path = cls.base / 'provenance.json'
        cls.input_path = cls.base / 'observation.json'
        cls.prov_path.write_text(json.dumps(PROV))
        cls.input_path.write_text(json.dumps(cls.request))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        world_state = SimpleNamespace(world_state=lambda: {'world': 'unchanged'})
        self.fake = SimpleNamespace(store=object(), world=world_state)
        self.operator = Operator(self.fake)

    def command(self, sha=None):
        args = [':world', 'shadow', str(self.ckpt), sha or self.sha,
                str(self.prov_path), str(self.input_path)]
        return ' '.join(shlex.quote(s) for s in args)

    def test_existing_world_status_unchanged(self):
        self.assertEqual(json.loads(self.operator.run(':world')), {'world': 'unchanged'})

    def test_explicit_tty_shadow_matches_direct_checkpoint_probe(self):
        paths = [self.ckpt, self.prov_path, self.input_path]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        result = json.loads(self.operator.run(self.command()))
        direct = probe_checkpoint(self.ckpt, self.sha, PROV, self.request)
        self.assertEqual(result, direct)
        self.assertEqual(result['mode'], 'SHADOW_ONLY')
        self.assertEqual(result['authority'], 0)
        self.assertFalse(result['action_executed'])
        self.assertFalse(result['learning_performed'])
        self.assertTrue(result['after_supplied'])
        self.assertFalse(result['after_verified'])
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])

    def test_non_operator_origin_and_wrong_digest_denied(self):
        with self.assertRaises(ValueError):
            self.operator.run(self.command(), origin='MODEL_OUTPUT')
        with self.assertRaises(ValueError):
            self.operator.run(self.command('0' * 64))

    def test_wrong_count_and_unknown_world_command_denied(self):
        with self.assertRaises(ValueError):
            self.operator.run(':world shadow')
        with self.assertRaises(ValueError):
            self.operator.run(':world unrelated')
        with self.assertRaises(ValueError):
            self.operator.run(':world shadow ' + str(self.ckpt))

    def test_help_mentions_explicit_shadow_and_no_authority(self):
        help_text = self.operator.run(':help')
        self.assertIn(':world shadow', help_text)
        self.assertIn('SHADOW', help_text)


if __name__ == '__main__':
    unittest.main()
