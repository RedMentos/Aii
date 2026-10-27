"""Sleep A retention must recover the exact source-backed memory, not any equal value."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from v13.config import initialize
from v13.store import Store
from v13.memory import Memory
from v13.sleep import SleepCycle


class SleepAExactRecallIdentityReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.store = Store(self.home)
        self.addCleanup(self.store.close)
        self.session = self.store.new_session()
        mem = Memory(self.store, self.cfg)
        self.first = self.store.event(self.session, 'Projekt Alpha Budget?')
        self.target_id = mem.feedback(self.first['event_id'], 'fact', '120 Euro')
        self.second = self.store.event(self.session, 'Projekt Beta Budget?')
        self.other_id = mem.feedback(self.second['event_id'], 'fact', '120 Euro')
        self.assertNotEqual(self.target_id, self.other_id)

    def probe_with(self, rows):
        fake = SimpleNamespace(recall=lambda query, session: rows)
        cycle = SleepCycle(self.store, self.cfg, fake, home=self.home)
        return cycle._probe({'event_id': self.first['event_id']})

    def test_same_value_from_different_memory_is_not_retention(self):
        outcome, errors, detail = self.probe_with([
            {'id': self.other_id, 'value': '120 Euro'}])
        self.assertEqual(outcome, 'FAIL')
        self.assertIn('RECALL_MISS:' + self.target_id, errors)
        self.assertIn('memory_retrieval', detail['affected_paths'])

    def test_value_without_memory_id_is_not_retention(self):
        outcome, errors, detail = self.probe_with([{'value': '120 Euro'}])
        self.assertEqual(outcome, 'FAIL')
        self.assertIn('RECALL_MISS:' + self.target_id, errors)

    def test_exact_memory_id_still_passes(self):
        outcome, errors, detail = self.probe_with([
            {'id': self.target_id, 'value': '120 Euro'}])
        self.assertEqual(outcome, 'PASS', (outcome, errors, detail))
        self.assertEqual(errors, [])
        self.assertTrue(all(check['pass'] for check in detail['checks']))


if __name__ == '__main__':
    unittest.main()
