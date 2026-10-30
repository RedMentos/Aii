"""Run17 test-first: expired F9 replay items must never enter Sleep A/wake selection."""
import tempfile
import time
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.sleep import SleepCycle, DAY


class Clock:
    def __init__(self, t):
        self.t = t
    def __call__(self):
        return self.t


class SleepReplayTTL(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.r.sleep.cycle.set_policy("ttl_days", "1")
        self.clock = Clock(time.time() + 5)
        self.cycle = self._cycle()

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _cycle(self):
        return SleepCycle(self.r.store, self.r.cfg, self.r.memory,
                          self.r.consolidation, None, self.home, clock=self.clock)

    def _correction(self, name):
        event = self.r.store.event(self.r.session, name)["event_id"]
        self.r.memory.feedback(event, "fact", "Verified " + name, key=name)
        return event

    def _schedule(self):
        st, version = self.cycle.queue.load()
        self.cycle.queue.sync(st, self.cycle.policy())
        return st, version

    def test_expiry_boundary_applies_to_due_and_bucketed_sample(self):
        self._correction("Project TTL one")
        st, _ = self._schedule()
        self.assertEqual(len(st["items"]), 1)
        item = next(iter(st["items"].values()))
        before = item["expires"] - 0.01
        self.assertEqual(len(self.cycle.queue.due(st, before)), 1)
        self.assertEqual(len(self.cycle.queue.sample(st, 1, self.cycle.policy()["mix"], before)), 1)
        for when in (item["expires"], item["expires"] + 60):
            with self.subTest(when=when):
                self.assertEqual(self.cycle.queue.due(st, when), [])
                self.assertEqual(self.cycle.queue.sample(st, 1, self.cycle.policy()["mix"], when), [])

    def test_wake_and_a_only_select_unexpired_and_preserve_original_rows(self):
        self._correction("Project TTL expired")
        self._correction("Project TTL valid")
        st, version = self._schedule()
        self.assertEqual(len(st["items"]), 2)
        entries = list(st["items"].items())
        expired_id, expired = entries[0]
        valid_id, valid = entries[1]
        expired["expires"] = self.clock.t - 1
        valid["expires"] = self.clock.t + DAY
        for _, it in entries:
            it["priority"] = 1.0
            it["next_due"] = self.clock.t - 1
        self.cycle.queue.save(st, version)
        before_replay = self.r.store.rows("SELECT id,event_id,kind FROM replay ORDER BY id")
        before_memory = self.r.store.rows("SELECT id,source_id,value FROM memories ORDER BY id")

        wake = self.cycle.run("wake", origin="USER")["phases"][0]
        self.assertEqual(wake["selected"], 1)
        st, version = self.cycle.queue.load()
        st["items"][valid_id]["next_due"] = self.clock.t - 1
        self.cycle.queue.save(st, version)
        direct = self.cycle.run("a", origin="USER")["phases"][0]
        self.assertEqual(direct["selected"], 1)
        count = self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ReplayItem' "
            "AND json_extract(payload,'$.stage')='SLEEP_A' "
            "AND json_extract(payload,'$.replay_id')=?", (expired_id,)
        )["n"]
        self.assertEqual(count, 0)
        self.assertEqual(before_replay, self.r.store.rows("SELECT id,event_id,kind FROM replay ORDER BY id"))
        self.assertEqual(before_memory, self.r.store.rows("SELECT id,source_id,value FROM memories ORDER BY id"))

    def test_restart_keeps_expired_item_excluded_until_sleep_c_retires(self):
        self._correction("Project TTL restart")
        st, version = self._schedule()
        item = next(iter(st["items"].values()))
        item["expires"] = self.clock.t - 1
        self.cycle.queue.save(st, version)
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.cycle = self._cycle()
        loaded, _ = self.cycle.queue.load()
        self.assertEqual(self.cycle.queue.due(loaded, self.clock.t), [])
        self.assertEqual(self.cycle.run("wake", origin="USER")["phases"][0]["selected"], 0)
        self.assertEqual(self.cycle.run("c", origin="USER")["phases"][0]["trace_decay"]["expired"], 1)
        final, _ = self.cycle.queue.load()
        self.assertEqual(next(iter(final["items"].values()))["retired"], "TTL")
        self.assertEqual(self.r.store.one("SELECT COUNT(*) AS n FROM replay")["n"], 1)


if __name__ == "__main__":
    unittest.main()
