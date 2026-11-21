"""GoalStore wake publication must not leave durable orphan goals or events."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.agi.goals import GoalStore
from v13.runtime import Runtime
from v13.scheduler import EventScheduler


class Clock:
    def __init__(self, value=1000.0):
        self.value = value

    def __call__(self):
        return self.value


class GoalWakeAtomicityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.runtime = Runtime(self.home)
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.runtime.sleep.cycle.set_policy("tick_seconds", "300")
        self.clock = Clock()
        self.scheduler = EventScheduler(
            self.runtime.store,
            self.runtime.cfg,
            self.clock,
            key="G13_GOAL_WAKE_ATOMICITY_TEST",
        )
        self.goals = GoalStore(
            self.runtime.store,
            scheduler=self.scheduler,
            clock=self.clock,
        )

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def _reopen_runtime(self):
        self.runtime.close()
        self.runtime = Runtime(self.home)
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.runtime.sleep.cycle.set_policy("tick_seconds", "300")
        self.scheduler = EventScheduler(
            self.runtime.store,
            self.runtime.cfg,
            self.clock,
            key="G13_GOAL_WAKE_ATOMICITY_TEST",
        )
        self.goals = GoalStore(
            self.runtime.store,
            scheduler=self.scheduler,
            clock=self.clock,
        )

    def test_invalid_wake_at_is_rejected_before_goal_or_queue_mutation(self):
        before_goal = self.goals.box.load()[0]
        before_queue = self.scheduler.report()
        invalid = (
            "not-a-time",
            "1060.0",
            True,
            float("nan"),
            float("inf"),
            -float("inf"),
            2 ** 1024,
        )
        for value in invalid:
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    self.goals.add("invalid wake", wake_at=value)
                self.assertEqual(self.goals.box.load()[0], before_goal)
                self.assertEqual(self.scheduler.report(), before_queue)

    def test_direct_schedule_validates_before_touching_goal_or_queue(self):
        goal_id = self.goals.add("without wake")
        before_goal = self.goals.box.load()[0]
        before_queue = self.scheduler.report()
        with self.assertRaises(ValueError):
            self.goals.schedule(goal_id, "not-a-time")
        self.assertEqual(self.goals.box.load()[0], before_goal)
        self.assertEqual(self.scheduler.report(), before_queue)

    def test_valid_wake_persists_matching_goal_and_scheduler_receipts(self):
        goal_id = self.goals.add("valid wake", wake_at=1060)
        goal = self.goals.get(goal_id)
        self.assertEqual(goal["wake_at"], 1060.0)
        event_id = goal["wake_event"]
        self.assertIsNotNone(event_id)
        pending = self.scheduler.pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], goal["wake_event"])
        self.assertEqual(pending[0]["kind"], "GOAL_WAKE")
        self.assertEqual(pending[0]["due"], 1060.0)
        self.assertEqual(pending[0]["payload"], {"goal_id": goal_id})
        self.assertEqual(pending[0]["dedup"], "goal:" + goal_id)

        # Both the goal row and the matching wake event must survive a process restart.
        self._reopen_runtime()
        restored = self.goals.get(goal_id)
        self.assertEqual(restored["wake_event"], event_id)
        self.assertEqual(restored["wake_at"], 1060.0)
        restored_pending = self.scheduler.pending()
        self.assertEqual([event["id"] for event in restored_pending], [event_id])

    def test_scheduler_refusal_rolls_back_goal_and_sequence(self):
        before_goal = self.goals.box.load()[0]
        before_queue = self.scheduler.report()
        with patch.object(self.scheduler, "post", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "could not be scheduled"):
                self.goals.add("queue full", wake_at=1060)
        self.assertEqual(self.goals.box.load()[0], before_goal)
        self.assertEqual(self.scheduler.report(), before_queue)

    def test_scheduler_exception_before_commit_rolls_back_goal(self):
        before_goal = self.goals.box.load()[0]
        before_queue = self.scheduler.report()
        with patch.object(self.scheduler, "post", side_effect=OSError("post rejected")):
            with self.assertRaisesRegex(OSError, "post rejected"):
                self.goals.add("post error", wake_at=1060)
        self.assertEqual(self.goals.box.load()[0], before_goal)
        self.assertEqual(self.scheduler.report(), before_queue)

    def test_post_committed_then_raised_is_compensated_without_orphan_wake(self):
        original_post = self.scheduler.post

        def post_then_raise(*args, **kwargs):
            self.assertIsNotNone(original_post(*args, **kwargs))
            raise OSError("simulated post telemetry failure")

        before_goal = self.goals.box.load()[0]
        with patch.object(self.scheduler, "post", side_effect=post_then_raise):
            with self.assertRaisesRegex(OSError, "telemetry failure"):
                self.goals.add("post committed then failed", wake_at=1060)
        self.assertEqual(self.goals.box.load()[0], before_goal)
        self.assertEqual(self.scheduler.pending(), [])
        history = self.scheduler.report()["history"]
        self.assertTrue(history)
        self.assertEqual(history[-1]["status"], "CANCELLED")

    def test_goal_backlink_failure_cancels_pending_event_and_rolls_back_goal(self):
        original_mutate = self.goals.box.mutate
        calls = 0

        def fail_second_mutation(function):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated goal backlink write failure")
            return original_mutate(function)

        before_goal = self.goals.box.load()[0]
        with patch.object(self.goals.box, "mutate", side_effect=fail_second_mutation):
            with self.assertRaisesRegex(OSError, "backlink write failure"):
                self.goals.add("backlink failure", wake_at=1060)
        self.assertEqual(calls, 3)  # create, failed backlink, compensating goal rollback
        self.assertEqual(self.goals.box.load()[0], before_goal)
        self.assertEqual(self.scheduler.pending(), [])
        history = self.scheduler.report()["history"]
        self.assertTrue(history)
        self.assertEqual(history[-1]["status"], "CANCELLED")

        # The compensated state is durable, not merely an in-memory cleanup.
        self._reopen_runtime()
        restored_state = self.goals.box.load()[0]
        self.assertEqual(restored_state["goals"], {})
        self.assertEqual(restored_state["seq"], 0)
        self.assertEqual(self.scheduler.pending(), [])
        restored_history = self.scheduler.report()["history"]
        self.assertTrue(restored_history)
        self.assertEqual(restored_history[-1]["status"], "CANCELLED")


if __name__ == "__main__":
    unittest.main()
