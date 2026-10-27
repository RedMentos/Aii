"""Run270 RED-first: live F1 recall must retain actual F5 human authority.

Actual Runtime + SQLite, synthetic user text; no native inference, no training proof.
"""
import json
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime


class MemoryHumanDecisionLineageRun270(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.s = self.r.store
        self.session = self.r.session
        self.query = 'Project Helios budget'
        self.event = self.s.event(self.session, self.query)
        self.mid = self.r.memory.feedback(self.event['event_id'], 'fact', '120 credits',
                                          permission='record', key=self.query)
        self.source = self.s.one('SELECT source_id FROM memories WHERE id=?', (self.mid,))['source_id']

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def change(self, sql, args=()):
        with self.s.tx() as conn:
            conn.execute(sql, args)

    def recall_ids(self, session=None, query=None):
        return [m['id'] for m in self.r.memory.recall(query or self.query, session or self.session)]

    def test_valid_record_and_learn_corrections_survive_restart_without_updates(self):
        other = self.s.event(self.session, 'Project Selene budget')
        mid2 = self.r.memory.feedback(other['event_id'], 'fact', '42 credits',
                                      permission='learn', key='Project Selene budget')
        self.assertEqual(self.recall_ids(), [self.mid])
        self.assertEqual(self.recall_ids(query='Project Selene budget'), [mid2])
        self.assertEqual(self.s.rows('SELECT * FROM updates'), [])
        self.r.close()
        self.r = Runtime(self.home)
        self.s = self.r.store
        self.assertEqual(self.recall_ids(), [self.mid])
        self.assertEqual(self.recall_ids(query='Project Selene budget'), [mid2])
        self.assertEqual(self.s.rows('SELECT * FROM updates'), [])

    def test_missing_human_decision_packet_must_not_recall(self):
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND event_id=?", (self.event['event_id'],))
        self.assertEqual(self.recall_ids(), [])

    def test_changed_human_decision_fields_must_not_recall(self):
        for field, wrong in [('kind', 'preference'), ('value', '999 credits'),
                             ('event_id', 'evt-foreign'), ('brain_generation_id', 'gen-foreign'),
                             ('learning_permission', 'automatic')]:
            with self.subTest(field=field):
                row = self.s.one("SELECT id,payload FROM packets WHERE kind='HumanDecision' AND event_id=?", (self.event['event_id'],))
                old = json.loads(row['payload'])
                mutated = dict(old, **{field: wrong})
                self.change('UPDATE packets SET payload=? WHERE id=?', (json.dumps(mutated), row['id']))
                self.assertEqual(self.recall_ids(), [])
                self.change('UPDATE packets SET payload=? WHERE id=?', (json.dumps(old), row['id']))

    def test_decision_source_ref_and_provenance_must_remain_bound(self):
        row = self.s.one("SELECT id,payload FROM packets WHERE kind='HumanDecision' AND event_id=?", (self.event['event_id'],))
        old = json.loads(row['payload'])
        for mutation in ({'source_ref': dict(old['source_ref'], source_id='src-foreign')},
                         {'provenance': []}):
            with self.subTest(mutation=mutation):
                self.change('UPDATE packets SET payload=? WHERE id=?', (json.dumps(dict(old, **mutation)), row['id']))
                self.assertEqual(self.recall_ids(), [])
                self.change('UPDATE packets SET payload=? WHERE id=?', (json.dumps(old), row['id']))

    def test_missing_or_falsified_feedback_must_not_recall(self):
        row = self.s.one('SELECT * FROM feedback WHERE source_id=?', (self.source,))
        foreign_event = self.s.event(self.session, 'Another event for FK-preserving tamper')
        for field, wrong in [('kind', 'preference'), ('value', '999 credits'),
                             ('permission', 'automatic'), ('event_id', foreign_event['event_id'])]:
            with self.subTest(field=field):
                self.change('UPDATE feedback SET '+field+'=? WHERE id=?', (wrong, row['id']))
                self.assertEqual(self.recall_ids(), [])
                self.change('UPDATE feedback SET '+field+'=? WHERE id=?', (row[field], row['id']))
        self.change('DELETE FROM feedback WHERE id=?', (row['id'],))
        self.assertEqual(self.recall_ids(), [])

    def test_source_kind_cannot_change_human_authority(self):
        self.change('UPDATE sources SET kind=? WHERE id=?', ('REPLAY_HYPOTHESIS', self.source))
        self.assertEqual(self.recall_ids(), [])

    def test_provisional_event_cannot_retain_authoritative_memory(self):
        row = self.s.one('SELECT packet FROM events WHERE id=?', (self.event['event_id'],))
        env = json.loads(row['packet'])
        env['authority'] = 'PROVISIONAL'
        self.change('UPDATE events SET packet=? WHERE id=?', (json.dumps(env), self.event['event_id']))
        self.assertEqual(self.recall_ids(), [])

    def test_duplicate_decision_is_ambiguous_and_refused(self):
        row = self.s.one("SELECT * FROM packets WHERE kind='HumanDecision' AND event_id=?", (self.event['event_id'],))
        self.change('INSERT INTO packets SELECT ?,kind,event_id,generation_id,payload,created FROM packets WHERE id=?',
                    ('pkt-run270-duplicate', row['id']))
        self.assertEqual(self.recall_ids(), [])

    def test_invalid_decision_does_not_suppress_independent_valid_correction(self):
        other = self.s.event(self.session, 'Project Selene budget')
        mid2 = self.r.memory.feedback(other['event_id'], 'fact', '42 credits',
                                      permission='record', key='Project Selene budget')
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND event_id=?", (self.event['event_id'],))
        self.assertEqual(self.recall_ids(), [])
        self.assertEqual(self.recall_ids(query='Project Selene budget'), [mid2])


if __name__ == '__main__':
    unittest.main()
