"""Run96: newly recorded correction must be visible to idle wake scheduler.

Real Runtime/Memory/SQLite state with model-free mocked scheduler dispatch.
No native models, no Age bypass, no background job actually executed.
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from v13.runtime import Runtime
from v13.sleep import default_policy


class SleepWakeIndexRun96(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.r.sleep.cycle.set_policy("tick_seconds", "300")
        event = self.r.store.event(self.r.session, "What was the Aurora budget?")
        self.r.memory.feedback(event["event_id"], "fact", "120 EUR")
        self.replay_id = self.r.store.one(
            "SELECT id FROM replay WHERE event_id=?", (event["event_id"],)
        )["id"]
        self.assertNotIn(self.replay_id, self.r.sleep.cycle.queue.load()[0]["items"])

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def tick(self, enabled=True, save_error=False, idle=True):
        policy = default_policy()
        policy["enabled"] = enabled
        with mock.patch.object(self.r.sleep.cycle, "policy", return_value=policy), \
             mock.patch.object(self.r, "idle", return_value=idle), \
             mock.patch.object(self.r.sleep, "resource_state", return_value="NORMAL"), \
             mock.patch.object(self.r.sleep, "idle_seconds", return_value=30.), \
             mock.patch.object(self.r.sleep.scheduler, "post", return_value="posted") as post, \
             mock.patch.object(self.r.sleep.scheduler, "next", return_value=None), \
             mock.patch.object(self.r.sleep.cycle.queue, "save",
                               side_effect=ValueError("CAS conflict") if save_error else None,
                               wraps=None if save_error else self.r.sleep.cycle.queue.save):
            self.r.sleep.tick(force=True)
            return [c.args[0] for c in post.call_args_list]

    def test_new_correction_posts_wake_without_waiting_for_full_sleep(self):
        posts = self.tick()
        self.assertIn("REPLAY_DUE", posts)
        self.assertIn(self.replay_id, self.r.sleep.cycle.queue.load()[0]["items"])

    def test_real_scheduler_pending_survives_runtime_restart(self):
        policy = default_policy()
        with mock.patch.object(self.r.sleep.cycle, "policy", return_value=policy), \
             mock.patch.object(self.r, "idle", return_value=True), \
             mock.patch.object(self.r.sleep, "resource_state", return_value="NORMAL"), \
             mock.patch.object(self.r.sleep, "idle_seconds", return_value=30.), \
             mock.patch.object(self.r.sleep.scheduler, "next", return_value=None):
            self.r.sleep.tick(force=True)
        pending = self.r.sleep.scheduler.pending()
        self.assertTrue(any(x["kind"] == "REPLAY_DUE" and
                            x["status"] == "PENDING" for x in pending))
        self.assertIn(self.replay_id, self.r.sleep.cycle.queue.load()[0]["items"])
        self.r.close()
        self.r = Runtime(Path(self.temp.name))
        self.assertIn(self.replay_id, self.r.sleep.cycle.queue.load()[0]["items"])
        self.assertTrue(any(x["kind"] == "REPLAY_DUE" and
                            x["status"] == "PENDING"
                            for x in self.r.sleep.scheduler.pending()))
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")

    def test_disabled_sleep_does_not_index_or_post_background_wake(self):
        posts = self.tick(enabled=False)
        self.assertNotIn("REPLAY_DUE", posts)
        self.assertNotIn(self.replay_id, self.r.sleep.cycle.queue.load()[0]["items"])

    def test_busy_foreground_does_not_start_wake_or_index(self):
        posts = self.tick(idle=False)
        self.assertNotIn("REPLAY_DUE", posts)
        self.assertNotIn(self.replay_id, self.r.sleep.cycle.queue.load()[0]["items"])

    def test_cas_conflict_does_not_schedule_unpersisted_replay(self):
        posts = self.tick(save_error=True)
        self.assertNotIn("REPLAY_DUE", posts)
        self.assertNotIn(self.replay_id, self.r.sleep.cycle.queue.load()[0]["items"])


if __name__ == "__main__":
    unittest.main()
