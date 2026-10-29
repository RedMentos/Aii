"""Preregistered C5 PREDICTION vs COMMIT World-Model evidence."""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.contracts import packet
from v13 import world_model as wm


class WorldModelStageBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def make_event(self):
        return self.r.store.event(self.r.session, "Own observed digital action")

    def select(self, event, route, stage=None):
        fields = {"stage": stage} if stage is not None else {}
        p = packet("ActionSelection", "C5_ACTION_GATE",
                   event["event_id"], event["brain_generation_id"],
                   [event["source_ref"]],
                   selected={"action_id": "C3_LANGUAGE", "action_type": "TEXT_REPORT",
                             "score": 0., "permission_class": "local_text_only",
                             "focal_support": 0.},
                   candidates=[], suppressed=[], permission_class="local_text_only",
                   route_hint=route, **fields)
        self.r.store.add_packet("ActionSelection", p)
        return p

    def action(self, event):
        aid = self.r.store.start_action(
            event["event_id"], event["brain_generation_id"],
            forecast={"input_chars": 100, "resource_state": "NORMAL"})
        self.r.store.finish_action(aid, "FINAL",
                                   {"action_duration_s": 1., "characters": 42})
        return self.r.store.one("SELECT created FROM actions WHERE id=?", (aid,))["created"]

    def before(self, packets, created):
        with self.r.store.tx() as c:
            for index, p in enumerate(packets):
                c.execute("UPDATE packets SET created=? WHERE id=?",
                          (created - len(packets) + index, p["packet_id"]))

    def test_prediction_only_cannot_label_action(self):
        e = self.make_event()
        p = self.select(e, "detail", "PREDICTION")
        started = self.action(e)
        self.before([p], started)
        self.assertEqual(wm.transitions(self.r.store), [])

    def test_prediction_and_commit_use_only_committed_route(self):
        e = self.make_event()
        prediction = self.select(e, "detail", "PREDICTION")
        commit = self.select(e, "simple", "COMMIT")
        started = self.action(e)
        self.before([prediction, commit], started)
        got = wm.transitions(self.r.store)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["a"], "simple")

    def test_two_commits_remain_ambiguous(self):
        e = self.make_event()
        a = self.select(e, "detail", "COMMIT")
        b = self.select(e, "simple", "COMMIT")
        started = self.action(e)
        self.before([a, b], started)
        self.assertEqual(wm.transitions(self.r.store), [])

    def test_legacy_one_packet_stays_supported(self):
        e = self.make_event()
        p = self.select(e, "gist")
        started = self.action(e)
        self.before([p], started)
        self.assertEqual(wm.transitions(self.r.store)[0]["a"], "gist")

    def test_unknown_stage_is_not_trusted(self):
        e = self.make_event()
        p = self.select(e, "both", "PROVISIONAL_UNRECOGNIZED")
        started = self.action(e)
        self.before([p], started)
        self.assertEqual(wm.transitions(self.r.store), [])

    def test_bounded_packet_scan_never_silently_selects_one(self):
        e = self.make_event()
        packets = [self.select(e, "detail", "PREDICTION") for _ in range(17)]
        packets.append(self.select(e, "simple", "COMMIT"))
        started = self.action(e)
        self.before(packets, started)
        self.assertEqual(wm.transitions(self.r.store), [])


if __name__ == "__main__":
    unittest.main()
