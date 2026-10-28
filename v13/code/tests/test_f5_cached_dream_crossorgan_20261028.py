"""Cross-organ regression: a cached supported Dream verdict cannot survive F5 revocation.

Actual Runtime/SQLite synthetic feedback and restart, no native inference or fact writes.
This combines independent warm ContextOS, Sleep A probe, and cached Dream validation.
"""
import tempfile
import unittest
from pathlib import Path

from v13.context_os import ContextOS
from v13.runtime import Runtime


class CachedDreamCrossOrganF5(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def correction(self, key, kind, value):
        event = self.r.store.event(self.r.session, key)
        mid = self.r.memory.feedback(event['event_id'], kind, value, key=key)
        row = self.r.store.one(
            'SELECT m.source_id,s.hash,s.chars FROM memories m '
            'JOIN sources s ON s.id=m.source_id WHERE m.id=?', (mid,))
        ref = {'source_id': row['source_id'], 'sha256': row['hash'],
               'char_start': 0, 'char_end': row['chars'], 'modality': 'text'}
        return event, mid, row['source_id'], ref

    def test_restart_revocation_separates_warm_probe_and_cached_dream(self):
        anchor, anchor_mid, anchor_sid, ref = self.correction(
            'Explain Project Orion precisely', 'route', 'detail')
        self.correction('Explain Project Orion precisely please', 'route', 'gist')
        _, fact_mid, _, _ = self.correction(
            'Project Vega budget', 'fact', '42 credits')
        ctx = ContextOS(self.r.store, self.r.cfg)
        trigger = self.r.store.event(self.r.session, 'warm trigger')
        ctx.observe(trigger['event_id'], 'C3_LANGUAGE', {}, memory_ids=[fact_mid])
        self.assertIn(fact_mid, ctx.warm('Project Vega budget', self.r.session, [])['ids'])
        self.assertEqual(self.r.sleep.cycle._probe({'event_id': anchor['event_id']})[0], 'PASS')

        cy = self.r.sleep.cycle
        st, version = cy.queue.load()
        queued = cy._hypothesis(
            st, 'f5-crossorgan:' + anchor_mid, anchor['event_id'],
            'ROUTE_ALTERNATIVE', 'Hypothesis only: gist may replace detail.',
            [ref], {'observed_route': 'detail', 'alternative_route': 'gist',
                    'memory_id': anchor_mid})
        self.assertIsNotNone(queued)
        rid = queued['replay_id']
        cy.queue.sync(st, cy.policy())
        first = cy.validate_hypotheses(st, cy.policy(), limit=8)
        self.assertEqual(first['by_verdict'].get('SUPPORTED'), 1, first)
        before = self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ReplayItem' "
            "AND json_extract(payload,'$.replay_id')=? "
            "AND json_extract(payload,'$.stage')='SLEEP_B_VALIDATION'", (rid,))['n']
        cy.validate_hypotheses(st, cy.policy(), limit=8)
        after = self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ReplayItem' "
            "AND json_extract(payload,'$.replay_id')=? "
            "AND json_extract(payload,'$.stage')='SLEEP_B_VALIDATION'", (rid,))['n']
        self.assertEqual(before, after)  # stable SUPPORTED does not spam packets
        cy.queue.save(st, version)
        self.r.close()
        self.r = Runtime(self.home)

        with self.r.store.tx() as conn:
            conn.execute(
                "DELETE FROM packets WHERE kind='HumanDecision' "
                "AND json_extract(payload,'$.source_ref.source_id')=?", (anchor_sid,))
        self.assertNotEqual(
            self.r.sleep.cycle._probe({'event_id': anchor['event_id']})[0], 'PASS')
        # Unrelated verified fact remains available in the warm ContextOS lane.
        ctx = ContextOS(self.r.store, self.r.cfg)
        trigger = self.r.store.event(self.r.session, 'warm trigger after restart')
        ctx.observe(trigger['event_id'], 'C3_LANGUAGE', {}, memory_ids=[fact_mid])
        self.assertIn(fact_mid, ctx.warm('Project Vega budget', self.r.session, [])['ids'])

        restored, _ = self.r.sleep.cycle.queue.load()
        self.assertEqual(restored['hypothesis_checks'][rid]['verdict'], 'SUPPORTED')
        later = self.r.sleep.cycle.validate_hypotheses(
            restored, self.r.sleep.cycle.policy(), limit=8)
        self.assertEqual(later['by_verdict'].get('STALE'), 1, later)
        self.assertEqual(restored['hypothesis_checks'][rid]['verdict'], 'STALE')
        self.assertEqual(restored['items'][rid]['retired'], 'HYPOTHESIS_STALE')
        self.assertEqual(self.r.store.rows('SELECT * FROM updates'), [])


if __name__ == '__main__':
    unittest.main()
