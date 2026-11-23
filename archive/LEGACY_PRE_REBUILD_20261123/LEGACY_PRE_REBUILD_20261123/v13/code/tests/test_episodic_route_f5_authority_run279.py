"""Run279 RED-first: fast episodic routes require live F5 feedback authority.

Actual Runtime + SQLite correction and route suggestion, no native model calls.
"""
import json
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import episodic_route as ER


class EpisodicRouteF5AuthorityRun279(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.s = self.r.store
        self.session = self.r.session
        self.event = self.s.event(self.session, 'Explain Project Aurora precisely')
        self.mid = self.r.memory.feedback(self.event['event_id'], 'route', 'detail', permission='record')
        self.source_id = self.s.one('SELECT source_id FROM memories WHERE id=?', (self.mid,))['source_id']

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def change(self, sql, args=()):
        with self.s.tx() as c:
            c.execute(sql, args)

    def suggestion(self, query='Explain Project Aurora precisely'):
        return ER.suggest(self.s, query, self.session)

    def test_valid_record_and_learn_routes_remain_available(self):
        self.assertEqual(self.suggestion()['route'], 'detail')
        other = self.s.event(self.session, 'Explain Project Borealis precisely')
        mid2 = self.r.memory.feedback(other['event_id'], 'route', 'gist', permission='learn')
        self.assertEqual(self.suggestion('Explain Project Borealis precisely')['memory_id'], mid2)
        self.assertEqual(self.suggestion()['memory_id'], self.mid)

    def test_deleting_feedback_must_revoke_route_suggestion_and_active_use(self):
        self.assertEqual(self.suggestion()['route'], 'detail')
        ER.set_mode(self.s, 'active')
        self.assertEqual(ER.for_turn(self.s, 'Explain Project Aurora precisely', self.session)[0], 'detail')
        self.change('DELETE FROM feedback WHERE source_id=?', (self.source_id,))
        self.assertIsNone(self.suggestion())
        self.assertEqual(ER.for_turn(self.s, 'Explain Project Aurora precisely', self.session), (None, None))

    def test_falsified_feedback_fields_must_not_route(self):
        row = self.s.one('SELECT * FROM feedback WHERE source_id=?', (self.source_id,))
        foreign = self.s.event(self.session, 'Other event for FK-preserving tamper')
        for field, wrong in [('kind', 'fact'), ('value', 'both'),
                             ('permission', 'automatic'), ('event_id', foreign['event_id'])]:
            with self.subTest(field=field):
                self.change('UPDATE feedback SET ' + field + '=? WHERE id=?', (wrong, row['id']))
                self.assertIsNone(self.suggestion())
                self.change('UPDATE feedback SET ' + field + '=? WHERE id=?', (row[field], row['id']))

    def test_nonhuman_source_kind_must_not_route(self):
        self.change('UPDATE sources SET kind=? WHERE id=?', ('REPLAY_HYPOTHESIS', self.source_id))
        self.assertIsNone(self.suggestion())

    def test_duplicate_feedback_must_not_count_as_independent_authority(self):
        row = self.s.one('SELECT * FROM feedback WHERE source_id=?', (self.source_id,))
        self.change('INSERT INTO feedback VALUES (?,?,?,?,?,?,?)',
                    ('feedback-run279-duplicate', row['event_id'], row['source_id'],
                     row['kind'], row['value'], row['permission'], row['created']))
        self.assertIsNone(self.suggestion())

    def test_invalid_human_decision_producer_must_not_route(self):
        row = self.s.one("SELECT id,payload FROM packets WHERE kind='HumanDecision' AND event_id=?",
                         (self.event['event_id'],))
        packet = json.loads(row['payload'])
        packet['producer_component'] = 'MODEL_PREDICTION'
        self.change('UPDATE packets SET payload=? WHERE id=?', (json.dumps(packet), row['id']))
        self.assertIsNone(self.suggestion())

    def test_revoking_one_route_preserves_an_independent_valid_route(self):
        other = self.s.event(self.session, 'Explain Project Borealis precisely')
        mid2 = self.r.memory.feedback(other['event_id'], 'route', 'gist')
        self.change('DELETE FROM feedback WHERE source_id=?', (self.source_id,))
        self.assertIsNone(self.suggestion())
        other_suggestion = self.suggestion('Explain Project Borealis precisely')
        self.assertIsNotNone(other_suggestion)
        self.assertEqual(other_suggestion['memory_id'], mid2)


if __name__ == '__main__':
    unittest.main()
