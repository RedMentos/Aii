"""Run280 RED-first: STEP1 body-free proof must also isolate committed AG0 slots.

Uses actual Runtime/ModelManager/BodyFabric/SQLite with tiny synthetic model
file *paths only*. No native inference, model download or gate promotion.
"""
import hashlib
import inspect
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import proofs
from v13.agi.slots import ModelSlots
from v13.common import Unavailable


class Step1BodySlotIsolationRun280(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.paths = {}
        for role, key in [('B1_DETAIL', 'body'), ('B2_GIST', 'gist'),
                          ('C3_LANGUAGE', 'language')]:
            folder = self.home / 'models' / key
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / 'synthetic.gguf'
            payload = b'GGUF_RUN280_PATH_ONLY_' + role.encode()
            path.write_bytes(payload)
            rel = str(path.relative_to(self.home))
            entry = {
                'model_id': 'RUN280_PATH_ONLY', 'exact_revision': 'RUN280_' + role,
                'license_id': 'TEST_SYNTHETIC_NO_WEIGHTS', 'download_complete': True,
                'main_file': 'synthetic.gguf',
                'files': {'synthetic.gguf': {'path': rel, 'size': len(payload),
                                           'sha256': hashlib.sha256(payload).hexdigest()}},
            }
            self.r.models.installed[key] = entry
            self.r.bodies.slots.install(role, ModelSlots.from_installed(entry))
            self.paths[role] = path
        self.r.models.save()

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_manifest_only_removal_is_insufficient_because_slots_still_route(self):
        original = self.r.models.installed.pop('body')
        self.r.models.save()
        # RED mechanism: even without a manifest, committed slot still exposes B1.
        self.assertEqual(self.r.models.path_for('B1_DETAIL'), self.paths['B1_DETAIL'])
        self.r.models.installed['body'] = original
        self.r.models.save()

    def test_step1_mask_removes_both_body_access_paths_and_keeps_c3(self):
        saved = proofs._mask_step1_bodies(self.r)
        self.assertEqual(self.r.models.path_for('C3_LANGUAGE'), self.paths['C3_LANGUAGE'])
        self.assertNotIn('body', self.r.models.installed)
        self.assertNotIn('gist', self.r.models.installed)
        for role in ('B1_DETAIL', 'B2_GIST'):
            with self.subTest(role=role), self.assertRaises(Unavailable):
                self.r.models.path_for(role)
            self.assertNotIn(role, self.r.bodies.slots.box.load()[0]['slots'])
        proofs._restore_step1_bodies(self.r, saved)
        for role in ('B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE'):
            self.assertEqual(self.r.models.path_for(role), self.paths[role])

    def test_mask_survives_runtime_restart_and_restores_original_slots(self):
        before = self.r.bodies.slots.box.load()[0]['slots']
        saved = proofs._mask_step1_bodies(self.r)
        self.r.close()
        self.r = Runtime(self.home)
        for role in ('B1_DETAIL', 'B2_GIST'):
            with self.subTest(role=role), self.assertRaises(Unavailable):
                self.r.models.path_for(role)
        self.assertEqual(self.r.models.path_for('C3_LANGUAGE'), self.paths['C3_LANGUAGE'])
        proofs._restore_step1_bodies(self.r, saved)
        after = self.r.bodies.slots.box.load()[0]['slots']
        self.assertEqual(after, before)
        for role in ('B1_DETAIL', 'B2_GIST'):
            self.assertEqual(self.r.models.path_for(role), self.paths[role])

    def test_both_native_step1_proofs_use_slot_isolation_not_manifest_only(self):
        for name in ('probe_jef_modes', 'probe_step12'):
            source = inspect.getsource(getattr(proofs, name))
            with self.subTest(probe=name):
                self.assertIn('_mask_step1_bodies(runtime)', source)
                self.assertIn('_restore_step1_bodies(runtime,', source)


if __name__ == '__main__':
    unittest.main()
