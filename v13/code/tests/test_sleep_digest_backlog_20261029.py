"""S7 day digest backlog catch-up; real Store source lineage, no models."""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import sleep_offline as S
from v13.history import native_history


class DigestBacklog(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.r=Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled","off")
    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()
    def turn(self,n,session=None,answer=True):
        sess=session or self.r.session
        e=self.r.store.event(sess,"Source-valid question %03d with value %03d."%(n,n))
        if answer:
            self.r.store.message(sess,e["event_id"],"assistant",
                                 "Direct source copy answer %03d."%n,
                                 status="FINAL",metadata={"direct_source_copy":True})
        return e

    def test_150_turns_catch_up_oldest_first_in_bounded_batches(self):
        events=[self.turn(i) for i in range(150)]
        d1=S.digest(self.r.store)
        self.assertEqual(d1["turns"],64)
        st,_=self.r.store.state(S.KEY)
        self.assertEqual(len(st["sessions"][self.r.session]["entries"]),64)
        self.assertEqual(st["sessions"][self.r.session]["entries"][0]["event_id"],
                         events[0]["event_id"])
        self.assertEqual(S.digest(self.r.store)["turns"],64)
        self.assertEqual(S.digest(self.r.store)["turns"],22)
        self.assertEqual(S.digest(self.r.store)["turns"],0)
        st,_=self.r.store.state(S.KEY)
        entries=st["sessions"][self.r.session]["entries"]
        self.assertEqual(len(entries),S.ENTRIES_MAX)
        self.assertEqual(entries[0]["event_id"],events[54]["event_id"])
        self.assertEqual(entries[-1]["event_id"],events[-1]["event_id"])
        self.assertEqual(S.view(self.r.store,self.r.session,cap=100000)["entries"],96)

    def test_native_history_after_id_returns_earliest_complete_pairs(self):
        events=[self.turn(i) for i in range(70)]
        first,_=native_history(self.r.store,self.r.session,"",S.TURNS_MAX,after_id=0)
        self.assertEqual(len(first),128)
        self.assertEqual(first[0]["event_id"],events[0]["event_id"])
        self.assertEqual(first[-1]["event_id"],events[63]["event_id"])
        later,_=native_history(self.r.store,self.r.session,"",S.TURNS_MAX,after_id=first[-1]["id"])
        self.assertEqual(len(later),12)
        self.assertEqual(later[0]["event_id"],events[64]["event_id"])
        with self.assertRaises(ValueError):
            native_history(self.r.store,self.r.session,"",10,after_id=-1)

    def test_deleted_old_source_not_replayed_and_does_not_block_catchup(self):
        events=[self.turn(i) for i in range(75)]
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (events[5]["source_ref"]["source_id"],))
        self.assertEqual(S.digest(self.r.store)["turns"],63)
        self.assertEqual(S.digest(self.r.store)["turns"],11)
        self.assertEqual(S.digest(self.r.store)["turns"],0)
        st,_=self.r.store.state(S.KEY)
        ids={x["event_id"] for x in st["sessions"][self.r.session]["entries"]}
        self.assertNotIn(events[5]["event_id"],ids)
        self.assertIn(events[74]["event_id"],ids)

    def test_incomplete_boundary_turn_is_not_lost_when_assistant_arrives(self):
        for i in range(64):self.turn(i)
        pending=self.turn(64,answer=False)
        self.assertEqual(S.digest(self.r.store)["turns"],64)
        self.assertEqual(S.digest(self.r.store)["turns"],0)
        self.r.store.message(self.r.session,pending["event_id"],"assistant",
                             "Direct source copy answer 064.",
                             status="FINAL",metadata={"direct_source_copy":True})
        self.assertEqual(S.digest(self.r.store)["turns"],1)
        st,_=self.r.store.state(S.KEY)
        self.assertEqual(st["sessions"][self.r.session]["entries"][-1]["event_id"],
                         pending["event_id"])


if __name__=="__main__":
    unittest.main()
