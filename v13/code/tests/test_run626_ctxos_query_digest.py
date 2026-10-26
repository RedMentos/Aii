"""Run626: opt-in query-conditioned source-valid Sleep A Context OS selection."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from v13.runtime import Runtime
from v13.operator import Operator
from v13 import sleep_offline as S
from tests import test_run609_sleep_digest_backlog as backlog


TOPICS = (
    'The amber lantern hangs beside the eastern bridge.',
    'The silver compass points toward the northern valley.',
    'The green telescope belongs in the observatory.',
    'The copper kettle rests near the garden bench.',
    'The blue notebook contains the orchard sketch.',
    'The violet umbrella stays inside the hallway.',
    'The marble statue faces the central fountain.',
    'The wooden violin belongs to the music studio.',
    'The yellow bicycle stands behind the library.',
    'The red teapot sits beside the window.',
    'The white scarf hangs above the staircase.',
    'The black lantern is stored near the cellar.',
)
QUERY = 'Where does the amber lantern hang?'


class QueryDigestTests(unittest.TestCase):
    setUp = backlog.SleepBacklog.setUp
    tearDown = backlog.SleepBacklog.tearDown

    def turn_text(self, text):
        self.r.submit(text)
        until = time.monotonic() + 10
        while not self.r.idle() and time.monotonic() < until:
            time.sleep(.003)
        self.assertTrue(self.r.idle())
        self.assertIsNotNone(self.r.last_answer())

    def seed(self):
        for t in TOPICS:
            self.turn_text(t)
        self.assertEqual(S.digest(self.r.store)['turns'], len(TOPICS))

    def selected(self, mode, query=QUERY, cap=170):
        return S.context_items(self.r.store, self.r.session, cap=cap,
                               selection=mode, query=query)

    def test_source_recall_oldest_query_vs_recent_and_no_match_fallback(self):
        self.seed()
        recent = self.selected('recent')
        selected = self.selected('query')
        self.assertNotIn('amber lantern', '\n'.join(recent).lower())
        self.assertIn('amber lantern', '\n'.join(selected).lower())
        self.assertNotIn('black lantern', '\n'.join(selected).lower())
        self.assertLessEqual(sum(len(x) for x in selected), 170)
        self.assertEqual(self.selected('query', 'zzyzx unmatched'), recent)
        self.assertEqual(S.context_items(self.r.store, self.r.session, cap=170), recent)
        self.assertEqual(S.view(self.r.store, self.r.session)['fact_authority'], 0)

    def test_operator_idle_only_persistent_selection_and_restart(self):
        status = json.loads(Operator(self.r).run(':ctxos status'))
        self.assertEqual(status['digest_selection'], 'recent')
        self.assertEqual(json.loads(Operator(self.r).run(':ctxos digest select query')),
                         {'digest_selection': 'query'})
        self.assertEqual(json.loads(Operator(self.r).run(':ctxos status'))['digest_selection'], 'query')
        with self.assertRaises(ValueError):
            Operator(self.r).run(':ctxos digest select wrong')
        with self.r.lock:
            self.r.current = 'turn'
            try:
                with self.assertRaises(ValueError):
                    Operator(self.r).run(':ctxos digest select recent')
            finally:
                self.r.current = None
        self.assertEqual(json.loads(Operator(self.r).run(':ctxos status'))['digest_selection'], 'query')
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.assertEqual(json.loads(Operator(self.r).run(':ctxos status'))['digest_selection'], 'query')
        self.assertEqual(json.loads(Operator(self.r).run(':ctxos digest select recent')),
                         {'digest_selection': 'recent'})

    def test_actual_mocked_c3_turn_receives_selected_source_only_when_opted_in(self):
        self.seed()
        self.r.cfg['history_turns'] = 1
        seen = []
        def gen(messages, *args, **kwargs):
            seen.append(json.dumps(messages))
            yield 'Source-grounded response placeholder, not model quality proof.'
        self.r.pool.get = Mock(return_value=SimpleNamespace(
            role='C3_LANGUAGE', last_metrics={}, generate=gen))
        Operator(self.r).run(':ctxos digest select query')
        self.turn_text(QUERY)
        self.assertTrue(seen)
        self.assertIn('amber lantern', seen[-1].lower())
        self.assertNotIn('black lantern', seen[-1].lower())
        self.assertEqual(json.loads(self.r.last_answer()['metadata'])['digest_lines'], 1)

    def test_equal_lexical_score_prefers_newer_and_bounded_cap(self):
        self.turn_text('The amber lantern hangs by the eastern bridge.')
        self.turn_text('The amber lantern hangs by the western bridge.')
        S.digest(self.r.store)
        selected = self.selected('query', 'amber lantern', cap=180)
        self.assertEqual(len(selected), 1)
        self.assertIn('western bridge', selected[0])
        self.assertNotIn('eastern bridge', selected[0])

    def test_invalid_query_selector_fails_without_state_mutation(self):
        self.turn_text('Source-bound first turn.')
        S.digest(self.r.store)
        before = self.r.store.state(S.KEY, None)
        for opts in ({'selection': 'semantic', 'query': QUERY},
                     {'selection': 'query', 'query': None},
                     {'selection': 'query', 'query': 'x' * 8193}):
            with self.subTest(opts=str(opts)[:30]), self.assertRaises(ValueError):
                S.context_items(self.r.store, self.r.session, **opts)
        self.assertEqual(self.r.store.state(S.KEY, None), before)

    def test_revoked_source_and_other_session_never_surface(self):
        self.seed()
        self.assertIn('amber lantern', '\n'.join(self.selected('query')).lower())
        event = self.r.store.one(
            "SELECT event_id FROM messages WHERE session_id=? AND role='user' ORDER BY id LIMIT 1",
            (self.r.session,))
        source = self.r.store.one('SELECT source_id FROM events WHERE id=?', (event['event_id'],))
        with self.r.store.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (source['source_id'],))
        self.assertNotIn('amber lantern', '\n'.join(self.selected('query')).lower())
        Operator(self.r).run(':new')
        self.assertEqual(self.selected('query'), [])


if __name__ == '__main__':
    unittest.main()
