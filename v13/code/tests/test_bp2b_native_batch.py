"""Software-only BP2b serial batch tests: no model, no native weights."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from scripts import bp2b_native_batch as batch
from scripts import bp2b_native_runner as nr


class NativeBatchSoftwareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / 'out'
        self.calls = []

    @staticmethod
    def preflight(_):
        return {'status': 'FULL_FILE_HASH_PASS',
                'master_sha256_verified_locally': True,
                'pin_sha256': 'f' * 64}

    def fake_runner(self, cmd, stdout, stderr, timeout, check):
        self.assertFalse(check)
        self.assertEqual(stderr, batch.subprocess.STDOUT)
        seed = int(cmd[cmd.index('--seed') + 1])
        arm = cmd[cmd.index('--arm') + 1]
        attempt = cmd[cmd.index('--attempt') + 1]
        out = Path(cmd[cmd.index('--out') + 1])
        self.calls.append((seed, arm))
        path = out / f'seed-{seed}' / arm / f'attempt-{attempt}'
        path.mkdir(parents=True)
        result = {'status': 'COMPLETED', 'evidence_class': 'LINUX_NATIVE_CANDIDATE',
                  'seed': seed, 'arm': arm, 'plan': nr.plan(seed, arm),
                  'age_authority': 0, 'jepa_weight': 0,
                  'master_sha256_verified_locally': True,
                  'adapter_sha256': 'a' * 64}
        (path / 'RESULT.json').write_text(json.dumps(result), encoding='utf-8')
        stdout.write(b'SOFTWARE_FAKE_ONLY\n')
        return SimpleNamespace(returncode=0)

    def run_batch(self, prefix='software1', max_jobs=1, runner=None):
        return batch.execute(self.out, self.root / 'no-real-model', prefix, max_jobs,
                             timeout_seconds=5, runner=runner or self.fake_runner,
                             preflight=self.preflight)

    def test_all_twelve_registered_plans_fixed_and_unique(self):
        jobs = batch.registered('fixed1')
        self.assertEqual(len(jobs), 12)
        self.assertEqual(len({j['attempt'] for j in jobs}), 12)
        self.assertEqual({j['seed'] for j in jobs}, set(nr.SEEDS))
        self.assertEqual({j['arm'] for j in jobs}, set(nr.ARMS))
        for j in jobs:
            self.assertEqual(j['plan'], nr.plan(j['seed'], j['arm']))
            self.assertEqual(j['plan']['jepa_weight'], 0)
            self.assertEqual(j['plan']['age_authority'], 0)

    def test_dry_run_is_read_only_and_has_no_native_authority(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(batch.main(['--out', str(self.out), '--max-jobs', '3']), 0)
        obj = json.loads(output.getvalue())
        self.assertEqual(obj['registered_count'], 12)
        self.assertEqual(obj['selected_count'], 3)
        self.assertFalse(obj['full_acceptance'])
        self.assertEqual(obj['execution'], 'DRY_RUN')
        self.assertFalse(self.out.exists())

    def test_sequential_checkpoint_then_resume_skips_verified_results(self):
        first = self.run_batch(max_jobs=2)
        self.assertEqual(first['completed'], 2)
        self.assertFalse(first['full_acceptance'])
        self.assertEqual(self.calls, [(41, nr.ARMS[0]), (41, nr.ARMS[1])])
        again = self.run_batch(max_jobs=3)
        self.assertEqual(again['completed'], 3)
        self.assertEqual(self.calls, [(41, nr.ARMS[0]), (41, nr.ARMS[1]), (41, nr.ARMS[2])])
        state = json.loads(Path(again['state_path']).read_text())
        self.assertEqual(len(state['registered']), 12)
        self.assertEqual(len(state['attempts']), 3)
        self.assertTrue(all(a['status'] == 'COMPLETED' for a in state['attempts'].values()))
        self.assertFalse(state['full_acceptance'])

    def test_tampered_result_and_log_refuse_restart(self):
        self.run_batch(max_jobs=1)
        result = self.out / 'seed-41' / 'legacy' / 'attempt-software1-s41-legacy' / 'RESULT.json'
        result.write_text(result.read_text() + '\n')
        with self.assertRaises(ValueError):
            self.run_batch(max_jobs=2)
        self.assertEqual(len(self.calls), 1)

    def test_failed_subprocess_retained_and_no_overwrite(self):
        def failure(cmd, stdout, stderr, timeout, check):
            stdout.write(b'ORIGINAL_FAILURE\n')
            return SimpleNamespace(returncode=7)
        with self.assertRaises(RuntimeError):
            self.run_batch(runner=failure)
        state_path = self.out / '.bp2b-batch' / 'software1' / 'STATE.json'
        state = json.loads(state_path.read_text())
        self.assertEqual(state['attempts']['41:legacy']['status'], 'FAILED')
        self.assertEqual(state['attempts']['41:legacy']['exit_code'], 7)
        log = state_path.parent / 'log-s41-legacy.txt'
        self.assertEqual(log.read_bytes(), b'ORIGINAL_FAILURE\n')
        with self.assertRaises(ValueError):
            self.run_batch()
        self.assertEqual(log.read_bytes(), b'ORIGINAL_FAILURE\n')

    def test_completed_raw_log_is_fsynced_before_checkpoint(self):
        import os
        from unittest import mock
        original_fsync = os.fsync
        synced_paths = set()

        def recording_fsync(fd):
            synced_paths.add(os.readlink(f'/proc/self/fd/{fd}'))
            return original_fsync(fd)

        with mock.patch.object(batch.os, 'fsync', side_effect=recording_fsync):
            self.run_batch(max_jobs=1)
        log = self.out / '.bp2b-batch' / 'software1' / 'log-s41-legacy.txt'
        self.assertIn(str(log), synced_paths)

    def test_failed_raw_log_is_fsynced_before_failure_checkpoint(self):
        import os
        from unittest import mock
        original_fsync = os.fsync
        synced_paths = set()

        def recording_fsync(fd):
            synced_paths.add(os.readlink(f'/proc/self/fd/{fd}'))
            return original_fsync(fd)

        def failed_runner(cmd, stdout, stderr, timeout, check):
            stdout.write(b'ORIGINAL_FAILED_NATIVE_LOG\n')
            return SimpleNamespace(returncode=9)

        with mock.patch.object(batch.os, 'fsync', side_effect=recording_fsync):
            with self.assertRaises(RuntimeError):
                self.run_batch(max_jobs=1, runner=failed_runner)
        log = self.out / '.bp2b-batch' / 'software1' / 'log-s41-legacy.txt'
        self.assertIn(str(log), synced_paths)

    def test_timeout_is_failure_not_partial_success(self):
        def timed_out(cmd, stdout, stderr, timeout, check):
            raise batch.subprocess.TimeoutExpired(cmd, timeout)
        with self.assertRaises(RuntimeError):
            self.run_batch(runner=timed_out)
        state = json.loads((self.out / '.bp2b-batch' / 'software1' / 'STATE.json').read_text())
        self.assertEqual(state['attempts']['41:legacy']['exit_code'], 124)
        self.assertFalse(state['full_acceptance'])

    def test_prefix_matches_actual_child_native_attempt_contract(self):
        # Real run_arm rejects >32 characters and dots; fake subprocesses do not.
        import re
        child = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,31}\Z')
        for job in batch.registered('x' * 17):
            self.assertIsNotNone(child.fullmatch(job['attempt']))
            self.assertLessEqual(len(job['attempt']), 32)
        for bad in ('x' * 18, 'x.y', 'abc.def'):
            with self.subTest(prefix=bad), self.assertRaises(ValueError):
                batch.registered(bad)
        self.assertFalse(self.out.exists())

    def test_invalid_inputs_and_master_preflight_fail_before_output(self):
        for prefix in ('../escape', '..', '', 'a/b', 'bad space', 'x' * 25):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                batch.registered(prefix)
        with self.assertRaises(ValueError):
            self.run_batch(max_jobs=0)
        with self.assertRaises(ValueError):
            batch.execute(self.out, self.root, 'safe1',
                          preflight=lambda _: {'status': 'FAIL'})
        self.assertFalse(self.out.exists())

    def test_untracked_attempt_refused_before_model_subprocess(self):
        attempt = self.out / 'seed-41' / 'legacy' / 'attempt-software1-s41-legacy'
        attempt.mkdir(parents=True)
        with self.assertRaises(ValueError):
            self.run_batch()
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
