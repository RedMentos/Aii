"""Software preparation/ownership fixtures; no native process or inference."""
import fcntl
import json
from pathlib import Path
import platform
import tempfile
import threading
import unittest
from unittest.mock import patch

from v13 import causal_prepare as prepare
from v13.common import dumps, file_hash, Unavailable
from v13.config import initialize
from scripts.native_prefill_stream_client import STREAM_ABI


class Preparation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.model = self.home / 'models/fixture.gguf'
        self.model.write_bytes(b'NOT_A_NATIVE_MODEL_SOFTWARE_ONLY')
        self.binary = self.home / 'bin/native-prefill-stream'
        self.binary.write_bytes(b'SOFTWARE_BINARY_FIXTURE')
        self.binary.chmod(0o700)
        self.spec = {'runner': {'tag': 'SOFTWARE', 'source_url': 'SOFTWARE_NO_NETWORK',
                               'source_size': 42, 'source_sha256': 'a' * 64},
                     'models': {'language': {'files': [{'sha256': file_hash(self.model)}], 'revision': 'r1'}}}
        self.identity = {'fixture': 'SOFTWARE_NO_NATIVE'}
        self.binding = {'identity': self.identity, 'binary': str(self.binary),
                        'binary_sha256': file_hash(self.binary), 'feature_abi': {'stream_abi': STREAM_ABI}}
        self.marker = {'identity_key': {'feature_abi': STREAM_ABI, 'base_build_identity': {
            'source_archive': {'url': 'SOFTWARE_NO_NETWORK', 'size': 42, 'sha256': 'a' * 64},
            'machine': platform.machine(), 'build_flags': ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror']}}}
        self.save_marker()

    def tearDown(self):
        self.tmp.cleanup()

    def save_marker(self):
        (self.home / 'config/native-prefill-stream.json').write_text(dumps(self.marker))

    def test_read_only_check_verifies_abi_archive_platform_and_executable(self):
        with patch('scripts.native_prefill_stream_client.bind_installed', return_value=self.binding), patch.object(prepare, 'catalog', return_value=self.spec):
            self.assertEqual(prepare.check_prepared(self.home), self.binding)
            self.marker['identity_key']['feature_abi'] = 'OLD_SAME_DIMENSION'
            self.save_marker()
            with self.assertRaisesRegex(Unavailable, 'ABI/source/platform'):
                prepare.check_prepared(self.home)
            self.marker['identity_key']['feature_abi'] = STREAM_ABI
            self.marker['identity_key']['base_build_identity']['source_archive']['sha256'] = 'b' * 64
            self.save_marker()
            with self.assertRaises(Unavailable):
                prepare.check_prepared(self.home)

    def test_missing_binding_is_actionable_without_build(self):
        with patch('scripts.native_prefill_stream_client.bind_installed', side_effect=FileNotFoundError('fixture missing')):
            with self.assertRaisesRegex(Unavailable, 'VORBEREITEN_CAUSAL.sh'):
                prepare.check_prepared(self.home)

    def test_busy_coordinator_refuses_before_mutation_or_build(self):
        original = (self.home / 'config/settings.json').read_bytes()
        with (self.home / 'data/coordinator.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch('scripts.test_native_prefill_stream.build_stream') as build:
                with self.assertRaisesRegex(Unavailable, 'läuft oder baut'):
                    prepare.prepare_causal_stream(self.home, out_dir=self.home / 'exports/busy')
                build.assert_not_called()
        self.assertEqual((self.home / 'config/settings.json').read_bytes(), original)
        report = json.loads((self.home / 'exports/busy/report.json').read_text())
        self.assertEqual(report['status'], 'CAUSAL_PREPARATION_FAILED')
        self.assertFalse(report['native_inference_performed'])

    def prepare_mocked(self, *, guards=None, failure=None, enable=False):
        def run(command, log, cancel, seconds):
            self.assertEqual(command, [str(self.binary), '--guard-test'])
            log.write_text(dumps(guards or {'schema': 'V13_CAUSAL_STREAM_GUARDS_V2',
                                          'status': 'GUARD_PASS', 'checks': {'fixture_guard': True},
                                          'native_inference_performed': False}))
            return {'exit_code': 0, 'stop_reason': None, 'process_reaped': True}
        with patch.object(prepare, 'catalog', return_value=self.spec), patch.object(prepare, 'ModelManager') as manager, patch('scripts.test_native_prefill_port.installed_identity', return_value=self.identity), patch('scripts.test_native_prefill_stream.build_stream', return_value=(self.binary, {'SOFTWARE_BUILD': True}), side_effect=failure) as build, patch('scripts.test_native_prefill_port.bounded_process', side_effect=run), patch.object(prepare, 'check_prepared', return_value=self.binding):
            manager.return_value.path_for.return_value = self.model
            manager.return_value.revision.return_value = 'r1'
            report = prepare.prepare_causal_stream(self.home, out_dir=self.home / 'exports/attempt', enable=enable)
            build.assert_called_once()
            manager.return_value.install.assert_not_called()
            return report

    def test_explicit_prepare_enables_only_after_guards_and_exact_binding(self):
        report = self.prepare_mocked(enable=True)
        self.assertEqual(report['status'], 'CAUSAL_PREPARED_NO_MODEL_INFERENCE')
        self.assertFalse(report['native_inference_performed'])
        self.assertFalse(report['model_weights_modified'])
        self.assertTrue(report['runtime_enabled'])
        self.assertEqual(json.loads((self.home / 'config/settings.json').read_text())['c3_decode_mode'], 'same_causal_zero')
        self.assertEqual(report['configured_answer_tokens'], 64)
        self.assertEqual(json.loads((self.home / 'config/settings.json').read_text())['answer_tokens'], 64)

    def test_compile_failure_preserved_no_enable_and_lock_released(self):
        original = (self.home / 'config/settings.json').read_bytes()
        with self.assertRaisesRegex(Unavailable, 'compiler fixture failed'):
            self.prepare_mocked(enable=True, failure=RuntimeError('compiler fixture failed'))
        self.assertEqual((self.home / 'config/settings.json').read_bytes(), original)
        report = json.loads((self.home / 'exports/attempt/report.json').read_text())
        self.assertEqual(report['status'], 'CAUSAL_PREPARATION_FAILED')
        with (self.home / 'data/coordinator.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_native_guard_schema_or_failed_check_cannot_enable(self):
        with self.assertRaisesRegex(Unavailable, 'guard result'):
            self.prepare_mocked(enable=True, guards={'schema': 'V13_CAUSAL_STREAM_GUARDS_V2', 'status': 'GUARD_PASS',
                'checks': {'actual_failed_fixture': False}, 'native_inference_performed': False})
        self.assertFalse(json.loads((self.home / 'exports/attempt/report.json').read_text())['runtime_enabled'])

    def test_pre_cancelled_request_stops_before_build(self):
        cancel = threading.Event()
        cancel.set()
        with patch('scripts.test_native_prefill_stream.build_stream') as build:
            with self.assertRaisesRegex(Unavailable, 'cancelled before build'):
                prepare.prepare_causal_stream(self.home, cancel=cancel, out_dir=self.home / 'exports/cancelled')
            build.assert_not_called()

    def test_standard_bootstrap_cannot_download_or_build_during_runtime(self):
        from v13 import bootstrap
        with (self.home / 'data/coordinator.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch('sys.argv', ['bootstrap', '--home', str(self.home)]), patch.object(bootstrap, 'ModelManager') as models, patch.object(bootstrap, 'install_native') as install:
                with self.assertRaisesRegex(Unavailable, 'läuft oder baut'):
                    bootstrap.main()
                models.assert_not_called()
                install.assert_not_called()


if __name__ == '__main__':
    unittest.main()
