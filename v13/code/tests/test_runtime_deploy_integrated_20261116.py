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
        self.checkout = CODE.parent.parent
        self.commit = subprocess.run(['git', '-C', str(self.checkout), 'rev-parse', 'HEAD'],
                                     capture_output=True, text=True, check=True).stdout.strip()
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
from unittest.mock import Mock
import json
import time
from v13.operator import Operator
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

        def wait_for_turn():
            end = time.monotonic() + 15
            while not r.idle() and time.monotonic() < end:
                time.sleep(.01)
            assert r.idle(), 'Synthetic turn did not settle'
            answer = r.last_answer()
            assert answer['status'] == 'FINAL', answer
            return answer

        # Exercise the installed staged arithmetic path without a native runner.
        r.pool.get = Mock(side_effect=AssertionError('unexpected native runner'))
        r.submit('2+2')
        assert wait_for_turn()['text'] == '4'

        # Exercise installed B1/B2 -> C4 -> C3 using synthetic model outputs.
        question = ('Compare details with planning. The rent is 120 euros. '
                    'The plan preserves a long-term reserve.')
        r.cfg.update(deadline_seconds=90, observer_seconds=5, max_reentry=0,
                     observer_mode='background', b2_quote_select='off',
                     offer_quote_context_chars=0, b2_state_slots=0)
        Operator(r).run(':effort max')
        Operator(r).run(':ctxos active')
        r._route = Mock(return_value=('both', {'source': 'SYNTHETIC_DEPLOY_TEST'}))
        r.learner.output_delta = Mock(return_value=None)
        sent = []
        class Runner:
            def __init__(self, role):
                self.role = role
                self.last_metrics = {'role': role, 'status': 'FINAL',
                                     'generated_tokens': 5, 'synthetic': True}
            def generate(self, messages, cancel, deadline, *args, **kwargs):
                if self.role == 'B1_DETAIL':
                    yield json.dumps({'summary': 'The rent is 120 euros.',
                        'quotes': ['The rent is 120 euros.'], 'uncertainty': 'low',
                        'needs_reentry': False})
                elif self.role == 'B2_GIST':
                    yield json.dumps({'summary': 'A long-term reserve is needed.',
                        'quotes': ['The plan preserves a long-term reserve.'],
                        'uncertainty': 'low', 'needs_reentry': False})
                else:
                    sent.append(messages)
                    yield 'One combined response.'
        runners = {role: Runner(role) for role in ('B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE')}
        r.pool.get = Mock(side_effect=lambda role: runners[role])
        r.submit(question)
        answer = wait_for_turn()
        assert answer['text'] == 'One combined response.'
        selected = json.loads(answer['metadata'])['selected_offer_ids']
        assert len(selected) == 2, selected
        rendered = json.dumps(sent, ensure_ascii=False)
        assert all(packet_id in rendered for packet_id in selected), selected
        assert not (Path(tmp) / 'online_world' / 'online_predictor.npz').exists()
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
