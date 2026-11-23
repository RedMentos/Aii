"""V14 A4 attention outcomes: durable exactly-once receipts in real Runtime/Store SQLite."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest

from v13.runtime import Runtime
from v13.attention import Attention, KEY
from v13.neuromod import Neuromod

RECEIPT_PREFIX = "ATTENTION_OUTCOME_RECEIPT:"


class AttentionOutcomeReceiptV14(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.n = Neuromod(self.r.store)
        self.a = Attention(self.r.store, None, self.n)
        self.event = self.r.store.event(self.r.session, "V14 source-bound attention outcome test event")

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.tmp.cleanup()

    def granted(self, count=1):
        requests = [
            self.a.request(self.event["event_id"], "JEF", "MEMORY", "recall", budget=1)
            for _ in range(count)
        ]
        responses = self.a.admit(self.event["event_id"], requests, budget=count + 1)
        self.assertEqual(len(responses), count)
        self.assertTrue(all(p["status"] == "GRANTED" for p in responses))
        return [p["packet_id"] for p in responses]

    def policy(self):
        return self.a.report()["policy"].get("recall|MEMORY")

    def test_evicted_old_response_cannot_be_recredited_after_34_outcomes(self):
        ids = self.granted(34)
        for rid in ids:
            self.a.outcome(rid, 1.0)
        before = self.policy()
        self.assertEqual(before["n"], 34)
        self.assertEqual(len(self.r.store.rows("SELECT id FROM packets WHERE kind='ModulatorPacket'")), 34)
        self.assertLessEqual(
            len(self.r.store.state(KEY)[0]["policy"]["recall|MEMORY"]["outcomes"]), 32
        )

        with self.assertRaisesRegex(ValueError, "Ergebnis schon verbucht"):
            self.a.outcome(ids[0], -1.0)
        self.assertEqual(self.policy(), before)
        receipt = self.r.store.state(RECEIPT_PREFIX + ids[0])[0]
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["response_packet_id"], ids[0])
        self.assertEqual(receipt["policy_key"], "recall|MEMORY")
        self.assertEqual(receipt["source_ref_count"], 0)
        self.assertEqual(self.a.report()["mode"], "SHADOW")

    def test_policy_receipt_and_n10_modulator_roll_back_together(self):
        rid = self.granted()[0]
        original = self.n.signal_in_transaction

        def fail_after_insert(connection, *args, **kwargs):
            original(connection, *args, **kwargs)
            raise RuntimeError("injected N10 insert failure")

        self.n.signal_in_transaction = fail_after_insert
        with self.assertRaisesRegex(RuntimeError, "injected N10 insert failure"):
            self.a.outcome(rid, 1.0)
        self.assertIsNone(self.r.store.state(RECEIPT_PREFIX + rid)[0])
        self.assertIsNone(self.policy())
        self.assertEqual(
            self.r.store.rows(
                "SELECT id FROM packets WHERE kind='ModulatorPacket' AND event_id=?",
                (self.event["event_id"],),
            ),
            [],
        )

        self.n.signal_in_transaction = original
        self.a.outcome(rid, 1.0)
        receipt = self.r.store.state(RECEIPT_PREFIX + rid)[0]
        self.assertIsNotNone(receipt)
        self.assertTrue(receipt["modulator_packet_id"])
        self.assertEqual(self.policy()["n"], 1)
        self.assertEqual(
            len(self.r.store.rows(
                "SELECT id FROM packets WHERE kind='ModulatorPacket' AND event_id=?",
                (self.event["event_id"],),
            )),
            1,
        )

    def test_durable_receipt_survives_runtime_restart(self):
        ids = self.granted(34)
        for rid in ids:
            self.a.outcome(rid, 1.0)
        before = self.policy()
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.n = Neuromod(self.r.store)
        self.a = Attention(self.r.store, None, self.n)

        with self.assertRaisesRegex(ValueError, "Ergebnis schon verbucht"):
            self.a.outcome(ids[0], -1.0)
        self.assertEqual(self.policy(), before)
        receipt = self.r.store.state(RECEIPT_PREFIX + ids[0])[0]
        self.assertIsNotNone(receipt)
        self.assertTrue(receipt["modulator_packet_id"])
        persisted = self.r.store.rows(
            "SELECT payload FROM packets WHERE id=? AND kind='ModulatorPacket'",
            (receipt["modulator_packet_id"],),
        )
        self.assertEqual(len(persisted), 1)
        persisted_packet = json.loads(persisted[0]["payload"])
        self.assertIn("reward_error", persisted_packet["channels"])
        self.assertIn("surprise", persisted_packet["channels"])

    def test_concurrent_same_response_is_credited_once(self):
        rid = self.granted()[0]
        barrier = threading.Barrier(2)

        def submit():
            barrier.wait(timeout=10)
            try:
                return ("OK", self.a.outcome(rid, 1.0))
            except ValueError as exc:
                return ("REJECT", str(exc))

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(), range(2)))
        self.assertEqual(sorted(x[0] for x in results), ["OK", "REJECT"])
        self.assertIn(
            "Ergebnis schon verbucht",
            next(x[1] for x in results if x[0] == "REJECT"),
        )
        self.assertEqual(self.policy()["n"], 1)
        self.assertEqual(len(self.r.store.rows("SELECT id FROM packets WHERE kind='ModulatorPacket' AND event_id=?", (self.event["event_id"],))), 1)
        self.assertIsNotNone(self.r.store.state(RECEIPT_PREFIX + rid)[0])

    def test_n10_transactional_signal_rejects_non_transaction_connection(self):
        with self.assertRaisesRegex(ValueError, "needs an active Store transaction"):
            self.n.signal_in_transaction(
                self.r.store.db,
                self.event["event_id"],
                path="attention_policy",
                source_class="internal_crosscheck",
                reward_error=-0.25,
                surprise=0.25,
            )

    def test_non_granted_response_never_writes_receipt_or_policy(self):
        req = self.a.request(
            self.event["event_id"], "JEF", "MEMORY", "recall", budget=100
        )
        resp = self.a.admit(self.event["event_id"], [req], budget=1)[0]
        self.assertEqual(resp["status"], "TOO_EXPENSIVE")
        with self.assertRaises(ValueError):
            self.a.outcome(resp["packet_id"], 1.0)
        self.assertIsNone(self.r.store.state(RECEIPT_PREFIX + resp["packet_id"])[0])
        self.assertIsNone(self.policy())


if __name__ == "__main__":
    unittest.main()
