"""Real SQLite Store SHADOW ticket persistence; no model or live authority."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts import run18_step2_balanced_controls as balanced
from scripts import run11_store_shadow_use_boundary as boundary
from scripts import run11_store_shadow_ticket_io as io
from v13.config import initialize
from v13.store import Store


class PrivateShadowTicketIO(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.case = next(c for c in balanced.FIXTURES if c['id'] == 'Veldora')
        events = [self.store.event(self.session, text) for text in
                  (self.case['history'][0], self.case['history'][2],
                   self.case['current'])]
        self.refs = dict(zip(('old', 'sheet', 'current'),
                             (e['event_id'] for e in events)))
        self.private = self.home / 'private-tickets'
        self.private.mkdir(mode=0o700)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def ticket(self):
        return boundary.seal_candidate(self.store, self.session,
                                       self.case['id'], self.refs,
                                       self.case['temporal_mode'], 'sheet')

    def save(self, ticket=None, directory=None, filename='candidate.json'):
        return io.save_ticket(self.store, ticket or self.ticket(),
                              self.session, self.case['id'],
                              directory or self.private, filename)

    def inspect(self, directory=None, filename='candidate.json', session=None):
        return io.inspect_saved_ticket(self.store, session or self.session,
                                       self.case['id'], directory or self.private,
                                       filename)

    def test_private_save_restart_replay_is_shadow_only(self):
        receipt = self.save()
        self.assertEqual(receipt['status'], 'SHADOW_ONLY')
        self.assertIs(receipt['authority'], False)
        self.assertIs(receipt['post_return_atomic'], False)
        self.assertEqual((self.private / 'candidate.json').stat().st_mode & 0o777, 0o600)
        self.store.close()
        self.store = Store(self.home)
        result = self.inspect()
        self.assertEqual(result['action'], self.case['oracle']['action'])
        self.assertIs(result['authority'], False)
        self.assertIs(result['canonical_gate_pass'], False)

    def test_save_never_overwrites_original(self):
        self.save()
        before = (self.private / 'candidate.json').read_bytes()
        with self.assertRaises(io.Refusal):
            self.save()
        self.assertEqual((self.private / 'candidate.json').read_bytes(), before)

    def test_revoked_original_source_refuses_disk_replay(self):
        self.save()
        with self.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=('
                       'SELECT source_id FROM events WHERE id=?)',
                       (self.refs['old'],))
        with self.assertRaises(io.Refusal):
            self.inspect()

    def test_reordered_original_event_refuses_disk_replay(self):
        self.save()
        row = self.store.one('SELECT rowid AS seq FROM events WHERE id=?',
                             (self.refs['current'],))
        with self.store.tx() as db:
            db.execute('UPDATE events SET rowid=? WHERE id=?',
                       (row['seq'] + 1000, self.refs['current']))
        with self.assertRaises(io.Refusal):
            self.inspect()

    def test_corrupted_disk_ticket_refuses(self):
        self.save()
        (self.private / 'candidate.json').write_bytes(b'{}')
        with self.assertRaises(io.Refusal):
            self.inspect()

    def test_noncanonical_duplicate_keys_refuses(self):
        (self.private / 'candidate.json').write_bytes(b'{"x":1,"x":2}')
        with self.assertRaises(io.Refusal):
            self.inspect()

    def test_oversized_disk_ticket_refuses(self):
        (self.private / 'candidate.json').write_bytes(b'x' * 65537)
        with self.assertRaises(io.Refusal):
            self.inspect()

    def test_symlink_ticket_refuses(self):
        self.save()
        (self.private / 'linked.json').symlink_to(self.private / 'candidate.json')
        with self.assertRaises(io.Refusal):
            self.inspect(filename='linked.json')

    def test_hardlink_ticket_refuses(self):
        self.save()
        os.link(self.private / 'candidate.json', self.private / 'linked.json')
        with self.assertRaises(io.Refusal):
            self.inspect()

    def test_world_readable_ticket_refuses(self):
        self.save()
        (self.private / 'candidate.json').chmod(0o644)
        with self.assertRaises(io.Refusal):
            self.inspect()

    def test_nonprivate_directory_refuses(self):
        self.private.chmod(0o755)
        try:
            with self.assertRaises(io.Refusal):
                self.save()
        finally:
            self.private.chmod(0o700)

    def test_symlink_directory_refuses(self):
        linked = self.home / 'linked-private'
        linked.symlink_to(self.private, target_is_directory=True)
        with self.assertRaises(io.Refusal):
            self.save(directory=linked)

    def test_invalid_filename_and_wrong_session_refuse(self):
        ticket = self.ticket()
        for filename in ('../escape.json', '/tmp/absolute.json', 'bad.txt', '.hidden.json'):
            with self.subTest(filename=filename):
                with self.assertRaises(io.Refusal):
                    self.save(ticket, filename=filename)
        self.save(ticket)
        other = self.store.new_session()
        with self.assertRaises(io.Refusal):
            self.inspect(session=other)

    def test_saved_ticket_contains_no_raw_original_user_message(self):
        self.save()
        content = (self.private / 'candidate.json').read_text(encoding='utf-8')
        for source in (self.case['history'][0], self.case['history'][2],
                       self.case['current']):
            self.assertNotIn(source, content)
        self.assertEqual(self.inspect()['status'], 'SHADOW_ONLY')


if __name__ == '__main__':
    unittest.main()
