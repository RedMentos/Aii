"""Run41 actual V13 Runtime/Store source-only bridge; no model inference."""
from pathlib import Path
import tempfile
import time
import unittest

from v13.runtime import Runtime
from v13.contracts import packet
from scripts import run40_b2_store_history_readonly as bridge

NOTE = ('Project Aquila initial approved procurement note. ' +
        'Administrative introduction only. ' * 10 +
        'Binding rules: Budget 134 euros. Deadline 9 days. Local-only requirement: true.')
SHEET = 'Project Aquila supplier sheet. Option A costs 91 euros, option B costs 105 euros.'
CURRENT = 'Project Aquila: decide using the earlier binding project rules.'


class RealStoreCrosscheck(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.temp.name))
        self.store = self.runtime.store
        self.model_revision = self.runtime.models.revision('B2_GIST')

    def tearDown(self):
        self.runtime.close()
        self.temp.cleanup()

    def offer(self, text):
        e = self.store.event(self.runtime.session, text)
        p = packet('OfferPacket', 'B2_GIST', e['event_id'], e['brain_generation_id'],
                   [e['source_ref']], role='B2_GIST', based_on_state_version=0,
                   deadline_monotonic_ns=time.monotonic_ns() + 10**9,
                   evidence_refs=[e['source_ref']],
                   offer={'summary': 'Untrusted hypothesis.', 'quotes': [],
                          'uncertainty': '', 'needs_reentry': False},
                   confidence=0.0, model_revision=self.model_revision)
        self.store.add_packet('OfferPacket', p)
        self.runtime.cognition.retain_body_offer(p)
        return e, p

    def select(self, current):
        return bridge.select_from_store(self.store, current, self.runtime.session,
                                        current['brain_generation_id'], self.model_revision)

    def test_real_store_retrieves_old_rule_outside_retained_state_without_writes(self):
        first, p = self.offer(NOTE)
        for _ in range(5):
            self.offer(SHEET)
        current = self.store.event(self.runtime.session, CURRENT)
        state_key = 'B2_GIST:' + self.runtime.session
        before_state = self.store.state(state_key)
        self.assertNotIn(p['packet_id'], before_state[0]['retained_offer_ids'])
        before_counts = {table: self.store.one('SELECT COUNT(*) AS n FROM ' + table)['n']
                         for table in ('events', 'packets', 'states', 'sources')}
        before_generation = self.store.generation_id
        result = self.select(current)
        self.assertEqual(len(result['items']), 1)
        selected = result['items'][0]
        self.assertEqual(selected['source_ref']['source_id'], first['source_ref']['source_id'])
        self.assertIn('Budget 134 euros', selected['native_context']['exact_source_excerpt'])
        self.assertIn('Deadline 9 days', selected['native_context']['exact_source_excerpt'])
        self.assertEqual(self.store.read_source(selected['source_ref']),
                         selected['native_context']['exact_source_excerpt'])
        self.assertEqual(self.store.state(state_key), before_state)
        self.assertEqual(self.store.generation_id, before_generation)
        self.assertEqual({table: self.store.one('SELECT COUNT(*) AS n FROM ' + table)['n']
                          for table in before_counts}, before_counts)
        self.assertFalse(result['canonical_gate_pass'])
        self.assertEqual(result['authority'], 'SOURCE_POINTER_ONLY_SHADOW')

    def test_real_store_deleted_old_rule_cannot_resurface(self):
        first, _ = self.offer(NOTE)
        for _ in range(5):
            self.offer(SHEET)
        current = self.store.event(self.runtime.session, CURRENT)
        with self.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?',
                       (first['source_ref']['source_id'],))
        result = self.select(current)
        self.assertEqual(result['items'], [])
        self.assertFalse(result['canonical_gate_pass'])


if __name__ == '__main__':
    unittest.main()
