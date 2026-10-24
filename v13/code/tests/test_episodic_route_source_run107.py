"""Run107 preregistered real SQLite source-integrity counterexamples for WP-U10."""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13 import episodic_route as ER


QUERY = 'Erkläre Projekt Aurora bitte genau'
BASE = 'Erkläre Projekt Aurora genau'


class EpisodicRouteSourceRun107(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.s = self.r.store
        self.event = self.s.event(self.r.session, BASE)
        self.mid = self.r.memory.feedback(self.event['event_id'], 'route', 'detail')
        ER.set_mode(self.s, 'active')

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def mutate(self, sql, args):
        with self.s.tx() as conn:
            conn.execute(sql, args)

    def test_valid_route_value_mutation_cannot_redirect_active_or_shadow(self):
        self.assertEqual(ER.for_turn(self.s, QUERY, self.r.session)[0], 'detail')
        self.mutate("UPDATE memories SET value=? WHERE id=?", ('gist', self.mid))
        self.assertEqual(ER.for_turn(self.s, QUERY, self.r.session), (None, None))
        ER.set_mode(self.s, 'shadow')
        self.assertEqual(ER.for_turn(self.s, QUERY, self.r.session), (None, None))

    def test_mutated_key_cannot_redirect_to_another_named_entity(self):
        self.mutate("UPDATE memories SET key_text=? WHERE id=?",
                    ('Erkläre Projekt Borealis genau', self.mid))
        self.assertIsNone(ER.suggest(self.s, 'Erkläre Projekt Borealis bitte genau', self.r.session))

    def test_memory_record_packet_key_mismatch_rejected(self):
        self.mutate("UPDATE packets SET payload=json_set(payload,'$.key',?) "
                    "WHERE kind='MemoryRecord' AND json_extract(payload,'$.memory_id')=?",
                    ('Erkläre Projekt Borealis genau', self.mid))
        self.assertIsNone(ER.suggest(self.s, QUERY, self.r.session))

    def test_corrupt_source_blob_rejected(self):
        row = self.s.one("SELECT s.hash FROM sources s JOIN memories m ON s.id=m.source_id WHERE m.id=?", (self.mid,))
        (self.home / 'data' / 'blobs' / row['hash']).write_bytes(b'not-the-human-route-label')
        self.assertIsNone(ER.suggest(self.s, QUERY, self.r.session))

    def test_missing_originating_event_rejected(self):
        # FK-safe mutation: point to a different real event while retaining the old MemoryRecord.
        other = self.s.event(self.r.session, 'Unrelated user request')
        self.mutate("UPDATE memories SET event_id=? WHERE id=?", (other['event_id'], self.mid))
        self.assertIsNone(ER.suggest(self.s, QUERY, self.r.session))

    def test_read_only_valid_route_restart_and_global_scope(self):
        self.assertEqual(ER.suggest(self.s, QUERY, self.r.session)['route'], 'detail')
        before = self.s.one("SELECT COUNT(*) AS n FROM sources WHERE kind='MEMORY_KEY'")['n']
        self.assertEqual(ER.suggest(self.s, QUERY, self.r.session)['route'], 'detail')
        after = self.s.one("SELECT COUNT(*) AS n FROM sources WHERE kind='MEMORY_KEY'")['n']
        self.assertEqual(before, after)
        second = self.s.new_session()
        self.assertIsNone(ER.suggest(self.s, QUERY, second))
        ev = self.s.event(self.r.session, 'Erkläre Projekt Vega genau')
        self.r.memory.feedback(ev['event_id'], 'route', 'gist', scope='global')
        self.assertEqual(ER.suggest(self.s, 'Erkläre Projekt Vega bitte genau', second)['route'], 'gist')
        self.r.close()
        self.r = Runtime(self.home)
        self.s = self.r.store
        self.assertEqual(ER.suggest(self.s, 'Erkläre Projekt Vega bitte genau', second)['route'], 'gist')

    def test_invalid_newer_candidate_does_not_hide_valid_older(self):
        newer = self.s.event(self.r.session, 'Erkläre Projekt Aurora bitte genau')
        mid2 = self.r.memory.feedback(newer['event_id'], 'route', 'simple', key='Erkläre Projekt Aurora bitte genau')
        self.mutate("UPDATE memories SET value=? WHERE id=?", ('gist', mid2))
        suggestion = ER.suggest(self.s, QUERY, self.r.session)
        self.assertIsNotNone(suggestion)
        self.assertEqual((suggestion['memory_id'], suggestion['route']), (self.mid, 'detail'))


if __name__ == '__main__':
    unittest.main()
