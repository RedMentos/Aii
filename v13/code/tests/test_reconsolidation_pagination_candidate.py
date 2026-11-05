"""Real Store/SQLite tests for the opt-in pagination candidate. No model runs."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import reconsolidation_pagination_candidate as C
from v13.runtime import Runtime


class PaginationCandidate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.runtime = Runtime(self.home)
        self.store = self.runtime.store
        self.runtime.sleep.cycle.set_policy('enabled', 'off')

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def fact(self, question, value):
        event = self.store.event(self.runtime.session, question)
        return self.runtime.memory.feedback(event['event_id'], 'fact', value, 'record')

    def question(self, text='Welches Budget?'):
        return self.store.event(self.runtime.session, text)['event_id']

    def feedback(self, event, memory, label='relevant', permission='record'):
        return self.runtime.memory.retrieval_feedback(event, memory, label, permission)

    def scan(self, page_size=3):
        reports = []
        for _ in range(1000):
            report = C.process_page(self.store, page_size)
            reports.append(report)
            if report['complete']:
                return reports
        self.fail('scan did not finish')

    def events(self):
        return self.store.state(C.KEY, {'events': []})[0]['events']

    def test_identical_timestamps_restart_and_exactly_once(self):
        memory = self.fact('Budget Aurora?', '120 Euro')
        event = self.question()
        ids = [self.feedback(event, memory, 'relevant' if i % 2 else 'irrelevant',
                             'learn' if i % 3 == 0 else 'record') for i in range(9)]
        with self.store.tx() as db:
            db.execute("UPDATE feedback SET created=42 WHERE kind='retrieval'")
        first = C.process_page(self.store, page_size=3)
        self.assertEqual((first['added'], first['complete']), (3, False))
        self.runtime.close()
        self.runtime = Runtime(self.home)
        self.store = self.runtime.store
        self.scan(page_size=3)
        self.assertEqual([x['feedback_id'] for x in self.events()], ids)
        self.assertEqual([x['created'] for x in self.events()], [42.] * 9)
        self.assertEqual({x['permission'] for x in self.events()}, {'record', 'learn'})
        self.scan(page_size=2)
        self.assertEqual([x['feedback_id'] for x in self.events()], ids)

    def test_512_orphans_do_not_block_later_valid_feedback(self):
        old = self.fact('Altes Budget?', '120 Euro')
        current = self.fact('Neues Budget?', '90 Euro')
        event = self.question()
        for _ in range(512):
            self.feedback(event, old)
        self.runtime.memory.forget(old)
        valid = self.feedback(event, current, 'irrelevant')
        reports = self.scan(page_size=128)
        self.assertEqual(sum(x['invalid'] for x in reports), 512)
        self.assertEqual([x['feedback_id'] for x in self.events()], [valid])
        self.scan(page_size=128)
        self.assertEqual([x['feedback_id'] for x in self.events()], [valid])

    def test_late_old_timestamp_and_recycled_low_rowid(self):
        memory = self.fact('Budget Aurora?', '120 Euro')
        event = self.question()
        original = [self.feedback(event, memory) for _ in range(5)]
        first = C.process_page(self.store, page_size=2)
        self.assertFalse(first['complete'])
        late_low = self.feedback(event, memory, 'irrelevant')
        late_high = self.feedback(event, memory)
        with self.store.tx() as db:
            db.execute('UPDATE feedback SET rowid=-100,created=0 WHERE id=?', (late_low,))
            db.execute('UPDATE feedback SET created=0 WHERE id=?', (late_high,))
        self.scan(page_size=2)
        self.assertEqual([x['feedback_id'] for x in self.events()], original + [late_high])
        self.scan(page_size=2)
        self.assertEqual([x['feedback_id'] for x in self.events()], original + [late_high, late_low])
        self.scan(page_size=2)
        self.assertEqual(len(self.events()), 7)

    def test_repaired_invalid_row_can_be_seen_on_next_sweep(self):
        memory = self.fact('Budget Aurora?', '120 Euro')
        event = self.question()
        later_repaired = self.feedback(event, memory)
        valid = self.feedback(event, memory, 'irrelevant')
        with self.store.tx() as db:
            db.execute("UPDATE feedback SET value='bad' WHERE id=?", (later_repaired,))
        self.scan(page_size=1)
        self.assertEqual([x['feedback_id'] for x in self.events()], [valid])
        with self.store.tx() as db:
            db.execute("UPDATE feedback SET value='relevant' WHERE id=?", (later_repaired,))
        self.scan(page_size=1)
        self.assertEqual([x['feedback_id'] for x in self.events()], [valid, later_repaired])

    def test_interruption_rolls_back_page_and_watermark(self):
        memory = self.fact('Budget Aurora?', '120 Euro')
        event = self.question()
        ids = [self.feedback(event, memory) for _ in range(5)]
        C.process_page(self.store, page_size=2)
        before = self.store.state(C.KEY)
        real = C._extract
        calls = []
        def interrupt(store, row):
            calls.append(row['id'])
            if len(calls) == 2:
                raise RuntimeError('simulated interruption')
            return real(store, row)
        with patch.object(C, '_extract', side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError, 'simulated interruption'):
                C.process_page(self.store, page_size=2)
        self.assertEqual(self.store.state(C.KEY), before)
        self.runtime.close()
        self.runtime = Runtime(self.home)
        self.store = self.runtime.store
        self.scan(page_size=2)
        self.assertEqual([x['feedback_id'] for x in self.events()], ids)

    def test_candidate_cannot_modify_existing_recon_facts_or_recall(self):
        a = self.fact('Budget Aurora Plan?', '120 Euro')
        b = self.fact('Budget Aurora Notiz?', '90 Euro')
        event = self.question('Budget Aurora?')
        self.feedback(event, a, 'irrelevant')
        self.feedback(event, b, 'relevant', 'learn')
        self.store.set_state('BP7_RECON', {'revision': 'bp7-recon-v1', 'memories': {},
                                          'cursor': 999., 'seen': ['legacy'], 'runs': 1})
        self.runtime.cfg['reconsolidation'] = 'active'
        before_memories = self.store.rows('SELECT * FROM memories ORDER BY id')
        before_recon = self.store.state('BP7_RECON')
        before_recall = [x['id'] for x in self.runtime.memory.recall('Budget Aurora', self.runtime.session)]
        self.scan(page_size=1)
        self.assertEqual(self.store.rows('SELECT * FROM memories ORDER BY id'), before_memories)
        self.assertEqual(self.store.state('BP7_RECON'), before_recon)
        self.assertEqual([x['id'] for x in self.runtime.memory.recall('Budget Aurora', self.runtime.session)], before_recall)
        serialized = json.dumps(self.store.state(C.KEY)[0])
        self.assertNotIn('120 Euro', serialized)
        self.assertNotIn('90 Euro', serialized)

    def test_concurrent_page_calls_commit_each_feedback_once(self):
        memory = self.fact('Budget Aurora?', '120 Euro')
        event = self.question()
        ids = [self.feedback(event, memory) for _ in range(24)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            reports = list(pool.map(lambda _: C.process_page(self.store, page_size=3), range(8)))
        self.assertEqual(sum(report['added'] for report in reports), len(ids))
        self.scan(page_size=3)
        self.assertEqual([x['feedback_id'] for x in self.events()], ids)

    def test_invalid_page_size_or_candidate_state_fails_closed(self):
        for size in (0, -1, 1025, True, 1.0):
            with self.assertRaises(ValueError):
                C.process_page(self.store, size)
        self.store.set_state(C.KEY, {'revision': 'different', 'events': [], 'cursor': None, 'sweeps': 0})
        before = self.store.state(C.KEY)
        with self.assertRaises(ValueError):
            C.process_page(self.store)
        self.assertEqual(self.store.state(C.KEY), before)


if __name__ == '__main__':
    unittest.main()
