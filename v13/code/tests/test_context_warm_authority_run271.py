"""Run271: ContextOS warm path must not bypass F5 human correction authority.

Actual Runtime/SQLite, synthetic text; no native model or Redmi claim.
"""
import json
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.context_os import ContextOS


class ContextWarmAuthorityRun271(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.s = self.r.store
        self.c = ContextOS(self.s, self.r.cfg)
        self.session = self.r.session
        self.key = 'Project Apollo budget'
        e = self.s.event(self.session, self.key)
        self.mid = self.r.memory.feedback(e['event_id'], 'fact', '120 credits', key=self.key)
        self.sid = self.s.one('SELECT source_id FROM memories WHERE id=?', (self.mid,))['source_id']
        self.c.observe(self.s.event(self.session, 'warm up')['event_id'], 'C3_LANGUAGE', {}, memory_ids=[self.mid])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def change(self, sql, args=()):
        with self.s.tx() as conn:
            conn.execute(sql, args)

    def warm(self, query=None):
        return self.c.warm(query or self.key, self.session, [])

    def test_valid_warm_correction_survives_restart_and_explicit_active_mode(self):
        self.assertEqual(self.warm()['ids'], [self.mid])
        self.assertFalse(self.warm()['applied'])
        self.c.set_mode('ACTIVE', 'EXPLICIT_HUMAN')
        self.assertEqual(self.warm()['ids'], [self.mid])
        self.assertTrue(self.warm()['applied'])
        self.r.close()
        self.r = Runtime(self.home)
        self.s = self.r.store
        self.c = ContextOS(self.s, self.r.cfg)
        self.assertEqual(self.warm()['ids'], [self.mid])

    def test_deleted_human_decision_never_warm_reactivates(self):
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?", (self.sid,))
        self.assertEqual(self.r.memory.recall(self.key, self.session), [])
        self.assertEqual(self.warm()['ids'], [])
        self.c.set_mode('ACTIVE', 'EXPLICIT_HUMAN')
        self.assertEqual(self.warm()['ids'], [])

    def test_changed_source_kind_cannot_reactivate(self):
        self.change('UPDATE sources SET kind=? WHERE id=?', ('REPLAY_HYPOTHESIS', self.sid))
        self.assertEqual(self.warm()['ids'], [])

    def test_deleted_feedback_cannot_reactivate(self):
        self.change('DELETE FROM feedback WHERE source_id=?', (self.sid,))
        self.assertEqual(self.warm()['ids'], [])

    def test_duplicate_human_decision_cannot_reactivate(self):
        row = self.s.one("SELECT id FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?", (self.sid,))
        self.change('INSERT INTO packets SELECT ?,kind,event_id,generation_id,payload,created FROM packets WHERE id=?',
                    ('pkt-run271-duplicate', row['id']))
        self.assertEqual(self.warm()['ids'], [])

    def test_invalid_first_warm_candidate_does_not_starve_valid_second(self):
        other_key = 'Project Apollo funding'
        e = self.s.event(self.session, other_key)
        other = self.r.memory.feedback(e['event_id'], 'fact', '42 credits', key=other_key)
        self.c.observe(self.s.event(self.session, 'more warm')['event_id'], 'C3_LANGUAGE', {}, memory_ids=[self.mid, other])
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?", (self.sid,))
        got = self.warm('Project Apollo budget funding')
        self.assertEqual(got['ids'], [other])
        self.assertEqual(got['items'][0]['value'], '42 credits')


if __name__ == '__main__':
    unittest.main()
