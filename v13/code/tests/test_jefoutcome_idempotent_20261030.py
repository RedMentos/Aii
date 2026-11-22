"""JEF FINAL self-label retries are no-ops and preserve corrected outcomes."""
import tempfile
import unittest
from pathlib import Path

from v13 import fastpolicy as fp
from v13 import jefoutcome as jo
from v13.agi.live import _save
from v13.runtime import Runtime


class JEFOutcomeRetry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self, text="Synthetic skill request"):
        e = self.r.store.event(self.r.session, text)
        fp.head(self.r, "skill", e, "skill")
        _save(self.r.store, e["event_id"], skill="synthetic_skill")
        return e

    def finish(self, e, status="FINAL"):
        return jo.after_turn(self.r, e,
                             {"skill": {"name": "synthetic_skill"}},
                             status, {"coalition": []})

    def labels(self, eid):
        return [x for x in (self.r.store.state(jo.KEY)[0] or {}).get(
            "labels", []) if x["event_id"] == eid and x["component"] == "skill"]

    def sources(self):
        return self.r.store.one(
            "SELECT COUNT(*) AS n FROM sources WHERE kind=?",
            (jo.AUTHORITY,))["n"]

    def test_identical_final_retry_does_not_write_or_double_count(self):
        e = self.event()
        self.assertEqual(self.finish(e), {"skill": "skill"})
        before = self.r.store.state(jo.KEY)
        n = self.sources()
        self.assertEqual(self.finish(e), {"skill": "skill"})
        self.assertEqual(self.r.store.state(jo.KEY), before)
        self.assertEqual(self.sources(), n)
        self.assertEqual(len(self.labels(e["event_id"])), 1)
        self.assertEqual(jo.report(self.r)["heads"]["skill"]["labels"], 1)
        self.assertEqual(self.r.pool.pids(), [])

    def test_correction_survives_final_replay_and_sqlite_restart(self):
        e = self.event()
        self.finish(e)
        self.assertEqual(jo.on_route_correction(
            self.r.store, e["event_id"], "detail"), 1)
        self.assertEqual(self.labels(e["event_id"])[0]["value"], "none")
        before = self.r.store.state(jo.KEY)
        n = self.sources()
        self.assertEqual(self.finish(e), {"skill": "none"})
        self.assertEqual(self.r.store.state(jo.KEY), before)
        self.assertEqual(self.sources(), n)
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.assertEqual(self.finish(e), {"skill": "none"})
        self.assertEqual(self.r.store.state(jo.KEY), before)
        self.assertEqual(self.sources(), n)
        self.assertEqual(len(self.labels(e["event_id"])), 1)

    def test_distinct_events_not_deduped_and_failed_turn_not_labelled(self):
        a = self.event("same synthetic request")
        b = self.event("same synthetic request")
        self.assertEqual(self.finish(a), {"skill": "skill"})
        self.assertEqual(self.finish(b), {"skill": "skill"})
        self.assertEqual(len(self.labels(a["event_id"])), 1)
        self.assertEqual(len(self.labels(b["event_id"])), 1)
        self.assertEqual(self.sources(), 2)
        self.assertEqual(self.finish(a, status="ERROR"), {})
        self.assertEqual(jo.report(self.r)["heads"]["skill"]["labels"], 2)
        missing = self.r.store.event(self.r.session, "no decision")
        self.assertEqual(self.finish(missing), {})
        self.assertEqual(self.sources(), 2)


if __name__ == "__main__":
    unittest.main()
