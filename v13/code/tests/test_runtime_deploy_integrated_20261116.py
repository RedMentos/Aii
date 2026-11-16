"""Real staged-deploy paths with synthetic data; no Android or native models."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from v13 import runtime_deploy as deploy

CODE = Path(__file__).resolve().parents[1]


class IntegratedRuntimeDeploy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.home = root / 'home'
        (self.home / 'bin').mkdir(parents=True)
        (self.home / 'models').mkdir()
        (self.home / 'data/db').mkdir(parents=True)
        self.launcher = self.home / 'bin/v13'
        self.original_launcher = b'#!/bin/sh\necho old\n'
        self.launcher.write_bytes(self.original_launcher)
        self.model = self.home / 'models/model.gguf'
        self.model.write_bytes(b'GGUF_SYNTHETIC_PRESERVE')
        self.db = self.home / 'data/db/brain.sqlite3'
        self.db.write_bytes(b'SQLITE_SYNTHETIC_PRESERVE')
        self.private = root / 'private'
        self.builds = root / 'builds'
        self.commit = 'a' * 40
        self.checkout = root / 'checkout'
        self.source_mock = mock.patch.object(deploy, '_source',
            return_value=(self.checkout, CODE, self.commit))
        self.stop_mock = mock.patch.object(deploy, '_check_stopped')
        self.source_mock.start()
        self.stop_mock.start()
        self.addCleanup(self.source_mock.stop)
        self.addCleanup(self.stop_mock.stop)

    def install(self):
        return deploy.deploy(self.checkout, home=self.home, private=self.private,
                             builds=self.builds, ci_verified=True)

    def test_real_stage_is_installed_and_record_only_gates_are_retained(self):
        original_runtime = (CODE / 'v13/runtime.py').read_bytes()
        installed = self.install()
        self.assertEqual(installed['status'], 'DEPLOYED')
        target = Path(installed['code'])
        self.assertNotEqual((target / 'v13/runtime.py').read_bytes(), original_runtime)
        self.assertEqual((CODE / 'v13/runtime.py').read_bytes(), original_runtime)
        self.assertTrue((target / deploy.CANON).is_file())
        self.assertEqual(self.model.read_bytes(), b'GGUF_SYNTHETIC_PRESERVE')
        self.assertEqual(self.db.read_bytes(), b'SQLITE_SYNTHETIC_PRESERVE')
        self.assertIn(str(target).encode(), self.launcher.read_bytes())
        marker = json.loads((self.private / deploy.MARKER_NAME).read_text())
        self.assertEqual(marker['stage_manifest_sha256'], deploy._verify_stage(target))
        self.assertFalse(deploy.needs_deploy(self.checkout, home=self.home, private=self.private))
        script = """
from pathlib import Path
from tempfile import TemporaryDirectory
from v13.runtime import Runtime
with TemporaryDirectory() as tmp:
    r = Runtime(Path(tmp))
    try:
        r.sleep.cycle.set_policy('enabled', 'off')
        assert r.cfg['learning_mode'] == 'RECORD_ONLY'
        result = r.online_world_update(limit=1)
        assert result['status'] == 'SKIPPED_RECORD_ONLY', result
        assert not (Path(tmp) / 'online_world' / 'online_predictor.npz').exists()
        result = r.world_jepa_update(steps=1, limit=16, authority='EXPLICIT_HUMAN')
        assert result['status'] == 'SKIPPED_RECORD_ONLY', result
    finally:
        r.close()
"""
        env = dict(os.environ, PYTHONPATH=str(target), PYTHONDONTWRITEBYTECODE='1')
        run = subprocess.run([sys.executable, '-c', script], cwd=target, env=env,
                             capture_output=True, text=True, timeout=45)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_tampered_stage_is_detected_and_previous_launcher_is_retained(self):
        result = self.install()
        installed_launcher = self.launcher.read_bytes()
        target = Path(result['code'])
        runtime = target / 'v13/runtime.py'
        runtime.write_bytes(runtime.read_bytes() + b'\n# unexpected change\n')
        self.assertTrue(deploy.needs_deploy(self.checkout, home=self.home, private=self.private))
        with mock.patch.object(deploy, '_stage_integrated_runtime',
                               side_effect=deploy.RuntimeDeployError('injected stage failure')):
            with self.assertRaisesRegex(deploy.RuntimeDeployError, 'stage failure'):
                self.install()
        self.assertEqual(self.launcher.read_bytes(), installed_launcher)
        self.assertEqual(self.model.read_bytes(), b'GGUF_SYNTHETIC_PRESERVE')
        self.assertEqual(self.db.read_bytes(), b'SQLITE_SYNTHETIC_PRESERVE')


if __name__ == '__main__':
    unittest.main()
