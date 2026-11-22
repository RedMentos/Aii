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
from v13 import cognition as cognition_module
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

    def test_budgeted_scheduler_defers_subminimum_first_role_and_continues_peer(self):
        minimum = native_budget.MIN_ROLE_SLICE_S
        now = [0.]
        seen, errors = [], []

        def ask(role, peer, role_end=None):
            self.assertTrue(peer)
            self.assertIsNotNone(role_end)
            seconds = role_end - now[0]
            seen.append((role, seconds))
            if seconds < minimum:
                raise Limits('below minimum fair role slice')
            now[0] = role_end
            return role

        plan = obs.plan(obs.DEFAULT, ['B1_DETAIL', 'B2_GIST'], 'e')
        offers = obs.run(plan, ask, 1.5, lambda role, exc: errors.append((role, type(exc).__name__)),
                         clock=lambda: now[0], budgeted=True)
        self.assertEqual(offers, ['B2_GIST'])
        self.assertEqual([role for role, _ in seen], ['B1_DETAIL', 'B2_GIST'])
        self.assertAlmostEqual(seen[0][1], .75, places=2)
        self.assertAlmostEqual(seen[1][1], 1.5, places=2)
        self.assertEqual(errors, [('B1_DETAIL', 'Limits')])

    def test_budgeted_scheduler_runs_both_roles_at_exact_minimum_slice(self):
        minimum = native_budget.MIN_ROLE_SLICE_S
        now = [0.]
        seen = []

        def ask(role, peer, role_end=None):
            self.assertTrue(peer)
            seconds = role_end - now[0]
            seen.append((role, seconds))
            if seconds < minimum:
                raise Limits('below minimum fair role slice')
            now[0] = role_end
            return role

        plan = obs.plan(obs.DEFAULT, ['B1_DETAIL', 'B2_GIST'], 'e')
        offers = obs.run(plan, ask, 2.0, lambda role, exc: self.fail(f'{role} unexpectedly deferred: {exc}'),
                         clock=lambda: now[0], budgeted=True)
        self.assertEqual(offers, ['B1_DETAIL', 'B2_GIST'])
        self.assertEqual([role for role, _ in seen], ['B1_DETAIL', 'B2_GIST'])
        self.assertAlmostEqual(seen[0][1], minimum, places=2)
        self.assertAlmostEqual(seen[1][1], minimum, places=2)

    def test_unbudgeted_scheduler_retains_one_second_admission_guard(self):
        plan = obs.plan(obs.DEFAULT, ['B1_DETAIL', 'B2_GIST'], 'e')
        calls = []
        offers = obs.run(plan, lambda role, peer: calls.append(role) or role,
                         .5, lambda *_: None, clock=lambda: 0.)
        self.assertEqual(offers, [])
        self.assertEqual(calls, [])

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
        for count in (False, 0.0, '0', None):
            malformed = {'status': 'DEADLINE', 'metadata': {'runner': {
                'role': 'C3_LANGUAGE', 'generated_tokens': count, 'last_phase': 'prefill'}}}
            self.assertFalse(native_budget.zero_token_prefill_failure(malformed))
        fair = native_budget.plan(100, 130, 104, recent=[failed, failed],
                                  background_enabled=True, observer_deadline=113.5)
        self.assertTrue(fair['recovery'])
        self.assertEqual(fair['preanswer_end_monotonic'], 113.5)
        self.assertAlmostEqual(fair['preanswer_seconds_available'], 9.5, places=2)
        self.assertAlmostEqual(fair['c3_reserved_seconds'], 16.5, places=2)
        self.assertEqual(fair['minimum_role_slice_s'], 1.0)
        first_slot = native_budget.plan(100, 130, 104, recent=[failed, failed],
                                        background_enabled=True, observer_deadline=106.75)
        self.assertAlmostEqual(first_slot['preanswer_seconds_available'], 2.75, places=2)
        self.assertAlmostEqual(first_slot['c3_reserved_seconds'], 16.5, places=2)


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


    # Include Runtime routing/budget telemetry in failures; this protects the same-turn B1/B2 gate.
    def test_two_recent_c3_prefill_failures_keep_b1_and_b2_in_same_turn_c4_to_c3(self):
        with tempfile.TemporaryDirectory() as folder:
            r = Runtime(Path(folder))
            try:
                r.sleep.cycle.set_policy('enabled', 'off')
                r.cfg.update(deadline_seconds=30, observer_seconds=35, max_reentry=0)
                effort.set_mode(r.store, 'max')
                r._route = Mock(return_value=('both', {'source': 'SYNTHETIC_RECOVERY_TEST'}))
                r.learner.output_delta = Mock(return_value=None)
                for index in range(2):
                    previous = r.store.event(r.session, f'previous failed C3 {index}')
                    r.store.message(r.session, previous['event_id'], 'assistant',
                        status='DEADLINE',
                        metadata={'runner': {'role': 'C3_LANGUAGE', 'generated_tokens': 0,
                                             'last_phase': 'prefill', 'duration_s': 29.1}})
                now = [time.monotonic()]
                start = now[0]
                calls, sent = [], []
                source = 'Compare Cedar train options: option A costs 11 and option B costs 17. Which costs less?'
                offers_by_role = {
                    'B1_DETAIL': ('Cedar option A costs 11.', 'option A costs 11'),
                    'B2_GIST': ('Cedar option B costs 17.', 'option B costs 17'),
                }

                def get_runner(role, *_args, **_kwargs):
                    runner = SimpleNamespace(role=role, last_metrics={})

                    def generate(messages, cancel, end, *_args, **_kwargs):
                        calls.append((role, end))
                        now[0] += .2
                        if role in offers_by_role:
                            summary, quote = offers_by_role[role]
                            schema = _args[1] if len(_args) > 1 else _kwargs.get('schema', {})
                            pointer = (isinstance(schema, dict)
                                and schema.get('properties', {}).get('quotes', {})
                                    .get('items', {}).get('type') == 'integer')
                            runner.last_metrics = {'role': role, 'status': 'FINAL',
                                                   'generated_tokens': 20, 'prompt_tokens': 60}
                            yield json.dumps({'summary': summary,
                                'quotes': [1] if pointer else [quote],
                                'uncertainty': 'none', 'needs_reentry': False})
                        elif role == 'C3_LANGUAGE':
                            sent.append(copy.deepcopy(messages))
                            runner.last_metrics = {'role': role, 'status': 'FINAL',
                                                   'generated_tokens': 5, 'prompt_tokens': 80}
                            yield 'Option A costs less, at 11.'
                        else:
                            raise AssertionError(f'unexpected runner {role}')

                    runner.generate = generate
                    return runner

                r.pool.get = Mock(side_effect=get_runner)
                fake_time = SimpleNamespace(monotonic=lambda: now[0],
                                            monotonic_ns=lambda: int(now[0] * 1e9))
                event = r.store.event(r.session, source)
                real_run = obs.run

                def run_with_clock(*args, **kwargs):
                    return real_run(*args, **dict(kwargs, clock=lambda: now[0]))

                with patch.object(runtime_module, 'time', fake_time), \
                     patch.object(cognition_module, 'time', fake_time), \
                     patch.object(obs, 'run', run_with_clock), \
                     patch.object(obs, 'background', return_value=[]):
                    r._turn(event)

                answer = r.last_answer()
                self.assertEqual(answer['status'], 'FINAL', answer)
                diagnostic = json.loads(answer['metadata'])
                offer_diagnostics = [
                    {'kind': row['kind'], 'metrics': json.loads(row['metrics'])}
                    for row in r.store.rows(
                        "SELECT kind,metrics FROM telemetry WHERE event_id=? AND kind IN "
                        "('offer_rejected','native_body_deferred_for_c3','native_body_budgeted_for_c3') ORDER BY id",
                        (event['event_id'],))
                ]
                self.assertEqual([role for role, _ in calls],
                                 ['B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE'],
                                 json.dumps({
                                     'route': diagnostic.get('route'),
                                     'resource_mode': diagnostic.get('resource_mode'),
                                     'observer_schedule': diagnostic.get('observer_schedule'),
                                     'fast_forward': diagnostic.get('fast_forward'),
                                     'reflex': diagnostic.get('reflex'),
                                     'reasoning_effort': diagnostic.get('reasoning_effort'),
                                     'stage_marks_s': diagnostic.get('stage_marks_s'),
                                     'focal': diagnostic.get('focal'),
                                     'offers': offer_diagnostics,
                                 }, sort_keys=True))
                rows = r.store.rows(
                    "SELECT id,payload FROM packets WHERE event_id=? AND kind='OfferPacket' ORDER BY created",
                    (event['event_id'],))
                self.assertEqual(len(rows), 2)
                packets = [json.loads(row['payload']) for row in rows]
                self.assertEqual({item['role'] for item in packets}, {'B1_DETAIL', 'B2_GIST'})
                self.assertTrue(all(len(item['evidence_refs']) == 1 for item in packets))
                for item in packets:
                    self.assertEqual(r.store.read_source(item['evidence_refs'][0]), source)

                metadata = json.loads(answer['metadata'])
                packet_ids = {item['packet_id'] for item in packets}
                self.assertEqual(set(metadata['selected_offer_ids']), packet_ids)
                self.assertEqual(set(metadata['focal']['coalition']), packet_ids)
                self.assertEqual(len(sent), 1)
                c3_view = json.dumps(sent)
                self.assertIn('Cedar option A costs 11.', c3_view)
                self.assertIn('Cedar option B costs 17.', c3_view)
                self.assertIn('MODEL_HYPOTHESIS_NOT_FACT', c3_view)

                budget_rows = r.store.rows(
                    "SELECT metrics FROM telemetry WHERE event_id=? AND kind='native_body_budgeted_for_c3' ORDER BY id",
                    (event['event_id'],))
                self.assertEqual(len(budget_rows), 2)
                budgets = [json.loads(row['metrics']) for row in budget_rows]
                self.assertEqual({item['role'] for item in budgets}, {'B1_DETAIL', 'B2_GIST'})
                self.assertTrue(all(item['status'] == 'PREANSWER_BUDGETED' for item in budgets))
                self.assertTrue(all(abs(item['c3_reserved_seconds'] - 26.0) < .01 for item in budgets))
                self.assertTrue(all(item['recent_real_prefill_failures'] == 2 for item in budgets))
                self.assertEqual(r.cfg['learning_mode'], 'RECORD_ONLY')
                self.assertFalse(r.pool.pids())
            finally:
                r.close()


class LongTurnBudgetTests(unittest.TestCase):
    def test_ninety_second_composed_stage_splits_both_bodies_and_reserves_c3(self):
        # This file is executed from the final staged tree by
        # test_final_composed_runtime_and_native_success_contract, so these
        # imports exercise the composed module, not the source-tree policy.
        failed = {'status': 'DEADLINE', 'metadata': {'runner': {
            'role': 'C3_LANGUAGE', 'generated_tokens': 0, 'last_phase': 'prefill'}}}
        plan = native_budget.plan(
            100.0, 190.0, 100.0, recent=[failed, failed],
            background_enabled=True,
        )
        self.assertFalse(plan['recovery'])
        self.assertEqual(plan['reason'], 'NORMAL_COGNITIVE_PREANSWER')
        self.assertAlmostEqual(plan['preanswer_end_monotonic'], 140.5)
        self.assertAlmostEqual(plan['preanswer_seconds_available'], 40.5)
        self.assertAlmostEqual(plan['c3_reserved_seconds'], 49.5)
        self.assertFalse(plan['postcommit_body_eligible'])
        self.assertFalse(plan['age_changed'])
        self.assertFalse(plan['memory_or_native_weights_changed'])

        now = [100.0]
        seen = []
        schedule = obs.plan(obs.DEFAULT, ['B1_DETAIL', 'B2_GIST'], 'ninety-second-stage')

        def ask(role, peer, role_end=None):
            self.assertTrue(peer)
            self.assertIsNotNone(role_end)
            seconds = role_end - now[0]
            seen.append((role, seconds, role_end))
            now[0] = role_end
            return role

        offers = obs.run(
            schedule, ask, plan['preanswer_end_monotonic'],
            lambda role, exc: self.fail(f'{role} unexpectedly deferred: {exc}'),
            clock=lambda: now[0], budgeted=True,
        )
        self.assertEqual(offers, ['B1_DETAIL', 'B2_GIST'])
        self.assertEqual([item[0] for item in seen], ['B1_DETAIL', 'B2_GIST'])
        self.assertAlmostEqual(seen[0][1], 20.25, places=2)
        self.assertAlmostEqual(seen[1][1], 20.25, places=2)
        self.assertAlmostEqual(seen[0][2], 120.25, places=2)
        self.assertAlmostEqual(seen[1][2], 140.5, places=2)


if __name__ == '__main__':
    unittest.main()
