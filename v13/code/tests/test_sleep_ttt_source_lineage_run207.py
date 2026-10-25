"""Run207: Stage-only Sleep TTT must not re-export revoked or forged context.

Uses actual Runtime/Store/Sleep source in GitHub CI with a deterministic C3 seam.
No model weights, learning permission, native inference, or age promotion.
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


class SleepTTTSourceLineageRun207(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.sleep.cycle.set_policy('tick_seconds', '300')
        self.r._route = Mock(return_value=('simple', {'source': 'TEST_ROUTE_SEAM'}))
        self.r.learner.output_delta = Mock(return_value=None)
        self.r.pool.get = Mock(return_value=SimpleNamespace(
            role='C3_LANGUAGE', last_metrics={}, generate=lambda messages, *a, **k: iter(['synthetic response'])
        ))

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

    def rows(self):
        S.stage_ttt(self.r.store, self.home)
        path = self.home / 'exports/sleep-ttt-candidates.jsonl'
        return [json.loads(x) for x in path.read_text().splitlines()]

    def prepare(self):
        self.turn('Run207 alpha historical context synthetic marker ALPHA_207')
        self.turn('Run207 beta middle context synthetic marker BETA_207')
        self.turn('Run207 gamma target synthetic marker GAMMA_207')
        self.assertEqual(S.digest(self.r.store)['turns'], 3)
        self.assertEqual(len(self.rows()), 2)

    def revoke_user_source(self, marker):
        row = self.r.store.one(
            'SELECT e.source_id FROM events e JOIN messages m ON m.event_id=e.id '
            "WHERE m.role='user' AND m.text LIKE ? ORDER BY m.id DESC LIMIT 1", ('%' + marker + '%',)
        )
        self.assertIsNotNone(row)
        with self.r.store.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (row['source_id'],))

    def test_revoked_earlier_turn_cannot_be_reexported_in_training_context(self):
        self.prepare()
        self.revoke_user_source('ALPHA_207')
        rows = self.rows()
        self.assertLess(len(rows), 2, 'source-dependent later turns may also be invalidated')
        self.assertFalse(any('ALPHA_207' in json.dumps(row) for row in rows), rows)
        self.assertTrue(all(row['status'] == 'CANDIDATE_NOT_TRAINED' for row in rows))

    def test_revoked_target_turn_is_not_staged_for_training(self):
        self.prepare()
        self.revoke_user_source('GAMMA_207')
        rows = self.rows()
        self.assertFalse(any('GAMMA_207' in json.dumps(row) for row in rows), rows)

    def test_tampered_persisted_digest_does_not_become_training_input(self):
        self.prepare()
        st, version = self.r.store.state(S.KEY, None)
        entries = st['sessions'][self.r.session]['entries']
        entries[0]['user'] = 'FORGED_RUN207_CONTEXT'
        entries[1]['answer'] = 'FORGED_RUN207_ANSWER'
        self.r.store.set_state(S.KEY, st, expected=version)
        rows = self.rows()
        self.assertFalse(any('FORGED_RUN207' in json.dumps(row) for row in rows), rows)
        self.assertFalse(any('BETA_207' in row['input'] for row in rows), rows)


if __name__ == '__main__':
    unittest.main()
