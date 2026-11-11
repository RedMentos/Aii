"""Real Runtime/SQLite integration for the isolated C5 feedback shadow adapter."""
import json
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from v13 import c5_feedback_shadow_store_candidate as shadow
from v13 import inputs
from v13.common import dumps
from v13.runtime import Runtime


class FeedbackShadowStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = self.open_runtime()

    def open_runtime(self):
        r = Runtime(self.home)
        r.sleep.cycle.set_policy('enabled', 'off')
        r._route = Mock(return_value=('simple', {'source': 'TEST_ROUTE_SEAM'}))
        r.pool.get = Mock(return_value=SimpleNamespace(role='C3_LANGUAGE', last_metrics={},
                                                       generate=lambda *a, **k: iter(['private answer'])))
        r.learner.output_delta = Mock(return_value=None)
        return r

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def answer(self, text='private question'):
        self.r.submit(text)
        until = time.monotonic() + 10
        while not self.r.idle() and time.monotonic() < until:
            time.sleep(.005)
        result = self.r.last_answer()
        self.assertEqual(result['status'], 'FINAL')
        return result['event_id']

    def rating(self, event, score, origin, note='private note'):
        # These tests exercise the standalone/reconciliation API directly.
        return inputs.record_rating(self.r.store, event, score, origin, note)

    def captured(self, event, origin):
        return shadow.capture(self.r.store, self.r.session, event, origin)

    def test_origin_correction_duplicate_restart_and_no_c5_write(self):
        event = self.answer()
        self.rating(event, 3, 'IMPLICIT_CHAT')
        c5_before = self.r.store.state('N4_C5_LEARNING')
        self.assertEqual(self.captured(event, 'IMPLICIT_CHAT')['status'], 'RECORDED')
        self.assertEqual(self.r.store.state('N4_C5_LEARNING'), c5_before)
        first = shadow.view(self.r.store, self.r.session)
        action = next(iter(first['by_action']))
        self.assertEqual(first['by_action'][action]['n'], 1)
        self.assertAlmostEqual(first['by_action'][action]['human_correction'], 7 / 9)
        duplicate = self.captured(event, 'IMPLICIT_CHAT')
        self.assertEqual((duplicate['status'], duplicate['version']), ('UNCHANGED', first['version']))

        self.rating(event, 10, 'EXPLICIT_NOTE')
        stale = shadow.view(self.r.store, self.r.session)
        self.assertEqual((stale['events'], stale['excluded']), (0, 1))
        self.captured(event, 'EXPLICIT_NOTE')
        explicit = shadow.view(self.r.store, self.r.session)
        self.assertEqual(explicit['by_action'][action], {'n': 1, 'human_approval': 1., 'human_correction': 0.})
        # A second submission of the same note has a new timestamp but must
        # still contribute only one effective event after reconciliation.
        self.rating(event, 10, 'EXPLICIT_NOTE')
        self.captured(event, 'EXPLICIT_NOTE')
        self.assertEqual(shadow.view(self.r.store, self.r.session)['by_action'][action]['n'], 1)
        self.rating(event, 8, 'IMPLICIT_CHAT')
        self.captured(event, 'IMPLICIT_CHAT')
        self.assertEqual(shadow.view(self.r.store, self.r.session)['by_action'][action],
                         {'n': 1, 'human_approval': 1., 'human_correction': 0.})
        self.rating(event, 1, 'EXPLICIT_NOTE')
        self.captured(event, 'EXPLICIT_NOTE')
        corrected = shadow.view(self.r.store, self.r.session)
        self.assertEqual(corrected['by_action'][action], {'n': 1, 'human_approval': 0., 'human_correction': 1.})
        self.assertEqual(corrected['learning_authority'], 0)
        saved = self.r.store.one('SELECT payload FROM states WHERE key=?', (shadow.KEY,))['payload']
        for private in ('private question', 'private answer', 'private note'):
            self.assertNotIn(private, saved)
        session = self.r.session
        self.r.close()
        self.r = self.open_runtime()
        self.assertEqual(self.r.session, session)
        self.assertEqual(shadow.view(self.r.store, session), corrected)

    def test_session_revocation_and_selection_tampering(self):
        event = self.answer()
        self.rating(event, 10, 'EXPLICIT_NOTE')
        self.captured(event, 'EXPLICIT_NOTE')
        saved_state = self.r.store.state(shadow.KEY)
        other = self.r.store.new_session('other')
        with self.assertRaises(ValueError):
            shadow.capture(self.r.store, other, event, 'EXPLICIT_NOTE')
        self.assertEqual(shadow.view(self.r.store, other)['events'], 0)
        source = self.r.store.one('SELECT source_id FROM events WHERE id=?', (event,))['source_id']
        with self.r.store.tx() as conn:
            conn.execute('UPDATE sources SET deleted=1 WHERE id=?', (source,))
        result = shadow.view(self.r.store, self.r.session)
        self.assertEqual((result['events'], result['excluded']), (0, 1))
        with self.assertRaises(ValueError):
            self.captured(event, 'EXPLICIT_NOTE')
        self.assertEqual(self.r.store.state(shadow.KEY), saved_state)
        with self.r.store.tx() as conn:
            conn.execute('UPDATE sources SET deleted=0 WHERE id=?', (source,))
            row = conn.execute("SELECT id,payload FROM packets WHERE kind='ActionSelection' AND event_id=? ORDER BY rowid DESC LIMIT 1", (event,)).fetchone()
            packet = json.loads(row['payload'])
            packet['selected']['action_id'] = 'B1_DETAIL'
            conn.execute('UPDATE packets SET payload=? WHERE id=?', (dumps(packet), row['id']))
        self.assertEqual(shadow.view(self.r.store, self.r.session)['events'], 0)
        with self.assertRaisesRegex(ValueError, 'binding changed'):
            self.captured(event, 'EXPLICIT_NOTE')

    def test_reconcile_transaction_rolls_back_both_states_on_failure(self):
        event = self.answer()
        self.rating(event, 10, 'EXPLICIT_NOTE')
        self.captured(event, 'EXPLICIT_NOTE')
        original_rating = self.r.store.state(shadow.RATINGS_KEY)
        original_shadow = self.r.store.state(shadow.KEY)
        with self.assertRaisesRegex(RuntimeError, 'abort'):
            with self.r.store.tx() as conn:
                payload = json.loads(conn.execute('SELECT payload FROM states WHERE key=?', (shadow.RATINGS_KEY,)).fetchone()['payload'])
                payload['ratings'][0]['score'] = 1
                conn.execute('UPDATE states SET version=version+1,payload=? WHERE key=?',
                             (dumps(payload), shadow.RATINGS_KEY))
                shadow.capture_in_tx(self.r.store, conn, self.r.session, event, 'EXPLICIT_NOTE')
                raise RuntimeError('abort')
        self.assertEqual(self.r.store.state(shadow.RATINGS_KEY), original_rating)
        self.assertEqual(self.r.store.state(shadow.KEY), original_shadow)
        with self.assertRaises(ValueError):
            shadow.capture_in_tx(self.r.store, self.r.store.db, self.r.session, event, 'EXPLICIT_NOTE')
        with self.r.store.tx() as conn:
            payload = json.loads(conn.execute('SELECT payload FROM states WHERE key=?', (shadow.RATINGS_KEY,)).fetchone()['payload'])
            payload['ratings'][0]['score'] = 1
            conn.execute('UPDATE states SET version=version+1,payload=? WHERE key=?',
                         (dumps(payload), shadow.RATINGS_KEY))
            shadow.capture_in_tx(self.r.store, conn, self.r.session, event, 'EXPLICIT_NOTE')
        self.assertEqual(next(iter(shadow.view(self.r.store, self.r.session)['by_action'].values())),
                         {'n': 1, 'human_approval': 0., 'human_correction': 1.})

    def test_revoked_supporting_context_excludes_evidence(self):
        event = self.answer()
        supporting = self.r.store.source('private supporting fact')
        with self.r.store.tx() as conn:
            row = conn.execute("SELECT id,metadata FROM messages WHERE event_id=? AND role='assistant'", (event,)).fetchone()
            meta = json.loads(row['metadata'])
            meta['context_source_refs'].append(supporting)
            conn.execute('UPDATE messages SET metadata=? WHERE id=?', (dumps(meta), row['id']))
        self.rating(event, 9, 'EXPLICIT_NOTE')
        self.captured(event, 'EXPLICIT_NOTE')
        self.assertEqual(shadow.view(self.r.store, self.r.session)['events'], 1)
        with self.r.store.tx() as conn:
            conn.execute('UPDATE sources SET deleted=1 WHERE id=?', (supporting['source_id'],))
        report = shadow.view(self.r.store, self.r.session)
        self.assertEqual((report['events'], report['excluded']), (0, 1))
        with self.assertRaises(ValueError):
            self.captured(event, 'EXPLICIT_NOTE')

    def test_changed_answer_metadata_invalidates_the_captured_binding(self):
        event = self.answer()
        self.rating(event, 9, 'EXPLICIT_NOTE')
        self.captured(event, 'EXPLICIT_NOTE')
        with self.r.store.tx() as conn:
            row = conn.execute("SELECT id,metadata FROM messages WHERE event_id=? AND role='assistant'", (event,)).fetchone()
            metadata = json.loads(row['metadata'])
            metadata['model_revision'] = 'different-review-revision'
            conn.execute('UPDATE messages SET metadata=? WHERE id=?', (dumps(metadata), row['id']))
        report = shadow.view(self.r.store, self.r.session)
        self.assertEqual((report['events'], report['excluded']), (0, 1))
        with self.assertRaisesRegex(ValueError, 'binding changed'):
            self.captured(event, 'EXPLICIT_NOTE')

    def test_answer_text_must_match_its_committed_candidate_hash(self):
        event = self.answer()
        with self.r.store.tx() as conn:
            conn.execute("UPDATE messages SET text=? WHERE event_id=? AND role='assistant'", ('changed answer', event))
        self.rating(event, 9, 'EXPLICIT_NOTE')
        with self.assertRaisesRegex(ValueError, 'answer content binding'):
            self.captured(event, 'EXPLICIT_NOTE')
        self.assertIsNone(self.r.store.state(shadow.KEY, None)[0])

    def test_origin_breakdown_preserves_implicit_and_explicit_evidence(self):
        event = self.answer()
        self.rating(event, 3, 'IMPLICIT_CHAT')
        self.captured(event, 'IMPLICIT_CHAT')
        self.rating(event, 10, 'EXPLICIT_NOTE')
        self.captured(event, 'EXPLICIT_NOTE')
        report = shadow.view(self.r.store, self.r.session)
        self.assertEqual(report['origin_counts'], {'EXPLICIT_NOTE': 1, 'IMPLICIT_CHAT': 1})
        explicit = next(iter(report['by_origin']['EXPLICIT_NOTE'].values()))
        implicit = next(iter(report['by_origin']['IMPLICIT_CHAT'].values()))
        self.assertEqual(explicit, {'n': 1, 'human_approval': 1., 'human_correction': 0.})
        self.assertAlmostEqual(implicit['human_correction'], 7 / 9)
        self.assertEqual(next(iter(report['by_action'].values())), explicit)

    def test_duplicate_concurrent_delivery_is_one_event(self):
        event = self.answer()
        self.rating(event, 8, 'EXPLICIT_NOTE')
        with ThreadPoolExecutor(max_workers=4) as pool:
            statuses = list(pool.map(lambda _: self.captured(event, 'EXPLICIT_NOTE')['status'], range(8)))
        self.assertEqual(statuses.count('RECORDED'), 1)
        self.assertEqual(statuses.count('UNCHANGED'), 7)
        result = shadow.view(self.r.store, self.r.session)
        self.assertEqual((result['events'], result['excluded']), (1, 0))
        self.assertEqual(next(iter(result['by_action'].values()))['n'], 1)

    def test_concurrent_rating_corrections_remain_bound_to_latest_row(self):
        event = self.answer()
        self.rating(event, 8, 'EXPLICIT_NOTE')
        self.captured(event, 'EXPLICIT_NOTE')

        def correct(score):
            with self.r.store.tx() as conn:
                row = conn.execute('SELECT payload FROM states WHERE key=?', (shadow.RATINGS_KEY,)).fetchone()
                payload = json.loads(row['payload'])
                payload['ratings'][0]['score'] = score
                conn.execute('UPDATE states SET version=version+1,payload=? WHERE key=?',
                             (dumps(payload), shadow.RATINGS_KEY))
                shadow.capture_in_tx(self.r.store, conn, self.r.session, event, 'EXPLICIT_NOTE')

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(correct, [1, 10, 2, 9, 3, 8, 4, 7]))
        score = self.r.store.state(shadow.RATINGS_KEY)[0]['ratings'][0]['score']
        report = shadow.view(self.r.store, self.r.session)
        self.assertEqual((report['events'], report['excluded']), (1, 0))
        actual = next(iter(report['by_action'].values()))
        u = (score - 1) / 9
        self.assertEqual(actual['n'], 1)
        self.assertEqual(actual['human_approval'], u if u >= .5 else 0.)
        self.assertEqual(actual['human_correction'], 1 - u if u < .5 else 0.)


if __name__ == '__main__':
    unittest.main()
