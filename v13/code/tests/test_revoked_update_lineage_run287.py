"""Run287: source revocation and approval are one atomic SQLite gate.

Actual Store transactions, synthetic candidate artifacts; not native training.
"""
import json
from pathlib import Path
import tempfile
import unittest

from v13.common import atomic_write, dumps, file_hash, now, uid
from v13.config import initialize
from v13.memory import Memory
from v13.store import Store


class RevokedUpdateLineageRun287(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.s = Store(self.home)
        self.models = {'C2_CONTROL': 'encoder'}
        self.s.ensure_generation_snapshot(self.cfg, self.models)
        self.session = self.s.new_session()

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def candidate(self, source_ids, status='PENDING_APPROVAL'):
        update = uid('upd')
        rel = 'checkpoints/head-' + update + '.npz'
        atomic_write(self.home / rel, b'RUN287_SYNTHETIC_ARTIFACT')
        manifest = {'component': 'route', 'encoder_revision': 'encoder',
                    'commit_eligible': True, 'source_ids': source_ids}
        with self.s.tx() as c:
            c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',
                      (update, self.s.generation_id, status, rel,
                       file_hash(self.home / rel), dumps(manifest), now()))
        return update, manifest

    def test_live_exact_source_allows_original_commit_and_rollback(self):
        ref = self.s.source('run287 explicit human decision')
        update, _ = self.candidate([ref['source_id']])
        old = self.s.generation_id
        new = self.s.switch_generation(update, self.cfg, self.models)
        self.assertNotEqual(new, old)
        self.s.rollback(update)
        self.assertEqual(self.s.generation()['hashes'], {})
        self.assertEqual(self.s.integrity(True), [])

    def test_revoked_source_refuses_commit_without_changing_generation(self):
        ref = self.s.source('run287 revoked')
        update, _ = self.candidate([ref['source_id']])
        old = self.s.generation_id
        with self.s.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (ref['source_id'],))
        with self.assertRaisesRegex(ValueError, 'Lineage'):
            self.s.switch_generation(update, self.cfg, self.models)
        self.assertEqual(self.s.generation_id, old)
        self.assertEqual(self.s.one('SELECT status FROM updates WHERE id=?', (update,))['status'], 'PENDING_APPROVAL')

    def test_missing_and_malformed_source_ids_refuse(self):
        for source_ids in [['src_nonexistent'], 'src_wrong_shape', [True], [None], [0]]:
            with self.subTest(source_ids=source_ids):
                update, _ = self.candidate(source_ids)
                with self.assertRaises(ValueError):
                    self.s.switch_generation(update, self.cfg, self.models)
                self.assertEqual(self.s.generation()['hashes'], {})

    def test_forget_during_training_before_lineage_publication_refuses_late_approval(self):
        e = self.s.event(self.session, 'Projekt Run287 Budget?')
        mid = Memory(self.s, self.cfg).feedback(e['event_id'], 'fact', '400 Euro')
        sid = self.s.one('SELECT source_id FROM memories WHERE id=?', (mid,))['source_id']
        update, manifest = self.candidate([], status='SHADOW_TRAINING')
        # The optimizer has observed this source, but has not yet published its
        # source_ids into the update manifest. Forget cannot quarantine by ID.
        Memory(self.s, self.cfg).forget(mid)
        self.assertEqual(self.s.one('SELECT deleted FROM sources WHERE id=?', (sid,))['deleted'], 1)
        manifest['source_ids'] = [sid]
        with self.s.tx() as c:
            c.execute('UPDATE updates SET status=?,manifest=? WHERE id=?',
                      ('PENDING_APPROVAL', dumps(manifest), update))
        old = self.s.generation_id
        with self.assertRaisesRegex(ValueError, 'Lineage'):
            self.s.switch_generation(update, self.cfg, self.models)
        self.assertEqual(self.s.generation_id, old)
        self.assertEqual(self.s.generation()['hashes'], {})
        self.assertEqual(self.s.integrity(True), [])


if __name__ == '__main__':
    unittest.main()
