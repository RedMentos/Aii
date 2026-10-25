"""Run308 RED-first: exactly-once learned Attention outcomes beyond 32-item cache.

Actual Runtime/Store SQLite and F1 AttentionRequest/Response packets. Software only.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import unittest

from v13.runtime import Runtime
from v13.attention import Attention, KEY


RECEIPT_PREFIX = 'ATTENTION_OUTCOME_RECEIPT:'


class AttentionOutcomeReceiptRun308(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.a = Attention(self.r.store)
        self.event = self.r.store.event(self.r.session, 'RUN308 real attention feedback event')

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.tmp.cleanup()

    def granted(self, count=1):
        requests = [
            self.a.request(self.event['event_id'], 'JEF', 'MEMORY', 'recall', budget=1)
            for _ in range(count)
        ]
        responses = self.a.admit(self.event['event_id'], requests, budget=count + 1)
        self.assertEqual(len(responses), count)
        self.assertTrue(all(p['status'] == 'GRANTED' for p in responses))
        return [p['packet_id'] for p in responses]

    def policy(self):
        return self.a.report()['policy'].get('recall|MEMORY')

    def test_evicted_old_response_cannot_be_recredited_after_34_outcomes(self):
        ids = self.granted(34)
        for rid in ids:
            self.a.outcome(rid, 1.)
        before = self.policy()
        self.assertEqual(before['n'], 34)
        self.assertLessEqual(len(self.r.store.state(KEY)[0]['policy']['recall|MEMORY']['outcomes']), 32)

        with self.assertRaisesRegex(ValueError, 'Ergebnis schon verbucht'):
            self.a.outcome(ids[0], -1.)
        self.assertEqual(self.policy(), before)
        receipt = self.r.store.state(RECEIPT_PREFIX + ids[0])[0]
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt['response_packet_id'], ids[0])
        self.assertEqual(self.a.report()['mode'], 'SHADOW')

    def test_durable_receipt_survives_restart(self):
        ids = self.granted(34)
        for rid in ids:
            self.a.outcome(rid, 1.)
        before = self.policy()
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.a = Attention(self.r.store)
        with self.assertRaisesRegex(ValueError, 'Ergebnis schon verbucht'):
            self.a.outcome(ids[0], -1.)
        self.assertEqual(self.policy(), before)
        self.assertIsNotNone(self.r.store.state(RECEIPT_PREFIX + ids[0])[0])

    def test_concurrent_same_response_is_credited_once(self):
        rid = self.granted()[0]
        barrier = threading.Barrier(2)

        def submit():
            barrier.wait(timeout=10)
            try:
                return ('OK', self.a.outcome(rid, 1.))
            except ValueError as exc:
                return ('REJECT', str(exc))

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(), range(2)))
        self.assertEqual(sorted(x[0] for x in results), ['OK', 'REJECT'])
        self.assertIn('Ergebnis schon verbucht', next(x[1] for x in results if x[0] == 'REJECT'))
        self.assertEqual(self.policy()['n'], 1)
        self.assertIsNotNone(self.r.store.state(RECEIPT_PREFIX + rid)[0])

    def test_non_granted_response_never_writes_receipt_or_policy(self):
        req = self.a.request(self.event['event_id'], 'JEF', 'MEMORY', 'recall', budget=100)
        resp = self.a.admit(self.event['event_id'], [req], budget=1)[0]
        self.assertEqual(resp['status'], 'TOO_EXPENSIVE')
        with self.assertRaises(ValueError):
            self.a.outcome(resp['packet_id'], 1.)
        self.assertIsNone(self.r.store.state(RECEIPT_PREFIX + resp['packet_id'])[0])
        self.assertIsNone(self.policy())


if __name__ == '__main__':
    unittest.main()
