from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock

from v13 import route_probation as RP
from v13.runtime import Runtime


class RouteProbationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.r = Runtime(Path(self.tmp.name))
    def tearDown(self):
        self.r.close(); self.tmp.cleanup()

    def _update(self, status='PENDING_APPROVAL', component='route'):
        with self.r.store.tx() as c:
            c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)', ('upd_x', self.r.store.generation_id, status, 'checkpoints/x.npz', 'h', json.dumps({'component': component}), 0.))

    def test_start_requires_open_route_update(self):
        self._update(component='wake')
        with self.assertRaises(ValueError): RP.start(self.r, 'upd_x')

    def _run(self, cand, labels):
        self._update(); RP.start(self.r, 'upd_x')
        preds = iter(cand)
        with mock.patch.object(RP, '_predict', lambda r, path, text, sid: next(preds)):
            for i, lab in enumerate(labels):
                e = self.r.store.event(self.r.session, 'Frage %d' % i); st = RP.observe(self.r, e['event_id'], lab)
        return st

    def test_ready_when_candidate_beats_scaffold_prospectively(self):
        st = self._run(['simple'] * 8, ['simple'] * 8)   # no active head: parent = scaffold
        self.assertEqual(st['observed'], 8); self.assertEqual(st['candidate_hits'], 8); self.assertEqual(st['verdict'], 'READY')

    def test_reject_when_candidate_is_worse(self):
        st = self._run(['gist'] * 8, ['simple'] * 8)
        self.assertEqual(st['candidate_hits'], 0); self.assertIn(st['verdict'], ('REJECT',))

    def test_stale_when_update_no_longer_pending(self):
        self._update(); RP.start(self.r, 'upd_x')
        with self.r.store.tx() as c: c.execute("UPDATE updates SET status='REJECTED' WHERE id='upd_x'")
        e = self.r.store.event(self.r.session, 'Hallo'); self.assertEqual(RP.observe(self.r, e['event_id'], 'simple')['verdict'], 'STALE')


if __name__ == '__main__':
    unittest.main()
