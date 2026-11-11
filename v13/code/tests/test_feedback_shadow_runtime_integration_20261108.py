"""The real rating writer captures bound SHADOW feedback without blocking ratings."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch
import time
import unittest

from v13 import c5_feedback_shadow_store_candidate as shadow, inputs
from v13.operator import Operator
from v13.runtime import Runtime


class FeedbackShadowRuntimeIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy('enabled', 'off')
        self.runtime._route = Mock(return_value=('simple', {'source': 'TEST_ROUTE_SEAM'}))
        self.runtime.pool.get = Mock(return_value=SimpleNamespace(
            role='C3_LANGUAGE', last_metrics={}, generate=lambda *a, **k: iter(['answer'])))
        self.runtime.learner.output_delta = Mock(return_value=None)
        self.runtime.submit('question')
        until = time.monotonic() + 10
        while not self.runtime.idle() and time.monotonic() < until:
            time.sleep(.005)
        answer = self.runtime.last_answer()
        self.assertEqual(answer['status'], 'FINAL')
        self.event = answer['event_id']
        self.assertFalse(shadow.capture_enabled(self.runtime.store))
        with self.assertRaises(PermissionError):
            shadow.set_capture_enabled(self.runtime.store, True)
        Operator(self.runtime).run(':c5 feedback-shadow on')

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def test_real_rating_captures_origins_and_explicit_precedence(self):
        store = self.runtime.store
        inputs.record_rating(store, self.event, 3, 'IMPLICIT_CHAT')
        first = shadow.view(store, self.runtime.session)
        self.assertEqual((first['events'], first['excluded']), (1, 0))
        self.assertEqual(first['origin_counts']['IMPLICIT_CHAT'], 1)
        inputs.record_rating(store, self.event, 10, 'EXPLICIT_NOTE')
        result = shadow.view(store, self.runtime.session)
        self.assertEqual(result['origin_counts'], {'EXPLICIT_NOTE': 1, 'IMPLICIT_CHAT': 1})
        self.assertEqual(next(iter(result['by_action'].values())),
                         {'n': 1, 'human_approval': 1., 'human_correction': 0.})
        self.assertEqual(result['learning_authority'], 0)
        session = self.runtime.session
        self.runtime.close()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy('enabled', 'off')
        self.assertEqual(self.runtime.session, session)
        self.assertTrue(shadow.capture_enabled(self.runtime.store))
        self.assertEqual(shadow.view(self.runtime.store, session), result)

    def test_operator_can_disable_and_reenable_capture(self):
        store = self.runtime.store
        Operator(self.runtime).run(':c5 feedback-shadow off')
        inputs.record_rating(store, self.event, 3, 'IMPLICIT_CHAT')
        self.assertIsNone(store.state(shadow.KEY, None)[0])
        self.assertEqual(inputs.ratings(store)[-1]['score'], 3)
        Operator(self.runtime).run(':c5 feedback-shadow on')
        inputs.record_rating(store, self.event, 10, 'EXPLICIT_NOTE')
        report = shadow.view(store, self.runtime.session)
        self.assertEqual(report['events'], 1)
        self.assertEqual(report['origin_counts'], {'EXPLICIT_NOTE': 1, 'IMPLICIT_CHAT': 1})

    def test_invalid_policy_fails_closed_and_can_be_disabled(self):
        store = self.runtime.store
        with store.tx() as conn:
            conn.execute('UPDATE states SET payload=? WHERE key=?', ('{}', shadow.POLICY_KEY))
        inputs.record_rating(store, self.event, 3, 'EXPLICIT_NOTE')
        self.assertEqual(inputs.ratings(store)[-1]['score'], 3)
        self.assertIsNone(store.state(shadow.KEY, None)[0])
        with self.assertRaises(ValueError):
            Operator(self.runtime).run(':c5 feedback-shadow on')
        Operator(self.runtime).run(':c5 feedback-shadow off')
        self.assertFalse(shadow.capture_enabled(store))

    def test_shadow_failure_rolls_back_its_writes_but_keeps_rating_and_fanout(self):
        store = self.runtime.store
        def partial_write_then_fail(store_arg, conn, session_id, event_id, origin):
            conn.execute('INSERT INTO states VALUES (?,?,?)', (shadow.KEY, 1, '{}'))
            raise ValueError('synthetic candidate failure')
        with patch.object(shadow, 'capture_in_tx', side_effect=partial_write_then_fail) as capture, \
                patch('v13.actionlearn.on_rating') as c5:
            row = inputs.record_rating(store, self.event, 7, 'EXPLICIT_NOTE')
        self.assertEqual(row['score'], 7)
        self.assertEqual(inputs.ratings(store)[-1]['score'], 7)
        self.assertIsNone(store.state(shadow.KEY, None)[0])
        capture.assert_called_once()
        c5.assert_called_once_with(store, self.event, 7)

    def test_interruption_rolls_back_rating_and_shadow_together(self):
        store = self.runtime.store
        def interrupt_after_partial_write(store_arg, conn, session_id, event_id, origin):
            conn.execute('INSERT INTO states VALUES (?,?,?)', (shadow.KEY, 1, '{}'))
            raise KeyboardInterrupt()
        with patch.object(shadow, 'capture_in_tx', side_effect=interrupt_after_partial_write):
            with self.assertRaises(KeyboardInterrupt):
                inputs.record_rating(store, self.event, 7, 'EXPLICIT_NOTE')
        self.assertEqual(inputs.ratings(store), [])
        self.assertIsNone(store.state(shadow.KEY, None)[0])

    def test_failed_correction_capture_cannot_leave_old_feedback_active(self):
        store = self.runtime.store
        inputs.record_rating(store, self.event, 9, 'EXPLICIT_NOTE')
        self.assertEqual(shadow.view(store, self.runtime.session)['events'], 1)
        with patch.object(shadow, 'capture_in_tx', side_effect=ValueError('synthetic failure')):
            inputs.record_rating(store, self.event, 1, 'EXPLICIT_NOTE')
        report = shadow.view(store, self.runtime.session)
        self.assertEqual((report['events'], report['excluded']), (0, 1))
        self.assertEqual(inputs.ratings(store)[-1]['score'], 1)

    def test_revoked_source_excludes_shadow_without_erasing_rating(self):
        store = self.runtime.store
        inputs.record_rating(store, self.event, 9, 'EXPLICIT_NOTE')
        source = store.one('SELECT source_id FROM events WHERE id=?', (self.event,))['source_id']
        with store.tx() as conn:
            conn.execute('UPDATE sources SET deleted=1 WHERE id=?', (source,))
        report = shadow.view(store, self.runtime.session)
        self.assertEqual((report['events'], report['excluded']), (0, 1))
        self.assertEqual(inputs.ratings(store)[-1]['score'], 9)

    def test_concurrent_corrections_match_the_persisted_latest_rating(self):
        store = self.runtime.store
        with patch('v13.agi.live.on_rating'), patch('v13.jefbridge.on_rating'), \
                patch('v13.actionlearn.on_rating'), patch('v13.deliberation.on_rating'), \
                patch('v13.callosum.on_rating'):
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda score: inputs.record_rating(store, self.event, score, 'EXPLICIT_NOTE'),
                              [1, 10, 2, 9, 3, 8]))
        rating = inputs.ratings(store)[-1]['score']
        result = shadow.view(store, self.runtime.session)
        self.assertEqual((result['events'], result['excluded']), (1, 0))
        value = next(iter(result['by_action'].values()))
        u = (rating - 1) / 9
        self.assertEqual(value['n'], 1)
        self.assertEqual(value['human_approval'], u if u >= .5 else 0.)
        self.assertEqual(value['human_correction'], 1 - u if u < .5 else 0.)


if __name__ == '__main__':
    unittest.main()
