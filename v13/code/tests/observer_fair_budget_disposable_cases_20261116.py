"""Synthetic scheduler and real staged Runtime/SQLite observer contracts."""
import copy
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from v13 import effort, native_turn_budget as native_budget, observer_schedule as obs
from v13 import runtime as runtime_module
from v13.common import Cancelled, Limits
from v13.runtime import Runtime


class SchedulingTests(unittest.TestCase):
    def test_first_timeout_preserves_second_role_slice_and_peer(self):
        now = [0.]
        seen = []
        def ask(role, peer, end):
            seen.append((role, peer, end))
            if role == 'B1_DETAIL':
                now[0] = end
                raise Limits('synthetic native timeout')
            return role
        p = obs.plan(obs.DEFAULT, ['B1_DETAIL', 'B2_GIST'], 'e')
        out = obs.run(p, ask, 10., lambda *_: None, clock=lambda: now[0], budgeted=True)
        self.assertEqual(out, ['B2_GIST'])
        self.assertEqual(seen, [('B1_DETAIL', True, 5.), ('B2_GIST', True, 10.)])

    def test_single_role_has_full_window_and_legacy_signature_is_preserved(self):
        p = obs.plan(obs.DEFAULT, ['B2_GIST'], 'e')
        calls = []
        self.assertEqual(obs.run(p, lambda role, peer, end: calls.append(end) or role,
                                10., lambda *_: None, clock=lambda: 0., budgeted=True), ['B2_GIST'])
        self.assertEqual(calls, [10.])
        self.assertEqual(obs.run(p, lambda role, peer: role, 10., lambda *_: None,
                                clock=lambda: 0.), ['B2_GIST'])

    def test_parallel_keeps_two_argument_callback_and_no_peer(self):
        barrier = threading.Barrier(2, timeout=5)
        def ask(role, peer):
            barrier.wait()
            self.assertFalse(peer)
            return role
        p = obs.plan('ALWAYS_BOTH_ASYNC', ['B1_DETAIL', 'B2_GIST'], 'e', parallel_ok=True)
        self.assertEqual(obs.run(p, ask, 10., lambda *_: None, clock=lambda: 0.),
                         ['B1_DETAIL', 'B2_GIST'])

    def test_cancellation_propagates_and_expired_window_stays_empty(self):
        p = obs.plan(obs.DEFAULT, ['B1_DETAIL', 'B2_GIST'], 'e')
        def cancel(*_):
            raise Cancelled('user')
        with self.assertRaises(Cancelled):
            obs.run(p, cancel, 10., lambda *_: None, clock=lambda: 0.,
                    cancelled=(Cancelled,), budgeted=True)
        ask = Mock()
        self.assertEqual(obs.run(p, ask, 10., lambda *_: None, clock=lambda: 10., budgeted=True), [])
        ask.assert_not_called()

    def test_arithmetic_finals_never_count_as_native_recovery(self):
        failed = {'status': 'DEADLINE', 'metadata': {'runner': {
            'role': 'C3_LANGUAGE', 'generated_tokens': 0, 'last_phase': 'prefill'}}}
        local = {'status': 'FINAL', 'metadata': {
            'output_authority': 'LOCAL_EXACT_ARITHMETIC', 'model_generated': False}}
        result = native_budget.plan(100, 130, 104, recent=[local, local, failed, failed])
        self.assertTrue(result['recovery'])
        self.assertEqual(result['recent_success_streak'], 0)
        for count in (True, 2.5, '2', 0, None):
            final = {'status': 'FINAL', 'metadata': json.dumps({'runner': {
                'role': 'C3_LANGUAGE', 'generated_tokens': count}})}
            self.assertEqual(native_budget.plan(100, 130, 104,
                recent=[final, final, failed, failed])['recent_success_streak'], 0)
        good = {'status': 'FINAL', 'metadata': {'runner': {
            'role': 'C3_LANGUAGE', 'generated_tokens': 3}}}
        self.assertFalse(native_budget.plan(100, 130, 104,
            recent=[good, good, failed, failed])['recovery'])


class RuntimeObserverTests(unittest.TestCase):
    def test_timed_out_b1_leaves_valid_b2_offer_for_c4_and_c3(self):
        with tempfile.TemporaryDirectory() as folder:
            r = Runtime(Path(folder))
            try:
                r.sleep.cycle.set_policy('enabled', 'off')
                r.cfg.update(deadline_seconds=30, observer_seconds=35, max_reentry=0)
                effort.set_mode(r.store, 'max')
                r._route = Mock(return_value=('both', {'source': 'SYNTHETIC_FAIRNESS_TEST'}))
                r.learner.output_delta = Mock(return_value=None)
                now = [time.monotonic()]
                start = now[0]
                calls, sent = [], []
                source = 'Compare Cedar train options: option A costs 11 and option B costs 17. Which costs less?'
                def get_runner(role, *_args, **_kwargs):
                    runner = SimpleNamespace(role=role, last_metrics={})
                    def generate(messages, cancel, end, *_args, **_kwargs):
                        calls.append((role, end))
                        if role == 'B1_DETAIL':
                            now[0] = end
                            runner.last_metrics = {'role': role, 'status': 'DEADLINE', 'generated_tokens': 0}
                            raise Limits('synthetic B1 reached allocated native slice')
                        if role == 'B2_GIST':
                            now[0] += .1
                            runner.last_metrics = {'role': role, 'status': 'FINAL', 'generated_tokens': 20}
                            schema = _args[1] if len(_args) > 1 else {}
                            pointer = schema.get('properties', {}).get('quotes', {}).get('items', {}).get('type') == 'integer'
                            yield json.dumps({'summary': 'Cedar option A costs 11; option B costs 17.',
                                'quotes': [1] if pointer else [source], 'uncertainty': 'none', 'needs_reentry': False})
                        else:
                            sent.append(copy.deepcopy(messages))
                            runner.last_metrics = {'role': role, 'status': 'FINAL', 'generated_tokens': 5}
                            yield 'Option A costs less.'
                    runner.generate = generate
                    return runner
                r.pool.get = Mock(side_effect=get_runner)
                real_run = obs.run
                def run_with_clock(*args, **kwargs):
                    return real_run(*args, **dict(kwargs, clock=lambda: now[0]))
                fake_time = SimpleNamespace(monotonic=lambda: now[0], monotonic_ns=lambda: int(now[0]*1e9))
                event = r.store.event(r.session, source)
                with patch.object(runtime_module, 'time', fake_time), patch.object(obs, 'run', run_with_clock):
                    r._turn(event)
                answer = r.last_answer()
                self.assertEqual(answer['status'], 'FINAL', answer)
                # B2 still reaches C4/C3 before the answer. The missing B1
                # may then retry post-commit without changing that answer.
                self.assertEqual([role for role, _ in calls],
                                 ['B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE', 'B1_DETAIL'])
                post = r.store.rows(
                    "SELECT metrics FROM telemetry WHERE event_id=? AND kind='background_observer_end'",
                    (event['event_id'],))
                self.assertEqual(len(post), 1)
                self.assertEqual(json.loads(post[0]['metrics'])['role'], 'B1_DETAIL')
                self.assertAlmostEqual(calls[0][1]-start, 6.75, places=2)
                self.assertAlmostEqual(calls[1][1]-start, 13.5, places=2)
                stored = r.store.rows("SELECT id,payload FROM packets WHERE event_id=? AND kind='OfferPacket'", (event['event_id'],))
                self.assertEqual(len(stored), 1)
                offer = json.loads(stored[0]['payload'])
                self.assertEqual(offer['role'], 'B2_GIST')
                self.assertEqual(len(offer['evidence_refs']), 1)
                self.assertEqual(r.store.read_source(offer['evidence_refs'][0]), source)
                meta = json.loads(answer['metadata'])
                self.assertIn(offer['packet_id'], meta['selected_offer_ids'])
                self.assertIn(offer['packet_id'], meta['focal']['coalition'])
                self.assertIn(offer['packet_id'], json.dumps(sent))
                self.assertIn('MODEL_HYPOTHESIS_NOT_FACT', json.dumps(sent))
                self.assertEqual(r.cfg['learning_mode'], 'RECORD_ONLY')
                self.assertFalse(r.pool.pids())
            finally:
                r.close()


if __name__ == '__main__':
    unittest.main()
