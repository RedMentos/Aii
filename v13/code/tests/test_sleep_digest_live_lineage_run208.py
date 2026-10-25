"""Run208: live C3 compressed digest must be source-bound, not a trusted cache.

Actual Runtime/Store/ContextOS with deterministic C3 seam; no native model run.
"""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from v13.runtime import Runtime
from v13 import sleep_offline as S


class LiveDigestLineageRun208(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.sleep.cycle.set_policy('tick_seconds', '300')
        self.r.cfg['history_turns'] = 6
        self.captured = []
        self.r._route = Mock(return_value=('simple', {'source': 'TEST_ROUTE_SEAM'}))
        self.r.learner.output_delta = Mock(return_value=None)
        def generate(messages, *a, **k):
            self.captured.append(messages)
            yield 'synthetic response'
        self.r.pool.get = Mock(return_value=SimpleNamespace(role='C3_LANGUAGE', last_metrics={}, generate=generate))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def turn(self, user):
        self.r.submit(user)
        deadline = time.monotonic() + 12
        while not self.r.idle() and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertTrue(self.r.idle())
        self.assertEqual(self.r.last_answer()['status'], 'FINAL')

    def prepare(self):
        for marker in ('ALPHA_208', 'BETA_208', 'GAMMA_208'):
            self.turn('Run208 synthetic source-bound context marker ' + marker)
        self.assertEqual(S.digest(self.r.store)['turns'], 3)
        self.r.cfg['history_turns'] = 0  # force digest path on the next live turn
        self.assertEqual(len(S.context_items(self.r.store, self.r.session)), 3)

    def test_forged_digest_text_cannot_enter_live_c3_system_context(self):
        self.prepare()
        st, version = self.r.store.state(S.KEY, None)
        st['sessions'][self.r.session]['entries'][0]['user'] = 'FORGED_RUN208_CONTEXT'
        self.r.store.set_state(S.KEY, st, expected=version)
        self.assertNotIn('FORGED_RUN208', '\n'.join(S.context_items(self.r.store, self.r.session)))
        self.turn('Run208 live probe after digest tamper')
        system = '\n'.join(m['content'] for m in self.captured[-1] if m['role'] == 'system')
        self.assertNotIn('FORGED_RUN208', system)

    def test_revoked_earlier_source_invalidates_transitively_dependent_digest(self):
        self.prepare()
        source = self.r.store.one(
            'SELECT e.source_id FROM events e JOIN messages m ON m.event_id=e.id '
            "WHERE m.role='user' AND m.text LIKE ? LIMIT 1", ('%ALPHA_208%',)
        )
        self.assertIsNotNone(source)
        with self.r.store.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (source['source_id'],))
        text = '\n'.join(S.context_items(self.r.store, self.r.session))
        self.assertNotIn('ALPHA_208', text)
        self.assertNotIn('BETA_208', text, 'later answer depends on revoked earlier context')

    def test_digest_message_id_must_match_its_event_and_source(self):
        self.prepare()
        st, version = self.r.store.state(S.KEY, None)
        entries = st['sessions'][self.r.session]['entries']
        entries[0]['msg'] = entries[1]['msg']
        self.r.store.set_state(S.KEY, st, expected=version)
        text = '\n'.join(S.context_items(self.r.store, self.r.session))
        self.assertNotIn('ALPHA_208', text)


if __name__ == '__main__':
    unittest.main()
