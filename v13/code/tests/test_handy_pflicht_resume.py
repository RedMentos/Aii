"""Resume refuses missing/tampered evidence and implicit repetition of a lost cohort."""
import contextlib
import fcntl
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import handy_pflicht as H


class ResumeEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)/'home'
        (self.home/'exports').mkdir(parents=True)
        self.root = self.home/'exports/handy-pflicht-kurz'
        self.state_path = self.root/'zustand.json'
        self.binding = {'sha256': 'test-inputs', 'inputs': {'source': 'test'}}

    def tearDown(self):
        self.tmp.cleanup()

    def complete(self, step='ram'):
        folder = self.root/step; folder.mkdir(parents=True, exist_ok=True)
        report = folder/H.REPORTS[step]; report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({'verdict': 'RESEARCH_FAIL', 'authority': 0}))
        return {'step': step, 'status': 'DONE', 'exit_code': 0}

    def main(self, *extra, runner=None, binding=None):
        check = {'installed': True, 'problems': [], 'warnings': [], 'chat_running': False, 'mem': {}, 'cpu_count': 4}
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(H.W, 'precheck', return_value=check))
            stack.enter_context(mock.patch.object(H.W, 'wake_lock', return_value=False))
            stack.enter_context(mock.patch.object(H, 'enable_eligibility', return_value={'eligibility_enabled': True}))
            stack.enter_context(mock.patch.object(H, 'input_binding', side_effect=binding or (lambda *_: self.binding)))
            run = stack.enter_context(mock.patch.object(H, 'run_step', side_effect=runner or (lambda step, *_: self.complete(step))))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            rc = H.main(['kurz', '--installed-home', str(self.home), '--target-dir', str(Path(self.tmp.name)/'dl'), '--nur', 'ram', *extra])
        return rc, run.call_count

    def test_verified_done_skips_and_scientific_fail_stays_fail(self):
        self.assertEqual(self.main(), (0, 1))
        self.assertEqual(self.main(), (0, 0))
        saved = json.loads(self.state_path.read_text())
        self.assertEqual(saved['steps']['ram']['evidence']['ram-budget.json']['size'], (self.root/'ram/ram-budget.json').stat().st_size)
        self.assertEqual(json.loads((self.root/'ram/ram-budget.json').read_text())['verdict'], 'RESEARCH_FAIL')

    def test_deleted_tampered_or_new_artifact_refuses_repeat_without_neu(self):
        for change in ('delete', 'tamper', 'add'):
            with self.subTest(change=change):
                self.assertEqual(self.main('--neu'), (0, 1))
                p = self.root/'ram/ram-budget.json'
                if change == 'delete': p.unlink()
                elif change == 'tamper': p.write_text('{"verdict":"CHANGED"}')
                else: (self.root/'ram/extra.json').write_text('{}')
                self.assertEqual(self.main(), (1, 0))
                self.assertEqual(self.main('--neu'), (0, 1))
                self.assertTrue(list(self.home.glob('exports/handy-pflicht-kurz-previous-*')))

    def test_changed_binding_requires_explicit_neu(self):
        self.assertEqual(self.main(), (0, 1))
        old = self.state_path.read_bytes()
        self.binding = {'sha256': 'new-source-config-model', 'inputs': {}}
        self.assertEqual(self.main(), (2, 0))
        self.assertEqual(self.state_path.read_bytes(), old)
        self.assertEqual(self.main('--neu'), (0, 1))

    def test_corrupt_and_legacy_state_preserved_until_new_attempt(self):
        for value in ('{"steps":', json.dumps({'steps': {'ram': {'status': 'DONE'}}})):
            with self.subTest(value=value):
                self.root.mkdir(parents=True, exist_ok=True); self.state_path.write_text(value)
                self.assertEqual(self.main(), (2, 0))
                self.assertEqual(self.state_path.read_text(), value)
                self.assertEqual(self.main('--neu'), (0, 1))

    def test_running_durable_before_launch_and_killed_attempt_not_repeated(self):
        def killed(*_):
            self.assertEqual(json.loads(self.state_path.read_text())['steps']['ram']['status'], 'RUNNING')
            raise RuntimeError('simulated host death')
        with self.assertRaisesRegex(RuntimeError, 'host death'):
            self.main(runner=killed)
        self.assertEqual(self.main(), (1, 0))
        self.assertEqual(self.main('--neu'), (0, 1))

    def test_missing_or_invalid_primary_report_never_done(self):
        def no_report(step, *_):
            (self.root/step).mkdir(parents=True, exist_ok=True)
            return {'step': step, 'status': 'DONE', 'exit_code': 0}
        self.assertEqual(self.main(runner=no_report), (1, 1))
        self.assertEqual(json.loads(self.state_path.read_text())['steps']['ram']['status'], 'MISSING_EVIDENCE')
        self.assertEqual(self.main(), (1, 0))
        for raw in ('not json', '[]', '{}'):
            (self.root/'ram/ram-budget.json').write_text(raw)
            self.assertIsNone(H.evidence(self.root/'ram', 'ram'))

    def test_inputs_changed_during_run_cannot_be_reused(self):
        calls = iter([self.binding, {'sha256': 'changed', 'inputs': {}}])
        self.assertEqual(self.main(binding=lambda *_: next(calls)), (1, 1))
        self.assertEqual(json.loads(self.state_path.read_text())['steps']['ram']['status'], 'INPUT_CHANGED')

    def test_concurrent_package_refuses_before_launch(self):
        with (self.home/'exports/handy-pflicht.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.main(), (2, 0))

    def test_atomic_writer_preserves_previous_state_on_failure(self):
        self.assertEqual(self.main(), (0, 1))
        before = self.state_path.read_bytes()
        with mock.patch('v13.common.os.replace', side_effect=OSError('simulated rename failure')):
            with self.assertRaises(OSError):
                H.atomic_write(self.state_path, '{"new":true}')
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_interrupt_escalates_ignored_signal_with_bounded_waits(self):
        proc = mock.Mock(pid=12345)
        proc.wait.side_effect = [subprocess.TimeoutExpired('child', 60), 0]
        with mock.patch.object(H.os, 'killpg') as kill:
            H.stop_process_group(proc, 2)
        self.assertEqual(kill.call_args_list, [mock.call(12345, 2), mock.call(12345, 9)])
        self.assertEqual(proc.wait.call_args_list, [mock.call(timeout=60), mock.call(timeout=60)])

    def test_generated_tool_runner_bytes_are_verified_before_skipping(self):
        result = self.complete('werkzeug')
        for name in H.DERIVED_TOOL_FILES:
            path = self.home/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('built')
        result['evidence'] = H.evidence(self.root/'werkzeug', 'werkzeug')
        result['derived_runner_evidence'] = H.derived_tool_evidence(self.home)
        self.assertTrue(H.resumable(result, self.root/'werkzeug', 'werkzeug', self.home))
        (self.home/'bin/native-layer-taps').write_text('changed after measurement')
        self.assertFalse(H.resumable(result, self.root/'werkzeug', 'werkzeug', self.home))


class BindingTest(unittest.TestCase):
    def test_source_config_runner_and_model_identity_changes_invalidate_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); app = root/'app'; home = root/'home'
            for p in (app/'v13', app/'scripts', app/'specs', app/'tests', home/'config', home/'models', home/'bin'):
                p.mkdir(parents=True)
            files = [app/'v13/runtime.py', home/'config/config.json', home/'config/models.json', home/'bin/llama-server', home/'models/synthetic.gguf']
            for p in files: p.write_text('original')
            with mock.patch.object(H, 'APP', app):
                before = H.input_binding(home, 'kurz')
                self.assertEqual(before, H.input_binding(home, 'kurz'))
                self.assertNotEqual(before, H.input_binding(home, 'voll'))
                for p in files:
                    p.write_text('changed')
                    after = H.input_binding(home, 'kurz')
                    self.assertNotEqual(before, after, str(p))
                    before = after
                private = 'do-not-persist-config-value'
                files[1].write_text(json.dumps({'secret': private}))
                self.assertNotIn(private, json.dumps(H.input_binding(home, 'kurz')))

    def test_pinned_measurement_build_outputs_do_not_change_global_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); app = root/'app'; home = root/'home'
            for p in (app/'scripts', home/'bin', home/'config'):
                p.mkdir(parents=True)
            (home/'bin/llama-server').write_text('inference runner')
            with mock.patch.object(H, 'APP', app):
                before = H.input_binding(home, 'kurz')
                for name in H.DERIVED_TOOL_FILES:
                    (home/name).write_text('generated output')
                self.assertEqual(before, H.input_binding(home, 'kurz'))
                (home/'bin/unexpected-new-runner').write_text('not allowlisted')
                self.assertNotEqual(before, H.input_binding(home, 'kurz'))


if __name__ == '__main__':
    unittest.main()
