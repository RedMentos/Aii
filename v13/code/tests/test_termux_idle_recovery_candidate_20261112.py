"""Real SQLite/scheduler tests in an isolated, hash-bound recovery package.

No model execution or user turns. The coordinator smoke advances injected
clocks explicitly; it is software evidence, not a phone longevity measurement.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

CODE = Path(__file__).resolve().parents[1]
DISPOSABLE = os.environ.get('V13_IDLE_DISPOSABLE') == '1'


def builder():
    path = CODE / 'scripts/termux_idle_recovery_candidate_20261112.py'
    spec = importlib.util.spec_from_file_location('idle_recovery_builder', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipIf(DISPOSABLE, 'outer staging harness')
class CandidateCompositionTests(unittest.TestCase):
    def test_builder_preserves_frozen_sources_and_upstream_additions(self):
        module = builder()
        before = {p: hashlib.sha256((CODE / p).read_bytes()).hexdigest() for p in module.PINS}
        inherited = {'v13/operator.py': (CODE / 'v13/operator.py').read_bytes().replace(
            b"        if cmd=='cancel':", b"        # composed upstream marker\n        if cmd=='cancel':"),
                     'v13/other_candidate.py': b'# preserved\n'}
        result = module.apply_sources(CODE, inherited)
        self.assertIn(b'composed upstream marker', result['v13/operator.py'])
        self.assertEqual(result['v13/other_candidate.py'], b'# preserved\n')
        self.assertIn(b'idle_cycle_blocked', result['v13/scheduler.py'])
        for path, digest in before.items():
            self.assertEqual(hashlib.sha256((CODE / path).read_bytes()).hexdigest(), digest)
        with mock.patch.dict(module.PINS, {'v13/idle_cycle_candidate.py': '0' * 64}):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                module.build_sources(CODE)

    def test_actual_scheduler_operator_and_no_input_coordinator(self):
        with tempfile.TemporaryDirectory(prefix='v13-idle-candidate-test-') as tmp:
            root = Path(tmp)
            shutil.copytree(CODE / 'v13', root / 'v13',
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            shutil.copytree(CODE / 'specs', root / 'specs')
            (root / 'tests').mkdir()
            test = Path(__file__)
            shutil.copyfile(test, root / 'tests' / test.name)
            for name, data in builder().build_sources(CODE).items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            result = subprocess.run([sys.executable, str(root / 'tests' / test.name), '-v'],
                                    cwd=root, env=dict(os.environ, PYTHONPATH=str(root),
                                                      V13_IDLE_DISPOSABLE='1'),
                                    capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('REAL_NO_INPUT_COORDINATOR_PASS', result.stdout)
            print(result.stdout.strip())


class Clock:
    def __init__(self):
        self.t = 1_900_000_000.0
        self.mono = 1000.0

    def __call__(self):
        return self.t

    def monotonic(self):
        return self.mono

    def advance(self, seconds):
        self.t += seconds
        self.mono += seconds


@unittest.skipUnless(DISPOSABLE, 'run only in isolated patched package')
class IdleCycleTests(unittest.TestCase):
    def setUp(self):
        from v13.runtime import Runtime
        from v13.scheduler import EventScheduler
        from v13 import idle_cycle_candidate as idle
        self.idle = idle
        self.tmp = tempfile.TemporaryDirectory(prefix='v13-idle-runtime-')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.addCleanup(lambda: self.r.close())
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.sleep.cycle.set_policy('tick_seconds', '300')
        self.clock = Clock()
        self.scheduler = EventScheduler(self.r.store, self.r.cfg, self.clock,
                                        key='IDLE_RECOVERY_TEST_QUEUE')

    def enable(self):
        self.idle.set_enabled(self.scheduler, True, 'EXPLICIT_HUMAN')

    def dispatch(self, action='sleep_c', *, origin='SYSTEM', complete='DONE'):
        eid = self.scheduler.post('IDLE', origin=origin, action=action)
        event = self.scheduler.next()
        self.assertIsNotNone(event)
        self.assertEqual(event['id'], eid)
        self.scheduler.complete(eid, complete)
        return event

    def no_user_turns(self):
        self.assertEqual(self.r.store.one('SELECT COUNT(*) AS n FROM accepted_turns')['n'], 0)
        self.assertEqual(self.r.store.one('SELECT COUNT(*) AS n FROM messages')['n'], 0)

    def test_default_per_input_budget_does_not_renew_by_time(self):
        for _ in range(12):
            self.dispatch()
        self.scheduler.post('IDLE', action='sleep_c')
        self.assertIsNone(self.scheduler.next())
        self.clock.advance(7200)
        self.assertIsNone(self.scheduler.next())
        self.no_user_turns()

    def test_opt_in_rolls_after_hour_and_never_fabricates_input(self):
        with self.assertRaises(PermissionError):
            self.idle.set_enabled(self.scheduler, True)
        self.enable()
        for _ in range(12):
            self.dispatch()
        pending = self.scheduler.post('IDLE', action='sleep_c')
        self.assertIsNone(self.scheduler.next())
        self.assertEqual(self.idle.blocked(self.scheduler, 'sleep_c'), 'HOURLY_QUOTA')
        self.clock.advance(3600)
        event = self.scheduler.next()
        self.assertEqual(event['id'], pending)
        self.scheduler.complete(pending, 'DONE')
        for _ in range(11):
            self.dispatch()
        self.assertEqual(self.scheduler.background_since_input(), 24)
        self.assertEqual(self.idle.blocked(self.scheduler, 'sleep_c'), 'HOURLY_QUOTA')
        self.idle.set_enabled(self.scheduler, False, 'EXPLICIT_HUMAN')
        self.assertEqual(self.idle.blocked(self.scheduler, 'sleep_c'), 'BURNED_OUT_WAITING_FOR_INPUT')
        self.no_user_turns()

    def test_retries_and_smaller_operator_budget_count(self):
        from v13.inputs import set_burnout
        self.enable()
        set_burnout(self.r.store, 2)
        eid = self.scheduler.post('IDLE', action='sleep_c')
        for attempt in (1, 2):
            self.assertEqual(self.scheduler.next()['attempts'], attempt)
            self.scheduler.complete(eid, 'RETRY')
        self.assertIsNone(self.scheduler.next())
        self.assertEqual(self.idle.blocked(self.scheduler, 'sleep_c'), 'HOURLY_QUOTA')

    def test_restart_preserves_quota_and_policy(self):
        from v13.runtime import Runtime
        from v13.scheduler import EventScheduler
        self.enable()
        for _ in range(12):
            self.dispatch()
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.scheduler = EventScheduler(self.r.store, self.r.cfg, self.clock,
                                        key='IDLE_RECOVERY_TEST_QUEUE')
        self.assertTrue(self.idle._load(self.r.store)[0]['enabled'])
        self.assertEqual(self.idle.blocked(self.scheduler, 'sleep_c'), 'HOURLY_QUOTA')
        self.clock.advance(3600)
        self.assertIsNone(self.idle.blocked(self.scheduler, 'sleep_c'))
        self.no_user_turns()

    def test_clock_rollback_and_corrupt_or_missing_ledger_fail_closed(self):
        self.enable()
        self.dispatch()
        self.clock.advance(-1)
        self.assertEqual(self.idle.blocked(self.scheduler, 'sleep_c'), 'CLOCK_ROLLBACK')
        self.clock.advance(1)
        state, version = self.scheduler._load()
        state['dispatch_times'] = ['corrupt']
        self.r.store.set_state(self.scheduler.key, state, expected=version)
        self.assertEqual(self.idle.blocked(self.scheduler, 'sleep_c'), 'INVALID_DISPATCH_LEDGER')
        state, version = self.scheduler._load()
        del state['dispatch_times']
        self.r.store.set_state(self.scheduler.key, state, expected=version)
        self.assertEqual(self.idle.blocked(self.scheduler, 'sleep_c'), 'LEGACY_DISPATCH_LEDGER')

    def test_full_evicted_ledger_cannot_refund_recent_dispatches(self):
        from v13.scheduler import DISPATCH_LEDGER_MAX
        self.enable()
        state, version = self.scheduler._load()
        state['dispatch_times'] = [self.clock.t - DISPATCH_LEDGER_MAX + i
                                   for i in range(DISPATCH_LEDGER_MAX)]
        self.r.store.set_state(self.scheduler.key, state, expected=version)
        self.assertEqual(self.idle.blocked(self.scheduler, 'sleep_c'), 'HOURLY_QUOTA')
        self.clock.advance(3600)
        self.assertIsNone(self.idle.blocked(self.scheduler, 'sleep_c'))

    def test_pause_resource_age_quiet_and_user_priority_are_preserved(self):
        from v13.inputs import set_pause
        self.enable()
        self.scheduler.post('IDLE', action='learn_medium')
        set_pause(self.r.store, 'training', True)
        self.assertIsNone(self.scheduler.next())
        self.assertEqual(self.idle.blocked(self.scheduler, 'learn_medium'), 'PAUSED_TRAINING')
        set_pause(self.r.store, 'training', False)
        self.assertIsNone(self.scheduler.next(idle=False))
        self.assertIsNone(self.scheduler.next(resource_state='CRITICAL'))
        self.assertIsNone(self.scheduler.next(resource_state='PRESSURE'))
        self.assertIsNone(self.scheduler.next(quiet=True))
        self.scheduler.post('USER_INPUT', origin='USER', action='notice')
        self.assertEqual(self.scheduler.next()['kind'], 'USER_INPUT')
        self.scheduler.post('IDLE', origin='SELF', action='sleep_c')
        self.assertEqual(self.scheduler.next()['action'], 'learn_medium')
        self.assertIsNone(self.scheduler.next())
        self.assertEqual(self.scheduler.pending()[-1]['status'], 'HELD_AGE')
        self.assertEqual(self.idle.blocked(self.scheduler, 'growth_practice'), 'OUTSIDE_IDLE_CYCLE_ACTIONS')
        set_pause(self.r.store, 'traum', True)
        self.assertEqual(self.idle.blocked(self.scheduler, 'sleep_full'), 'PAUSED_TRAUM')

    def test_operator_status_and_toggle_work_while_busy_without_learning_promotion(self):
        from v13.operator import Operator
        from v13.inputs import set_pause
        self.r.sleep.scheduler = self.scheduler
        self.r.current = 'probe'
        try:
            result = json.loads(Operator(self.r).run(':idle on'))
            self.assertTrue(result['enabled'])
            self.assertTrue(result['worker_alive'])
            self.assertEqual(result['blocked_reason'], 'FOREGROUND_OR_JOB_BUSY')
            self.assertEqual(result['learning_mode'], 'RECORD_ONLY')
            self.assertFalse(result['last_real_learning']['parameters_fitted'])
            self.assertEqual(json.loads(Operator(self.r).run(':idle status'))['current_job'], 'probe')
            self.r.current = None
            before = self.r.store.state(self.idle.KEY, None)
            with mock.patch.object(self.r.sleep, 'resource_state', return_value='NORMAL'):
                json.loads(Operator(self.r).run(':idle status'))
            self.assertEqual(self.r.store.state(self.idle.KEY, None), before,
                             'status must not advance the persistent clock watermark')
            set_pause(self.r.store, 'selfedit', True)
            self.assertFalse(json.loads(Operator(self.r).run(':idle off'))['enabled'])
        finally:
            self.r.current = None
        self.no_user_turns()

    def test_real_no_input_coordinator_runs_and_persists_without_fake_learning(self):
        from v13 import authority
        from v13.runtime import Runtime
        from v13.world_model import KEY as WORLD_KEY
        sl = self.r.sleep
        with self.r.lock:
            sl.clock = self.clock
            sl.monotonic = self.clock.monotonic
            sl.scheduler.clock = self.clock
            sl.cycle.clock = self.clock
            sl.cycle.monotonic = self.clock.monotonic
            sl.cycle.queue.clock = self.clock
            sl.last_tick = -1e18
            sl.cycle.set_policy('enabled', 'on')
            sl.cycle.set_policy('sleep_idle_s', '30')
            sl.cycle.set_policy('sleep_interval_s', '60')
            sl.cycle.set_policy('tick_seconds', '1')
            self.r.store.set_meta('sleep_boot_wall', self.clock.t)
            self.idle.set_enabled(sl.scheduler, True, 'EXPLICIT_HUMAN')
        with mock.patch.object(authority, 'now', self.clock):
            for cycle in range(6):
                with self.r.lock:
                    self.clock.advance(3601)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    count = sl.cycle.status()['cycles']
                    history = sl.scheduler.report()['history']
                    done_slow = sum(e['action'] == 'learn_slow' and e['status'] == 'DONE' for e in history)
                    if count >= cycle + 1 and done_slow >= cycle + 1:
                        break
                    with self.r.lock:
                        self.clock.advance(1)
                    self.r.wake.set()
                    time.sleep(.02)
                self.assertGreaterEqual(count, cycle + 1, history)
                self.assertGreaterEqual(done_slow, cycle + 1, history)
        self.no_user_turns()
        self.assertEqual(self.r.store.state(WORLD_KEY, None)[0]['status'], 'TOO_FEW_TRANSITIONS')
        self.assertEqual(self.r.pool.pids() + self.r.needle.pids(), [])
        completed = sl.scheduler.report()['history']
        self.assertGreater(len(completed), 12)
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.assertGreaterEqual(self.r.sleep.cycle.status()['cycles'], 6)
        self.assertTrue(self.idle._load(self.r.store)[0]['enabled'])
        self.assertEqual(self.r.store.state(WORLD_KEY, None)[0]['status'], 'TOO_FEW_TRANSITIONS')
        print('REAL_NO_INPUT_COORDINATOR_PASS: six accelerated hourly cycles, '
              'more than twelve real jobs, zero input/model calls, persisted restart, honest no-data result')


if __name__ == '__main__':
    unittest.main()
