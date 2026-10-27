"""WP-S7 deleted source cannot reappear in digest view or staged TTT data."""
import json
from pathlib import Path
import unittest

from tests.test_sleep_offline import Base
from v13 import sleep_offline as S


class SleepLineageGateTests(Base):
    def setup_three(self):
        self.turn('Private marker RAVEN-4711 for my notes.', 'Private answer RAVEN-4711 is recorded.')
        self.turn('What about the public garden?', 'The garden path is open to visitors.')
        self.turn('Any more public advice?', 'Water the plants every morning.')
        self.assertEqual(S.digest(self.r.store)['turns'], 3)

    def delete_event(self, user_text):
        event = self.r.store.one(
            "SELECT source_id FROM events WHERE id=(SELECT event_id FROM messages WHERE text=? LIMIT 1)",
            (user_text,))
        self.assertIsNotNone(event)
        with self.r.store.tx() as tx:
            tx.execute('UPDATE sources SET deleted=1 WHERE id=?', (event['source_id'],))

    def candidates(self):
        S.stage_ttt(self.r.store, self.home)
        p = self.home / 'exports/sleep-ttt-candidates.jsonl'
        return p, [json.loads(line) for line in p.read_text().splitlines() if line.strip()]

    def test_deleted_prior_source_hidden_in_view_and_staged_context(self):
        self.setup_three()
        self.delete_event('Private marker RAVEN-4711 for my notes.')
        view = S.view(self.r.store, self.r.session)
        self.assertNotIn('RAVEN-4711', view['text'] if view else '')
        p, rows = self.candidates()
        self.assertTrue(rows)
        self.assertTrue(all('RAVEN-4711' not in json.dumps(row) for row in rows))
        self.assertTrue(all(row['status'] == 'CANDIDATE_NOT_TRAINED' for row in rows))
        self.assertTrue(all(isinstance(row['context_event_ids'], list) for row in rows))
        self.assertTrue(all(type(row['target_message_id']) is int for row in rows))
        self.assertTrue(S.validate_ttt_export(self.r.store, p)['validated'])

    def test_deleted_target_source_never_staged(self):
        self.setup_three()
        self.delete_event('What about the public garden?')
        _, rows = self.candidates()
        self.assertTrue(rows)
        self.assertTrue(all('garden path is open' not in row['target'] for row in rows))
        self.assertTrue(all('public garden' not in row['context'] for row in rows))

    def test_persisted_export_fails_closed_after_source_deletion(self):
        self.setup_three()
        p, rows = self.candidates()
        self.assertEqual(len(rows), 2)
        self.assertEqual(S.validate_ttt_export(self.r.store, p)['candidates'], 2)
        self.delete_event('Private marker RAVEN-4711 for my notes.')
        with self.assertRaises(ValueError):
            S.validate_ttt_export(self.r.store, p)

    def test_legacy_candidate_without_source_refs_denied(self):
        self.setup_three()
        p, rows = self.candidates()
        self.assertTrue(rows)
        rows[0].pop('context_event_ids')
        p.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
        with self.assertRaises(ValueError):
            S.validate_ttt_export(self.r.store, p)

    def test_malformed_unhashable_context_or_session_fails_as_value_error(self):
        self.setup_three()
        p, rows = self.candidates()
        self.assertTrue(rows)
        original = p.read_bytes()
        for field, value in (('context_event_ids', [{}]), ('session', [])):
            try:
                modified = [dict(row) for row in rows]
                modified[0][field] = value
                p.write_text('\\n'.join(json.dumps(row) for row in modified) + '\\n')
                with self.subTest(field=field), self.assertRaises(ValueError):
                    S.validate_ttt_export(self.r.store, p)
            finally:
                p.write_bytes(original)

    def test_valid_source_retains_existing_sleep_behavior(self):
        self.setup_three()
        p, rows = self.candidates()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row['origin'] == 'self' for row in rows))
        self.assertTrue(all(row['status'] == 'CANDIDATE_NOT_TRAINED' for row in rows))
        self.assertTrue(S.validate_ttt_export(self.r.store, p)['validated'])
        self.assertIn('RAVEN-4711', S.view(self.r.store, self.r.session)['text'])


if __name__ == '__main__':
    unittest.main()
