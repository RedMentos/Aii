"""Real Runtime/SQLite with synthetic model outputs; no native/Redmi proof."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch as mock_patch

from scripts import postcommit_observer_candidate_20261116 as patch
from v13.common import Cancelled, Limits
from v13.operator import Operator


CODE = Path(__file__).resolve().parents[1]
QUESTION = ("Compare details with planning. The rent is 120 euros. "
            "The plan preserves a long-term reserve.")


def runtime_class(patched=True):
    if patched and os.environ.get('V13_TEST_POSTCOMMIT_STAGE') == '1':
        from v13.runtime import Runtime
        return Runtime
    raw = (CODE / 'v13/runtime.py').read_bytes()
    source = patch.apply_source(raw) if patched else raw
    module = types.ModuleType('v13.postcommit_disposable_runtime')
    module.__package__ = 'v13'
    exec(compile(source, 'postcommit_disposable_runtime.py', 'exec'), module.__dict__)
    return module.Runtime


class PinValidation(unittest.TestCase):
    def test_each_reviewed_source_is_accepted_and_original_is_unchanged(self):
        from scripts import integrated_online_world_candidate_20261110 as world
        from scripts import termux_runtime_recovery_candidate_20261112 as termux
        raw = (CODE / 'v13/runtime.py').read_bytes()
        sources = (raw, world.build_sources(CODE)['v13/runtime.py'],
                   termux.build_sources(CODE, include_postcommit=False)['v13/runtime.py'])
        self.assertTrue({hashlib.sha256(x).hexdigest() for x in sources}
                        <= patch.SOURCE_SHA256)
        for source in sources:
            with self.subTest(source=hashlib.sha256(source).hexdigest()):
                result = patch.apply_source(source)
                # Exact pinned sources may already contain some/all reviewed
                # post-commit replacements; applying the overlay is idempotent.
                self.assertEqual(result, patch.apply_source(source))
                self.assertEqual(result.count(b'foreground_body_attempts=set()'), 1)
                self.assertEqual(result.count(b'deferred_wake_route=None'), 1)
                if b'foreground_body_attempts=set()' not in source:
                    self.assertNotEqual(result, source)
        self.assertEqual((CODE / 'v13/runtime.py').read_bytes(), raw)

    def test_changed_unknown_and_wrong_type_fail_closed(self):
        raw = (CODE / 'v13/runtime.py').read_bytes()
        for changed in (raw + b'\n# mutation\n', raw[:-1], b''):
            with self.subTest(length=len(changed)), self.assertRaisesRegex(ValueError, 'hash mismatch'):
                patch.apply_source(changed)
        with self.assertRaises(TypeError):
            patch.apply_source(raw.decode())


class FakeRunner:
    def __init__(self, case, role):
        self.case = case
        self.role = role
        self.last_metrics = {'status': 'FINAL', 'role': role, 'synthetic': True}

    def generate(self, messages, cancel, deadline, *args, **kwargs):
        current = self.case.runtime.store.one(
            "SELECT status FROM messages WHERE role='assistant' ORDER BY id DESC LIMIT 1")
        state = current['status'] if current else 'MISSING'
        self.case.calls.append((self.role, state))
        behavior = self.case.behavior(self.role, state)
        if behavior == 'expire':
            time.sleep(max(0., deadline - time.monotonic()))
            behavior = 'fail'
        if behavior == 'cancel':
            cancel.set()
            raise Cancelled('synthetic user cancellation')
        if behavior == 'fail':
            self.last_metrics = {'status': 'DEADLINE', 'role': self.role, 'synthetic': True}
            raise Limits('synthetic observer failure')
        if self.role == 'B1_DETAIL':
            yield json.dumps({'summary': 'The rent is 120 euros.',
                              'quotes': ['The rent is 120 euros.'],
                              'uncertainty': 'low', 'needs_reentry': False})
        elif self.role == 'B2_GIST':
            yield json.dumps({'summary': 'The plan needs a reserve.',
                              'quotes': ['The plan preserves a long-term reserve.'],
                              'uncertainty': 'low', 'needs_reentry': False})
        else:
            yield 'One combined response.'


class RuntimePostcommit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = runtime_class()(Path(self.tmp.name))
        self.runtime.cfg.update(deadline_seconds=90, observer_seconds=4.4,
                                observer_mode='background', observer_schedule='A_THEN_B_SEQUENTIAL',
                                b2_quote_select='off', offer_quote_context_chars=0, b2_state_slots=0)
        self.runtime.sleep.cycle.set_policy('enabled', 'off')
        self.runtime.online_world_update = Mock(return_value={'status': 'TEST_DISABLED'})
        Operator(self.runtime).run(':effort max')
        self.runtime._route = Mock(return_value=('both', {'source': 'TEST_BOTH'}))
        self.runtime.learner.output_delta = Mock(return_value=None)
        self.calls = []
        self.behavior = lambda role, state: 'ok'
        self.runners = {}

        def get(role):
            if role not in self.runners:
                self.runners[role] = FakeRunner(self, role)
            return self.runners[role]

        self.runtime.pool.get = Mock(side_effect=get)

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def turn(self):
        event = self.runtime.submit(QUESTION)
        until = time.monotonic() + 15
        while not self.runtime.idle() and time.monotonic() < until:
            time.sleep(.01)
        self.assertTrue(self.runtime.idle(), 'runtime did not settle')
        answer = self.runtime.store.one(
            "SELECT * FROM messages WHERE event_id=? AND role='assistant'", (event,))
        self.assertEqual((answer['status'], answer['text']), ('FINAL', 'One combined response.'))
        return event, json.loads(answer['metadata'])

    def test_timed_out_first_foreground_body_gives_other_first_postcommit(self):
        self.runtime.cfg.update(deadline_seconds=10, observer_seconds=4.4)
        self.behavior = lambda role, status: ('expire' if status != 'FINAL' else 'fail') if role == 'B1_DETAIL' else 'ok'
        event, meta = self.turn()
        self.assertEqual(self.calls, [('B1_DETAIL', 'DRAFT'), ('C3_LANGUAGE', 'DRAFT'),
                                      ('B2_GIST', 'FINAL'), ('B1_DETAIL', 'FINAL')])
        self.assertEqual(meta['selected_offer_ids'], [])
        offers = [json.loads(r['payload']) for r in self.runtime.store.rows(
            "SELECT payload FROM packets WHERE event_id=? AND kind='OfferPacket'", (event,))]
        self.assertEqual([p['role'] for p in offers], ['B2_GIST'])
        row = self.runtime.store.one(
            "SELECT metrics FROM telemetry WHERE event_id=? AND kind='postcommit_offer'", (event,))
        self.assertFalse(json.loads(row['metrics'])['affects_committed_output'])

    def test_one_foreground_offer_only_retries_the_missing_body(self):
        count = 0
        def behavior(role, status):
            nonlocal count
            if role == 'B2_GIST':
                count += 1
                return 'fail' if count == 1 else 'ok'
            return 'ok'
        self.behavior = behavior
        event, meta = self.turn()
        self.assertEqual(self.calls, [('B1_DETAIL', 'DRAFT'), ('B2_GIST', 'DRAFT'),
                                      ('C3_LANGUAGE', 'DRAFT'), ('B2_GIST', 'FINAL')])
        rows = self.runtime.store.rows(
            "SELECT payload FROM packets WHERE event_id=? AND kind='OfferPacket' ORDER BY rowid", (event,))
        offers = [json.loads(row['payload']) for row in rows]
        self.assertEqual([p['role'] for p in offers], ['B1_DETAIL', 'B2_GIST'])
        self.assertNotIn(offers[1]['packet_id'], meta['selected_offer_ids'])
        self.assertEqual(self.runtime.store.read_source(offers[1]['evidence_refs'][0]),
                         'The plan preserves a long-term reserve.')

    def test_failed_postcommit_body_does_not_starve_other(self):
        self.runtime.cfg['observer_schedule'] = 'JEF_FIRST_THEN_BOTH'
        self.behavior = lambda role, status: 'fail' if role == 'B1_DETAIL' else 'ok'
        self.turn()
        self.assertEqual(self.calls, [('C3_LANGUAGE', 'DRAFT'), ('B1_DETAIL', 'FINAL'), ('B2_GIST', 'FINAL')])

    def test_user_one_body_effort_never_starts_other_body(self):
        for mode, allowed in [('detail', 'B1_DETAIL'), ('gist', 'B2_GIST')]:
            with self.subTest(mode=mode):
                Operator(self.runtime).run(':effort ' + mode)
                self.calls.clear()
                self.behavior = lambda role, status: 'fail' if role == allowed and status == 'DRAFT' else 'ok'
                self.turn()
                self.assertTrue(any(role == allowed for role, _ in self.calls))
                self.assertFalse(any(role in {'B1_DETAIL', 'B2_GIST'} and role != allowed for role, _ in self.calls))

    def test_resolved_learned_wake_cannot_expand_past_single_body(self):
        Operator(self.runtime).run(':effort adaptive')
        original = self.runtime.learner.decide
        def decide(kind, *args, **kwargs):
            if kind == 'wake':
                return {'learned': True, 'action': 'both'}
            return original(kind, *args, **kwargs)
        self.runtime.learner.decide = decide
        self.runtime.cfg['observer_schedule'] = 'JEF_FIRST_THEN_BOTH'
        self.runtime._route = Mock(return_value=('simple', {'source': 'TEST_SIMPLE'}))
        self.turn()
        row = self.runtime.store.one("SELECT payload FROM packets WHERE kind='EffortDecision' ORDER BY rowid DESC LIMIT 1")
        resolved = json.loads(row['payload'])['wake']
        allowed = {'none': set(), 'detail': {'B1_DETAIL'}, 'gist': {'B2_GIST'},
                   'both': {'B1_DETAIL', 'B2_GIST'}}[resolved]
        self.assertTrue({role for role, _ in self.calls if role.startswith('B')} <= allowed)

    def test_cancel_queue_and_pause_stop_following_body(self):
        for reason in ('cancel', 'queue', 'pause'):
            with self.subTest(reason=reason):
                self.runtime.cfg['observer_schedule'] = 'JEF_FIRST_THEN_BOTH'
                self.calls.clear()
                def behavior(role, status):
                    if role == 'B1_DETAIL' and status == 'FINAL':
                        if reason == 'cancel':
                            return 'cancel'
                        if reason == 'queue':
                            self.runtime.jobs.put_nowait(('synthetic_queue_test', None, 0, time.monotonic()))
                        if reason == 'pause':
                            self.runtime.paused = True
                        return 'fail'
                    return 'ok'
                self.behavior = behavior
                self.turn()
                self.assertEqual(self.calls, [('C3_LANGUAGE', 'DRAFT'), ('B1_DETAIL', 'FINAL')])
                self.runtime.paused = False
                self.runtime.cancel_event.clear()
                self.runtime.wake.set()

    def test_new_yellow_resource_limit_applies_after_first_attempt(self):
        self.runtime.cfg['observer_schedule'] = 'JEF_FIRST_THEN_BOTH'
        def behavior(role, status):
            if role == 'B1_DETAIL' and status == 'FINAL':
                self.runtime.guard.state = 'NORMAL'
                self.runtime.guard._mode = ('NORMAL', 'YELLOW')
                self.runtime.guard.update = lambda resources: 'NORMAL'
                return 'fail'
            return 'ok'
        self.behavior = behavior
        self.turn()
        self.assertEqual(self.calls, [('C3_LANGUAGE', 'DRAFT'), ('B1_DETAIL', 'FINAL')])

    def test_on_demand_stays_without_postcommit_calls(self):
        self.runtime.cfg['observer_schedule'] = 'ON_DEMAND_REENTRY'
        self.turn()
        self.assertEqual(self.calls, [('C3_LANGUAGE', 'DRAFT')])


    def test_timeout_reflex_defers_only_the_authorized_body(self):
        from v13 import reflex as reflexctl
        Operator(self.runtime).run(':effort detail')
        self.runtime._route = Mock(return_value=('detail', {'source': 'TEST_DETAIL'}))
        reflexctl.controller(self.runtime).timeout_check = Mock(
            return_value={'reflex': 'imminent_timeout'})
        self.turn()
        self.assertEqual(self.calls, [('C3_LANGUAGE', 'DRAFT'), ('B1_DETAIL', 'FINAL')])


    @unittest.skipUnless(os.environ.get('V13_TEST_POSTCOMMIT_STAGE') == '1',
                         'requires composed LateWatch stage')
    def test_latewatch_respects_user_one_body_effort(self):
        for mode, allowed in [('detail', 'B1_DETAIL'), ('gist', 'B2_GIST')]:
            with self.subTest(mode=mode):
                Operator(self.runtime).run(':effort ' + mode)
                self.runtime._route = Mock(return_value=(mode, {'source': 'TEST_EFFORT'}))
                self.calls.clear()
                self.behavior = lambda role, status: 'ok'
                with mock_patch('v13.latewatch.residency', return_value=None):
                    self.turn()
                body_calls = [role for role, _ in self.calls if role.startswith('B')]
                self.assertTrue(body_calls)
                self.assertTrue(all(role == allowed for role in body_calls), body_calls)


if __name__ == '__main__':
    unittest.main()
