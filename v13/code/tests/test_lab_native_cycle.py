"""Offline G13 lab cycle tests: real-role invocation, private state, preemption."""
import copy
import queue
import threading
import time
import unittest
from types import SimpleNamespace
from v13 import lab_native_cycle as lab


class Store:
    def __init__(self):
        self.mutex = threading.RLock()
        self.obj = None
        self.version = 0
        self.logs = []
        self.events = []
        self.user_messages = []
    def state(self, key, default=None):
        assert key == lab.KEY
        return copy.deepcopy(self.obj), self.version
    def set_state(self, key, obj, expected=None):
        assert key == lab.KEY and expected == self.version
        self.version += 1
        self.obj = copy.deepcopy(obj)
    def log(self, category, event, payload):
        self.logs.append((category, event, payload))


class Pool:
    def __init__(self):
        self.called = []
        self.runners = {}
    def resident_roles(self):
        return [role for role in self.runners]
    def get(self, role):
        self.called.append(role)
        if role not in self.runners:
            self.runners[role] = Runner(role)
        return self.runners[role]


class Runner:
    def __init__(self, role):
        self.role = role
        self.calls = []
        self.last_metrics = {"generated_tokens": 3}
    def generate(self, messages, cancel, deadline, max_tokens):
        self.calls.append((messages, max_tokens))
        yield "testing "
        yield self.role


class Scheduler:
    def __init__(self):
        self.events = []
    def post(self, kind, **kwargs):
        self.events.append((kind, kwargs))
        return "event-id"


class Runtime:
    def __init__(self):
        self.store = Store()
        self.cancel_event = threading.Event()
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.paused = False
        self.pool = Pool()
        self.notices = []
        self.cfg = {"observer_seconds": 25}
        self.current = None
        self.needle = SimpleNamespace(load=self.needle_load)
        self.needle_loads = 0
        self.sleep = SimpleNamespace(r=self, scheduler=Scheduler(),
                  clock=lambda: time.time(), idle_seconds=lambda: 90.,
                  resource_state=lambda: "NORMAL", lab_active=False,
                  tick=lambda force=False: None)
    def idle(self):
        return self.current is None
    def notice(self, message):
        self.notices.append(message)
    def needle_load(self, cancel, deadline):
        self.needle_loads += 1


class LabCycleTests(unittest.TestCase):
    def setUp(self):
        self.r = Runtime()
    def test_active_default_is_only_synthetic_local(self):
        x = lab.status(self.r)
        self.assertTrue(x["enabled"])
        self.assertEqual(x["next_role"], "B1_DETAIL")
        self.assertEqual(x["learning_authority"], "NONE")
        self.assertEqual(x["tool_authority"], "NONE")
        self.assertEqual(x["training_data_source"], "SYNTHETIC_UNTRUSTED")
    def test_g13_schedules_only_at_idle_when_resources_allow(self):
        self.assertTrue(lab.maybe_schedule(self.r.sleep, "NORMAL"))
        self.assertEqual(self.r.sleep.scheduler.events[0][1]["action"], "lab_check")
        self.assertIsNone(lab.maybe_schedule(self.r.sleep, "PRESSURE"))
        self.r.current = "turn"
        self.assertIsNone(lab.maybe_schedule(self.r.sleep, "NORMAL"))
        self.r.current = None
        self.r.sleep.idle_seconds = lambda: 1.
        self.assertIsNone(lab.maybe_schedule(self.r.sleep, "NORMAL"))
    def test_b1_b2_c3_peer_speech_and_c2_warm_without_fake_user(self):
        results = [lab.run(self.r) for _ in lab.ROLES]
        self.assertEqual([x["status"] for x in results],
                         ["FINAL", "FINAL", "FINAL", "LOADED"])
        self.assertEqual(self.r.pool.called,
                         ["B1_DETAIL", "B2_GIST", "C3_LANGUAGE"])
        self.assertEqual(self.r.needle_loads, 1)
        self.assertIn("testing B1_DETAIL",
                      self.r.pool.runners["B2_GIST"].calls[0][0][1]["content"])
        x = lab.status(self.r)
        self.assertEqual(x["completed"], 3)
        self.assertEqual(x["next_role"], "B1_DETAIL")
        self.assertEqual(len(x["last_thoughts"]), 3)
        self.assertEqual(self.r.store.user_messages, [])
        self.assertEqual(len(self.r.notices), 3)
        self.assertTrue(all("vorläufige Hypothese" in x for x in self.r.notices))
        self.assertFalse(any("text" in entry[2] or "prompt" in entry[2]
                             for entry in self.r.store.logs))
    def test_quota_and_cooldown_avoid_unbounded_idle_compute(self):
        lab.run(self.r)
        self.assertIsNone(lab.maybe_schedule(self.r.sleep, "NORMAL"))
        with self.r.store.mutex:
            obj, version = lab.load(self.r.store)
            obj["last_started"] = 0.
            obj["recent_started"] = [time.time()] * lab.MAX_RUNS_HOUR
            self.r.store.set_state(lab.KEY, obj, expected=version)
        self.assertIsNone(lab.maybe_schedule(self.r.sleep, "NORMAL"))
    def test_user_cancel_stops_model_and_never_promotes_partial_text(self):
        def cancel_on_decode(messages, cancel, deadline, max_tokens):
            self.r.cancel_event.set()
            yield "partial word"
        runner = Runner("B1_DETAIL")
        runner.generate = cancel_on_decode
        self.r.pool.get = lambda role: runner
        out = lab.run(self.r)
        self.assertEqual(out["status"], "CANCELLED")
        self.assertEqual(lab.status(self.r)["completed"], 0)
        self.assertEqual(self.r.notices, [])
    def test_off_while_busy_revokes_publication(self):
        def disable_on_decode(messages, cancel, deadline, max_tokens):
            lab.configure(self.r, enabled=False)
            yield "must not publish"
        runner = Runner("B1_DETAIL")
        runner.generate = disable_on_decode
        self.r.pool.get = lambda role: runner
        out = lab.run(self.r)
        self.assertEqual(out["status"], "DISABLED")
        self.assertFalse(lab.status(self.r)["enabled"])
        self.assertEqual(lab.status(self.r)["last_thoughts"], [])
        self.assertTrue(self.r.cancel_event.is_set())
        self.assertEqual(self.r.notices, [])
    def test_status_off_now_every_reset_are_bounded(self):
        self.assertFalse(lab.operator_command(self.r, ["off"])["enabled"])
        self.assertTrue(lab.operator_command(self.r, ["on"])["enabled"])
        self.assertEqual(lab.operator_command(self.r, ["every", "120"])["interval_s"], 120.)
        self.assertTrue(lab.operator_command(self.r, ["now"])["queued"])
        self.assertEqual(self.r.sleep.scheduler.events[-1][1]["origin"], "USER")
        self.assertEqual(lab.operator_command(self.r, ["reset"])["last_thoughts"], [])
        with self.assertRaises(ValueError):
            lab.operator_command(self.r, ["every", "0"])
        with self.assertRaises(ValueError):
            lab.operator_command(self.r, ["exec", "shell"])
    def test_corrupt_state_fail_closed(self):
        self.r.store.obj = {"schema": lab.SCHEMA, "enabled": "yes"}
        with self.assertRaises(ValueError):
            lab.status(self.r)


if __name__ == "__main__":
    unittest.main()
