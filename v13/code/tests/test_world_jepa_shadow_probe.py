"""Z12c manual operator SHADOW probe: no automatic activation or factual authority."""
import json
import shlex
import tempfile
import unittest
from pathlib import Path

import numpy as np
from v13.operator import Operator
from v13.runtime import Runtime
from v13.world_jepa_slots import SlotWorldJEPA
from tests.test_world_jepa_slots import world, S

PROV = {'cohort_sha256': 'a'*64, 'source_sha256': 'b'*64}


class ManualShadowProbe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.op = Operator(self.r)
        self.root = self.home / 'checkpoints' / 'world_jepa'
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'alder-shadow.npz'
        self.X, self.A, self.X2 = world(60, np.random.default_rng(13))
        self.m = SlotWorldJEPA(S, seed=17, ensemble=2).fit(
            self.X, self.A, self.X2, steps=30, log_every=10).calibrate(
                self.X[40:], self.A[40:], self.X2[40:])
        self.sha = self.m.save(self.path, provenance=PROV)['sha256']

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.tmp.cleanup()

    def cmd(self, text):
        return json.loads(self.op.run(':world shadow ' + text))

    def load(self):
        return self.cmd('load alder-shadow.npz ' + self.sha + ' ' +
                        PROV['cohort_sha256'] + ' ' + PROV['source_sha256'])

    def query(self, X=None, A=None):
        x = (self.X[:2] if X is None else X).tolist() if isinstance(
            self.X[:2] if X is None else X, np.ndarray) else X
        a = (self.A[:2] if A is None else A).tolist() if isinstance(
            self.A[:2] if A is None else A, np.ndarray) else A
        return self.cmd('predict ' + shlex.quote(json.dumps(x)) + ' ' +
                        shlex.quote(json.dumps(a)))

    def test_explicit_load_predict_matches_direct_model_and_is_shadow_only(self):
        self.assertEqual(self.cmd('status')['status'], 'UNBOUND')
        actions_before = self.r.store.rows('SELECT id FROM actions')
        self.assertEqual(self.load()['status'], 'VERIFIED_SHADOW_BOUND')
        result = self.query()
        self.assertEqual(result['status'], 'MODEL_SIMULATION_ONLY')
        self.assertFalse(result['truth_authority'])
        self.assertFalse(result['automatic_turn_activation'])
        p, spread = self.m.predict(self.X[:2], self.A[:2])
        conf, labels = self.m.confidence(self.X[:2], self.A[:2])
        np.testing.assert_array_equal(result['prediction_latent'], p)
        np.testing.assert_array_equal(result['spread'], spread)
        np.testing.assert_array_equal(result['confidence'], conf)
        self.assertEqual(result['labels'], labels)
        self.assertEqual(self.r.store.rows('SELECT id FROM actions'), actions_before)

    def test_binding_survives_runtime_restart_but_requires_fresh_digest(self):
        self.load()
        before = self.query()
        self.r.close()
        self.r = Runtime(self.home)
        self.op = Operator(self.r)
        self.assertEqual(self.cmd('status')['status'], 'BOUND_UNVERIFIED')
        after = self.query()
        self.assertEqual(before['prediction_latent'], after['prediction_latent'])
        self.assertEqual(before['confidence'], after['confidence'])

    def test_tamper_after_binding_fails_closed(self):
        self.load()
        self.path.write_bytes(self.path.read_bytes() + b'!')
        with self.assertRaises(ValueError):
            self.query()

    def test_wrong_hash_and_provenance_do_not_create_binding(self):
        with self.assertRaises(ValueError):
            self.cmd('load alder-shadow.npz ' + '0'*64 + ' ' +
                     PROV['cohort_sha256'] + ' ' + PROV['source_sha256'])
        with self.assertRaises(ValueError):
            self.cmd('load alder-shadow.npz ' + self.sha + ' ' +
                     'f'*64 + ' ' + PROV['source_sha256'])
        self.assertEqual(self.cmd('status')['status'], 'UNBOUND')

    def test_path_traversal_and_symlink_refused(self):
        with self.assertRaises(ValueError):
            self.cmd('load ../alder-shadow.npz ' + self.sha + ' ' +
                     PROV['cohort_sha256'] + ' ' + PROV['source_sha256'])
        (self.root / 'link.npz').symlink_to(self.path)
        with self.assertRaises(ValueError):
            self.cmd('load link.npz ' + self.sha + ' ' +
                     PROV['cohort_sha256'] + ' ' + PROV['source_sha256'])

    def test_invalid_input_shape_nonfinite_and_actions_fail_closed(self):
        self.load()
        with self.assertRaises(ValueError):
            self.query(X=self.X[:2, :-1])
        with self.assertRaises(ValueError):
            self.query(X=[[float('nan')]*self.X.shape[1]]*2)
        with self.assertRaises(ValueError):
            self.query(A=np.zeros_like(self.A[:2]))
        with self.assertRaises(ValueError):
            self.query(X=np.repeat(self.X[:1], 5, axis=0), A=np.repeat(self.A[:1], 5, axis=0))
        with self.assertRaises(ValueError):
            self.cmd('predict ' + shlex.quote('{"not":"array"}') + ' ' +
                     shlex.quote(json.dumps(self.A[:2].tolist())))

    def test_unload_preserves_checkpoint_and_no_model_origin_command(self):
        self.load()
        with self.assertRaises(ValueError):
            self.op.run(':world shadow status', origin='MODEL')
        self.assertEqual(self.cmd('unload')['status'], 'UNBOUND')
        self.assertTrue(self.path.exists())
        with self.assertRaises(ValueError):
            self.query()

    def test_world_without_subcommand_remains_existing_state(self):
        existing = self.r.world.world_state()
        self.assertEqual(json.loads(self.op.run(':world')), existing)


if __name__ == '__main__':
    unittest.main()
