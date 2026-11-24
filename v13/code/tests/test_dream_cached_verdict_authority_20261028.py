"""Cached Dream verdicts must not retain revoked F5 human evidence.

Actual Runtime/SQLite synthetic human corrections; no native inference or fact writes.
This tests validate_hypotheses (not just check_hypothesis), including restart.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime


class DreamCachedVerdictAuthority(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.session = self.r.session

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    @property
    def store(self):
        return self.r.store

    @property
    def cycle(self):
        return self.r.sleep.cycle

    def correction(self, key, route):
        event = self.store.event(self.session, key)
        mid = self.r.memory.feedback(event['event_id'], 'route', route, key=key)
        row = self.store.one(
            'SELECT m.source_id,s.hash,s.chars FROM memories m '
            'JOIN sources s ON s.id=m.source_id WHERE m.id=?', (mid,))
        ref = {'source_id': row['source_id'], 'sha256': row['hash'],
               'char_start': 0, 'char_end': row['chars'], 'modality': 'text'}
        return event, mid, row['source_id'], ref

    def revoke(self, sid):
        with self.store.tx() as conn:
            conn.execute(
                "DELETE FROM packets WHERE kind='HumanDecision' "
                "AND json_extract(payload,'$.source_ref.source_id')=?", (sid,))

    def supported_queue(self):
        event, mid, anchor_sid, ref = self.correction(
            'Explain Project Orion precisely', 'detail')
        _, _, neighbor_sid, _ = self.correction(
            'Explain Project Orion precisely please', 'gist')
        st, version = self.cycle.queue.load()
        queued = self.cycle._hypothesis(
            st, 'f5-cache:' + mid, event['event_id'], 'ROUTE_ALTERNATIVE',
            'Hypothesis only: gist may be an alternative route.', [ref],
            {'observed_route': 'detail', 'alternative_route': 'gist',
             'memory_id': mid})
        self.assertIsNotNone(queued)
        rid = queued['replay_id']
        self.cycle.queue.sync(st, self.cycle.policy())
        first = self.cycle.validate_hypotheses(
            st, self.cycle.policy(), limit=8)
        self.assertEqual(first['by_verdict'].get('SUPPORTED'), 1, first)
        self.assertEqual(st['hypothesis_checks'][rid]['verdict'], 'SUPPORTED')
        self.assertEqual(self.store.rows('SELECT * FROM updates'), [])
        return st, version, rid, anchor_sid, neighbor_sid

    def test_revoked_anchor_invalidates_cached_supported_verdict(self):
        st, _, rid, anchor_sid, _ = self.supported_queue()
        self.revoke(anchor_sid)
        again = self.cycle.validate_hypotheses(
            st, self.cycle.policy(), limit=8)
        self.assertEqual(again['by_verdict'].get('STALE'), 1, again)
        self.assertEqual(st['hypothesis_checks'][rid]['verdict'], 'STALE')
        self.assertEqual(st['items'][rid]['retired'], 'HYPOTHESIS_STALE')

    def test_revoked_supporting_neighbor_invalidates_cached_supported_verdict(self):
        st, _, rid, _, neighbor_sid = self.supported_queue()
        self.revoke(neighbor_sid)
        again = self.cycle.validate_hypotheses(
            st, self.cycle.policy(), limit=8)
        self.assertGreaterEqual(again['checked'], 1, again)
        self.assertNotEqual(st['hypothesis_checks'][rid]['verdict'], 'SUPPORTED')
        self.assertEqual(self.store.rows('SELECT * FROM updates'), [])

    def test_persisted_supported_verdict_revalidates_after_restart(self):
        st, version, rid, anchor_sid, _ = self.supported_queue()
        self.cycle.queue.save(st, version)
        self.r.close()
        self.r = Runtime(self.home)
        self.revoke(anchor_sid)
        restored, _ = self.cycle.queue.load()
        self.assertEqual(restored['hypothesis_checks'][rid]['verdict'], 'SUPPORTED')
        again = self.cycle.validate_hypotheses(
            restored, self.cycle.policy(), limit=8)
        self.assertEqual(again['by_verdict'].get('STALE'), 1, again)
        self.assertEqual(restored['hypothesis_checks'][rid]['verdict'], 'STALE')


if __name__ == '__main__':
    unittest.main()
