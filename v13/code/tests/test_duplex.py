"""WP-N14 live/full-duplex text timeline (§24.30). Synthetic runner; no models."""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13 import duplex
from v13.common import Cancelled
from v13.operator import Operator
from v13.runtime import Runtime

class Decide(unittest.TestCase):
    def test_cues_and_modes(self):
        for text in ('stop', 'Wait!', 'never mind', 'Stopp.', 'warte', 'abbrechen'):
            self.assertEqual(duplex.decide(text), ('INTERRUPT', 'STOP'), text)
        for text in ('no, I meant Berlin', 'Actually make it shorter', 'Nein, ich meinte Paris'):
            self.assertEqual(duplex.decide(text), ('REVISE', 'CORRECTION'), text)
        self.assertEqual(duplex.decide('stop the music in my story please'), ('CONTINUE', 'OVERLAP'))  # stop + content is not a cut
        self.assertEqual(duplex.decide('what about Rome?'), ('CONTINUE', 'OVERLAP'))
        self.assertEqual(duplex.decide('what about Rome?', 'interrupt'), ('INTERRUPT', 'OVERLAP'))
        self.assertEqual(duplex.decide('stop', 'off'), ('CONTINUE', 'OVERLAP'))
        with self.assertRaises(ValueError): duplex.decide('x', 'loud')

class Live(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled', 'off'); self.seen = []; self.started = threading.Event()
        def generate(messages, cancel, deadline, *a, **k):
            self.seen.append(messages); slow = 'capital' in messages[-1]['content']
            for i in range(200 if slow else 1):
                if cancel.is_set(): raise Cancelled('cancelled')
                if i == 1: self.started.set()
                yield 'word%d ' % i
                if slow: time.sleep(.01)
        self.r._route = Mock(return_value=('simple', {'source': 'TEST_ROUTE_SEAM'}))
        self.r.pool.get = Mock(return_value=SimpleNamespace(role='C3_LANGUAGE', last_metrics={}, generate=generate))
        self.r.learner.output_delta = Mock(return_value=None)
    def tearDown(self): self.r.close(); self.tmp.cleanup()
    def wait(self):
        until = time.monotonic()+20
        while not self.r.idle() and time.monotonic() < until: time.sleep(.005)
    def answer(self, eid):
        return self.r.store.one("SELECT * FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1", (eid,))

    def test_correction_cuts_answer_hands_off_and_stays_provisional(self):
        first = self.r.submit('Tell me a long story about the capital of France')
        self.assertTrue(self.started.wait(10))
        t0 = time.monotonic(); second = self.r.submit('No, I meant Germany'); took = time.monotonic()-t0
        self.assertLess(took, .5)  # the live path never waits for the running answer
        self.wait()
        cut = self.answer(first); meta = json.loads(cut['metadata'])
        self.assertEqual(cut['status'], 'CANCELLED'); self.assertTrue(cut['text'].startswith('word0'))
        self.assertEqual(meta['duplex'], {'interrupted_by': second, 'relation': 'CORRECTION', 'provisional': True, 'authority': 'PROVISIONAL_LIVE_NOT_LEARNED'})
        nxt = self.answer(second); self.assertEqual(nxt['status'], 'FINAL')
        answer_call = json.dumps(next(m for m in self.seen if m[-1]['content'] == 'No, I meant Germany'))
        self.assertIn('Live handoff', answer_call); self.assertIn('capital of France', answer_call); self.assertIn('word0', answer_call)
        refs = json.loads(nxt['metadata'])['context_source_refs']
        first_src = json.loads(self.r.store.one('SELECT packet FROM events WHERE id=?', (first,))['packet'])['source_ref']
        self.assertIn(first_src, refs)  # the cut question's source survives the handoff
        from v13.history import native_history
        hist, _ = native_history(self.r.store, self.r.session, 'evt_none', 8)
        self.assertNotIn(first, [h['event_id'] for h in hist])  # provisional answer never becomes native history
        st = duplex.status(self.r); self.assertEqual(st['counters']['REVISE'], 1); self.assertEqual(st['pending_handoffs'], 0)
        tel = self.r.store.rows("SELECT metrics FROM telemetry WHERE kind='duplex'")
        self.assertEqual(json.loads(tel[0]['metrics'])['decision'], 'REVISE')

    def test_plain_overlap_keeps_turn_taking(self):
        first = self.r.submit('Tell me a long story about the capital of Italy')
        self.assertTrue(self.started.wait(10)); second = self.r.submit('Thanks, and the weather?'); self.wait()
        self.assertEqual(self.answer(first)['status'], 'FINAL'); self.assertEqual(self.answer(second)['status'], 'FINAL')
        self.assertNotIn('Live handoff', json.dumps(next(m for m in self.seen if m[-1]['content'] == 'Thanks, and the weather?')))
        self.assertEqual(duplex.status(self.r)['counters']['CONTINUE'], 1)

    def test_operator_mode_switch(self):
        op = Operator(self.r)
        self.assertEqual(op.run(':duplex interrupt'), 'duplex_mode = interrupt'); self.assertEqual(self.r.cfg['duplex_mode'], 'interrupt')
        self.assertEqual(json.loads(op.run(':duplex'))['mode'], 'interrupt')
        with self.assertRaises(ValueError): op.run(':duplex loud')

if __name__ == '__main__':
    unittest.main()
