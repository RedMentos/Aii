"""Preregistered World-Model selection/action provenance regression witnesses."""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.contracts import packet
from v13 import world_model as wm


class WorldModelActionSelectionBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name))

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def event(self):
        return self.r.store.event(self.r.session, "Observed local digital action")

    def selection(self, event, route):
        p = packet(
            "ActionSelection", "C5_ACTION_GATE", event["event_id"],
            event["brain_generation_id"], [event["source_ref"]],
            selected={"action_id": "TEXT_REPORT", "action_type": "TEXT_REPORT",
                      "score": 0., "permission_class": "local_text_only",
                      "focal_support": 0.},
            candidates=[], suppressed=[], permission_class="local_text_only",
            route_hint=route)
        self.r.store.add_packet("ActionSelection", p)
        return p

    def action(self, event):
        aid = self.r.store.start_action(
            event["event_id"], event["brain_generation_id"],
            forecast={"input_chars": 100, "resource_state": "NORMAL"})
        self.r.store.finish_action(
            aid, "FINAL", {"action_duration_s": 1.0, "characters": 42})
        created = self.r.store.one(
            "SELECT created FROM actions WHERE id=?", (aid,))["created"]
        return aid, created

    def set_created(self, selection, created):
        with self.r.store.tx() as c:
            c.execute("UPDATE packets SET created=? WHERE id=?",
                      (created, selection["packet_id"]))

    def test_late_packet_cannot_relabel_finished_action(self):
        e = self.event()
        first = self.selection(e, "simple")
        _, started = self.action(e)
        self.set_created(first, started - 1)
        before = wm.transitions(self.r.store)
        self.assertEqual(len(before), 1)
        self.assertEqual(before[0]["a"], "simple")
        late = self.selection(e, "detail")
        self.set_created(late, started + 1)
        after = wm.transitions(self.r.store)
        self.assertEqual(len(after), 1)
        self.assertEqual(after[0]["a"], "simple")

    def test_post_dispatch_only_selection_is_not_training_evidence(self):
        e = self.event()
        _, started = self.action(e)
        late = self.selection(e, "both")
        self.set_created(late, started + 1)
        self.assertEqual(wm.transitions(self.r.store), [])

    def test_two_predispatch_selections_are_ambiguous(self):
        e = self.event()
        a = self.selection(e, "simple")
        b = self.selection(e, "gist")
        _, started = self.action(e)
        self.set_created(a, started - 2)
        self.set_created(b, started - 1)
        self.assertEqual(wm.transitions(self.r.store), [])

    def test_mismatched_packet_generation_cannot_relabel_action(self):
        e = self.event()
        first = self.selection(e, "simple")
        _, started = self.action(e)
        self.set_created(first, started - 2)
        mismatched = self.selection(e, "detail")
        self.set_created(mismatched, started - 1)
        # A corrupted packet-row generation is not an eligible C5 selection
        # for the event's actual brain generation.
        with self.r.store.tx() as c:
            c.execute("UPDATE packets SET generation_id=? WHERE id=?",
                      ("gen_foreign_generation", mismatched["packet_id"]))
        got = wm.transitions(self.r.store)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["a"], "simple")


if __name__ == "__main__":
    unittest.main()
