"""Run278 RED-first: operator-visible Sleep digest must not bypass source revocation.

Actual Runtime/SQLite/Operator with deterministic C3 seam; software evidence only.
No native inference, weights, Redmi, age or learning authority.
"""
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


class SleepDigestViewAuthorityRun278(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.sleep.cycle.set_policy('tick_seconds', '300')
        self.r.cfg['history_turns'] = 6
        self.r._route = Mock(return_value=('simple', {'source': 'RUN278_TEST_SEAM'}))
        self.r.learner.output_delta = Mock(return_value=None)
        self.r.pool.get = Mock(return_value=SimpleNamespace(
            role='C3_LANGUAGE', last_metrics={},
            generate=lambda messages, *a, **k: iter(['RUN278_SYNTHETIC_C3_REPLY']),
        ))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def turn(self, marker):
        self.r.submit('RUN278 human source marker ' + marker)
        deadline = time.monotonic() + 12
        while not self.r.idle() and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertTrue(self.r.idle())
        self.assertEqual(self.r.last_answer()['status'], 'FINAL')

    def prepare(self):
        for marker in ('ALPHA_278', 'BETA_278', 'GAMMA_278'):
            self.turn(marker)
        self.assertEqual(S.digest(self.r.store)['turns'], 3)
        self.assertEqual(S.view(self.r.store, self.r.session)['entries'], 3)

    def revoke(self, marker):
        source = self.r.store.one(
            'SELECT e.source_id FROM events e JOIN messages m ON m.event_id=e.id '
            "WHERE m.role='user' AND m.text LIKE ? LIMIT 1",
            ('%' + marker + '%',),
        )
        self.assertIsNotNone(source)
        with self.r.store.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (source['source_id'],))

    def test_valid_digest_remains_visible_through_operator(self):
        self.prepare()
        result = json.loads(Operator(self.r).run(':sleep digest'))
        self.assertEqual(result['entries'], 3)
        self.assertEqual(result['fact_authority'], 0)
        self.assertIn('ALPHA_278', result['text'])
        self.assertIn('GAMMA_278', result['text'])

    def test_deleted_source_is_not_exposed_by_sleep_digest_operator(self):
        self.prepare()
        self.revoke('GAMMA_278')
        result = json.loads(Operator(self.r).run(':sleep digest'))
        self.assertNotIn('GAMMA_278', result['text'])
        self.assertLess(result['entries'], 3)
        self.assertEqual(result['fact_authority'], 0)

    def test_transitive_revocation_cannot_leak_old_digest(self):
        self.prepare()
        self.revoke('ALPHA_278')
        result = json.loads(Operator(self.r).run(':sleep digest'))
        self.assertNotIn('ALPHA_278', result['text'])
        self.assertEqual(result['fact_authority'], 0)

    def test_forged_persisted_digest_is_not_shown_to_human(self):
        self.prepare()
        st, version = self.r.store.state(S.KEY, None)
        st['sessions'][self.r.session]['entries'][-1]['user'] = 'FORGED_RUN278_DIGEST'
        self.r.store.set_state(S.KEY, st, expected=version)
        result = json.loads(Operator(self.r).run(':sleep digest'))
        self.assertNotIn('FORGED_RUN278_DIGEST', result['text'])
        self.assertLess(result['entries'], 3)

    def test_cross_session_digest_copy_is_not_exposed(self):
        self.prepare()
        st, version = self.r.store.state(S.KEY, None)
        st['sessions']['RUN278_OTHER_SESSION'] = {
            'until': st['sessions'][self.r.session]['until'],
            'entries': list(st['sessions'][self.r.session]['entries']),
        }
        self.r.store.set_state(S.KEY, st, expected=version)
        result = S.view(self.r.store, 'RUN278_OTHER_SESSION')
        self.assertEqual(result['text'], '')
        self.assertEqual(result['entries'], 0)


if __name__ == '__main__':
    unittest.main()
