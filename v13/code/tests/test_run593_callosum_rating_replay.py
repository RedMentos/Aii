"""Run593: late Callosum duplicate notes must not replay human policy credit."""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.callosum import Callosum


class RatingReplay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.c = Callosum(self.r.store)
        p = self.r.store.event(self.r.session, "Question 42")
        self.eid, self.gen = p["event_id"], p["brain_generation_id"]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def message(self):
        offer = {"role": "B1_DETAIL", "event_id": self.eid,
                 "brain_generation_id": self.gen,
                 "packet_id": "sender_" + self.eid, "evidence_refs": [],
                 "rejected_quotes": 0,
                 "offer": {"summary": "42", "quotes": [], "uncertainty": "",
                           "needs_reentry": False}}
        return self.r.cognition.communicate(offer, "B2_GIST")["message_packet_id"]

    def n(self):
        d = self.c._load()[0]["dirs"]["B1_TO_B2"]["u"]
        return sum(q["n"] for q in d.values())

    def late_note(self, mid):
        original = next(m for m in self.c._load()[0]["pending"][self.eid]
                        if m["msg"] == mid)
        self.c.note(self.eid, mid, "B1_DETAIL", "B2_GIST",
                    original["channel"], original["proposal"], False, 0.)

    def test_note_after_successful_rating_does_not_replay(self):
        mid = self.message()
        self.assertEqual(self.c.on_rating(self.eid, .6), {"updated": 1})
        self.late_note(mid)
        self.assertEqual(self.c.on_rating(self.eid, .9), {"updated": 0})
        self.assertEqual(self.n(), 1)
        self.assertTrue(all(m.get("rated") for m in self.c._load()[0]["pending"][self.eid]))

    def test_partially_rated_legacy_pending_is_repaired_without_credit(self):
        mid = self.message()
        self.late_note(mid)
        st, version = self.c._load()
        xs = st["pending"][self.eid]
        self.assertEqual(len(xs), 2)
        xs[0]["rated"] = True
        xs[1].pop("rated", None)
        self.r.store.set_state("J_CALLOSUM", st, expected=version)
        self.assertEqual(self.c.on_rating(self.eid, .8), {"updated": 0})
        self.assertEqual(self.n(), 0)
        self.assertTrue(all(m.get("rated") for m in self.c._load()[0]["pending"][self.eid]))

    def test_distinct_real_packet_remains_eligible(self):
        first = self.message()
        self.assertEqual(self.c.on_rating(self.eid, .6), {"updated": 1})
        second = self.message()
        self.assertNotEqual(first, second)
        self.assertEqual(self.c.on_rating(self.eid, .7), {"updated": 1})
        self.assertEqual(self.n(), 2)
        self.late_note(first)
        self.assertEqual(self.c.on_rating(self.eid, .8), {"updated": 0})
        self.assertEqual(self.n(), 2)

    def test_late_duplicate_remains_spent_after_restart(self):
        mid = self.message()
        self.assertEqual(self.c.on_rating(self.eid, .5), {"updated": 1})
        self.late_note(mid)
        self.r.close()
        self.r = Runtime(self.home)
        self.c = Callosum(self.r.store)
        self.assertEqual(self.c.on_rating(self.eid, .9), {"updated": 0})
        self.assertEqual(self.n(), 1)


if __name__ == "__main__":
    unittest.main()
