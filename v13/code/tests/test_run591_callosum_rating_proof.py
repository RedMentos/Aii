"""Run591: human Callosum channel ratings require real source-bound packets and count once."""
import json
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13 import callosum as C


class Run591CallosumRatingProof(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.c = C.Callosum(self.r.store)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self, text="question"):
        p = self.r.store.event(self.r.session, text)
        return p["event_id"], p["brain_generation_id"]

    def message(self, eid, gen, refs=()):
        offer = {"role": "B1_DETAIL", "event_id": eid, "brain_generation_id": gen,
                 "packet_id": "pkt_sender_" + eid, "evidence_refs": list(refs),
                 "rejected_quotes": 0,
                 "offer": {"summary": "Answer 42", "quotes": [],
                           "uncertainty": "", "needs_reentry": False}}
        return self.r.cognition.communicate(offer, "B2_GIST")["message_packet_id"]

    def utility_n(self, channel="SOURCE_EXACT"):
        st = self.c._load()[0]
        return (st["dirs"]["B1_TO_B2"]["u"].get(channel) or {"n": 0})["n"]

    def test_real_message_receives_one_rating_even_after_restart(self):
        eid, gen = self.event()
        mid = self.message(eid, gen)
        self.assertEqual(self.c.on_rating(eid, .7), {"updated": 1})
        self.assertEqual(self.c.on_rating(eid, .9), {"updated": 0})
        self.assertTrue(all(m.get("rated") for m in self.c._load()[0]["pending"][eid]
                            if m["msg"] == mid))
        self.r.close()
        self.r = Runtime(self.home)
        self.c = C.Callosum(self.r.store)
        self.assertEqual(self.c.on_rating(eid, .8), {"updated": 0})

    def test_missing_packet_cannot_gain_policy_experience(self):
        eid, _ = self.event()
        self.c.note(eid, "pkt_missing", "B1_DETAIL", "B2_GIST",
                    "SOURCE_EXACT", "SOURCE_EXACT", False, 0.)
        before = self.c._load()[0]
        self.assertEqual(self.c.on_rating(eid, 1.), {"updated": 0})
        self.assertEqual(self.c._load()[0], before)

    def test_packet_from_other_event_cannot_be_rated(self):
        e1, gen = self.event("first")
        mid = self.message(e1, gen)
        e2, _ = self.event("second")
        self.c.note(e2, mid, "B1_DETAIL", "B2_GIST",
                    "SOURCE_EXACT", "SOURCE_EXACT", False, 0.)
        self.assertEqual(self.c.on_rating(e2, .8), {"updated": 0})
        self.assertEqual(self.c.on_rating(e1, .8), {"updated": 1})

    def test_tampered_packet_channel_is_not_rated(self):
        eid, gen = self.event()
        mid = self.message(eid, gen)
        row = self.r.store.one("SELECT payload FROM packets WHERE id=?", (mid,))
        p = json.loads(row["payload"])
        p["channel"] = "SYMBOLIC" if p["channel"] != "SYMBOLIC" else "CONTROL"
        with self.r.store.tx() as db:
            db.execute("UPDATE packets SET payload=? WHERE id=?", (json.dumps(p), mid))
        self.assertEqual(self.c.on_rating(eid, .8), {"updated": 0})
        self.assertEqual(sum(q["n"] for q in self.c._load()[0]["dirs"]["B1_TO_B2"]["u"].values()), 0)

    def test_deleted_source_ref_cannot_drive_rating(self):
        eid, gen = self.event()
        ref = self.r.store.source("verified evidence")
        self.message(eid, gen, [ref])
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?", (ref["source_id"],))
        self.assertEqual(self.c.on_rating(eid, .8), {"updated": 0})

    def test_duplicate_pending_packet_ids_count_once_across_calls(self):
        eid, gen = self.event()
        mid = self.message(eid, gen)
        st = self.c._load()[0]
        original = st["pending"][eid][0]
        self.c.note(eid, mid, "B1_DETAIL", "B2_GIST",
                    original["channel"], original["proposal"], False, 0.)
        self.assertEqual(self.c.on_rating(eid, .6), {"updated": 1})
        self.assertEqual(self.c.on_rating(eid, .6), {"updated": 0})
        self.assertTrue(all(m.get("rated") for m in self.c._load()[0]["pending"][eid]))

    def test_nonfinite_and_nonnumeric_utility_rejected(self):
        eid, gen = self.event()
        self.message(eid, gen)
        for utility in (float("nan"), float("inf"), -float("inf"), True, "1.0"):
            with self.subTest(utility=utility):
                with self.assertRaises(ValueError):
                    self.c.on_rating(eid, utility)
        self.assertEqual(self.c.on_rating(eid, .5), {"updated": 1})


if __name__ == "__main__":
    unittest.main()
