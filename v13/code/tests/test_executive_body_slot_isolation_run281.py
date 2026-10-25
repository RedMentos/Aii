"""Run281 RED-first: actual native executive acceptance must truly remove B paths.

Software test: real Runtime/RunnerPool/ModelSlots with synthetic path files only.
No native model inference, no model weights, no acceptance gate promotion.
"""
import hashlib
import inspect
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.slots import ModelSlots
from v13.proofs import _mask_step1_bodies, _restore_step1_bodies
from v13.common import Unavailable
import integration_executive


class ExecutiveBodySlotIsolationRun281(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.paths = {}
        for role, key in [('B1_DETAIL', 'body'), ('B2_GIST', 'gist'),
                          ('C3_LANGUAGE', 'language')]:
            path = self.home / 'models' / key / 'synthetic.gguf'
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = b'GGUF_RUN281_PATH_ONLY_' + role.encode()
            path.write_bytes(payload)
            entry = {
                'model_id': 'RUN281_PATH_ONLY', 'exact_revision': 'RUN281_' + role,
                'license_id': 'TEST_SYNTHETIC_NO_WEIGHTS', 'download_complete': True,
                'main_file': 'synthetic.gguf',
                'files': {'synthetic.gguf': {'path': str(path.relative_to(self.home)),
                                           'size': len(payload),
                                           'sha256': hashlib.sha256(payload).hexdigest()}},
            }
            self.r.models.installed[key] = entry
            self.r.bodies.slots.install(role, ModelSlots.from_installed(entry))
            self.paths[role] = path
        self.r.models.save()

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_executive_native_script_calls_proven_slot_mask(self):
        source = inspect.getsource(integration_executive.run)
        self.assertIn('_mask_step1_bodies(r)', source)
        self.assertNotIn("r.models.installed.pop('body'", source)
        self.assertNotIn("r.models.installed.pop('gist'", source)

    def test_executive_body_not_required_checks_slots_as_well_as_manifest(self):
        source = inspect.getsource(integration_executive.run)
        self.assertIn("'body_not_required'", source)
        self.assertIn("'body_slot_absent'", source)
        self.assertIn("r.bodies.slots.box.load()", source)

    def test_runner_pool_cannot_access_bodies_after_mask_but_c3_remains(self):
        self.assertEqual(self.r.pool.get('B1_DETAIL').role, 'B1_DETAIL')
        saved = _mask_step1_bodies(self.r)
        for role in ('B1_DETAIL', 'B2_GIST'):
            with self.subTest(role=role), self.assertRaises(Unavailable):
                self.r.pool.get(role)
        self.assertEqual(self.r.pool.get('C3_LANGUAGE').role, 'C3_LANGUAGE')
        self.assertEqual(self.r.pool.pids(), [], 'synthetic paths are never executed')
        _restore_step1_bodies(self.r, saved)
        self.assertEqual(self.r.pool.get('B1_DETAIL').role, 'B1_DETAIL')


if __name__ == '__main__':
    unittest.main()
