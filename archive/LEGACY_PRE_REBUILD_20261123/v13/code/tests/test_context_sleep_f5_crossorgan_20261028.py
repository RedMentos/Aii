"""Cross-organ F1/F5 authority: ContextOS warm, Sleep A/B and queued Dream.

Actual Runtime/SQLite synthetic human facts, no native model or fact writes.
Warm only admits fact/style/preference, not route; WORLD_RELATION uses facts.
"""
import json
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.context_os import ContextOS


class ContextSleepF5CrossOrgan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.s = self.r.store
        self.session = self.r.session
        self.cy = self.r.sleep.cycle
        self.context = ContextOS(self.s, self.r.cfg)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def correction(self, key, value):
        event = self.s.event(self.session, key)
        mid = self.r.memory.feedback(event['event_id'], 'fact', value, key=key)
        sid = self.s.one(
            'SELECT source_id FROM memories WHERE id=?', (mid,))['source_id']
        self.context.observe(
            self.s.event(self.session, 'warm trigger')['event_id'],
            'C3_LANGUAGE', {}, memory_ids=[mid])
        return event, mid, sid

    def revoke(self, sid):
        with self.s.tx() as conn:
            conn.execute(
                "DELETE FROM packets WHERE kind='HumanDecision' "
                "AND json_extract(payload,'$.source_ref.source_id')=?", (sid,))

    def test_one_revocation_clears_warm_sleep_and_queued_world_relation(self):
        key = 'Project Aurora budget'
        self.correction('Project Borealis budget', '120 credits')
        first, mid, sid = self.correction(key, '120 credits')
        self.assertIn(mid, self.context.warm(key, self.session, [])['ids'])
        self.assertEqual(self.cy._probe({'event_id': first['event_id']})[0], 'PASS')
        st, _ = self.cy.queue.load()
        dream = self.cy.sleep_b(st, self.cy.policy(), limit=12)
        worlds = [h for h in dream['hypotheses'] if h['kind'] == 'WORLD_RELATION']
        self.assertTrue(worlds, dream)
        rid = worlds[0]['replay_id']
        row = self.s.one(
            "SELECT payload FROM packets WHERE kind='ReplayItem' "
            "AND json_extract(payload,'$.replay_id')=? "
            "AND json_extract(payload,'$.stage')='QUEUED'", (rid,))
        self.assertIsNotNone(row)
        queued = json.loads(row['payload'])
        self.assertEqual(queued['fact_write_authority'], 0)
        self.revoke(sid)
        self.assertNotIn(mid, self.context.warm(key, self.session, [])['ids'])
        self.assertNotEqual(self.cy._probe({'event_id': first['event_id']})[0], 'PASS')
        later = self.cy.sleep_b(self.cy.queue.load()[0], self.cy.policy(), limit=12)
        self.assertFalse(any(h['kind'] == 'WORLD_RELATION' for h in later['hypotheses']))
        self.assertEqual(self.cy.check_hypothesis(queued)['verdict'], 'STALE')
        self.assertEqual(self.s.rows('SELECT * FROM updates'), [])

    def test_independent_valid_fact_survives_other_revocation(self):
        first, first_mid, first_sid = self.correction(
            'Project Orion budget', '120 credits')
        second, second_mid, _ = self.correction(
            'Project Vega budget', '42 credits')
        self.revoke(first_sid)
        self.assertIn(second_mid, self.context.warm(
            'Project Vega budget', self.session, [])['ids'])
        self.assertEqual(self.cy._probe({'event_id': second['event_id']})[0], 'PASS')
        self.assertNotEqual(self.cy._probe({'event_id': first['event_id']})[0], 'PASS')
        self.assertEqual(self.s.rows('SELECT * FROM updates'), [])


if __name__ == '__main__':
    unittest.main()
