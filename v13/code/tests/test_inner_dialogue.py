"""Offline tests for V13's optional, non-authoritative idle B1/B2/C3 conversation."""
import queue
import threading
import unittest
from types import SimpleNamespace

from v13 import inner_dialogue as d


class Store:
    def __init__(self):
        self.mutex = threading.RLock()
        self.saved = None
        self.version = 0
        self.logs = []
        self.source_reads = 0
        self.user_turns_created = 0

    def state(self, key, default=None):
        assert key == d.KEY
        return self.saved, self.version

    def set_state(self, key, payload, expected=None):
        assert key == d.KEY
        assert expected == self.version
        self.saved = __import__("copy").deepcopy(payload)
        self.version += 1
        return self.version

    def queue_stats(self):
        return {"count": 0}

    def one(self, sql, args=()):
        self.source_reads += 1
        return {"excerpt": "An earlier human question."}

    def log(self, kind, event, data):
        self.logs.append((kind, event, data))


class Runner:
    def __init__(self, model):
        self.role = model
        self.calls = []

    def generate(self, messages, cancel, deadline, max_tokens=64):
        self.calls.append((messages, max_tokens))
        yield "Working "
        yield self.role


class Pool:
    def __init__(self):
        self.roles = []
        self.runners = {}

    def get(self, role):
        self.roles.append(role)
        self.runners.setdefault(role, Runner(role))
        return self.runners[role]


class FakeRuntime:
    def __init__(self):
        self.store = Store()
        self.stop = threading.Event()
        self.cancel_event = threading.Event()
        self.wake = threading.Event()
        self.paused = False
        self.current = None
        self.jobs = queue.Queue()
        self.session = "private-session"
        self.cfg = {"observer_seconds": 35}
        self.pool = Pool()
        self.sleep = SimpleNamespace(idle_seconds=lambda: 60,
                                     resource_state=lambda: "NORMAL")
        self.notices = []

    def enqueue(self, kind):
        assert kind == "inner"
        self.jobs.put((kind, None, 0, 0))

    def notice(self, text):
        self.notices.append(text)


class InnerDialogueLabTests(unittest.TestCase):
    def setUp(self):
        self.r = FakeRuntime()
        self.lab = d.InnerDialogue(self.r, clock=lambda: 10000.,
                                   monotonic=lambda: 100.)

    def test_disabled_by_default_and_no_synthetic_user_turn(self):
        self.assertFalse(self.lab.tick())
        self.assertFalse(d.report(self.r)["enabled"])
        self.assertEqual(self.r.store.user_turns_created, 0)
        self.assertEqual(self.r.pool.roles, [])

    def test_real_roles_alternate_and_peer_utterance_is_visible(self):
        d.enable(self.r, True)
        for role in d.ROLES:
            result = self.lab.run()
            self.assertEqual(result["status"], "FINAL")
            self.assertEqual(result["role"], role)
        report = d.report(self.r)
        self.assertEqual(self.r.pool.roles, list(d.ROLES))
        self.assertEqual(report["next_role"], d.ROLES[0])
        self.assertEqual(report["completed"], 3)
        self.assertEqual([h["role"] for h in report["history"]], list(d.ROLES))
        self.assertIn("Working B1_DETAIL", self.r.pool.runners["B2_GIST"].calls[0][0][1]["content"])
        self.assertEqual(self.r.store.user_turns_created, 0)
        self.assertEqual(len(self.r.notices), 3)
        self.assertTrue(all("Hypothese" in x for x in self.r.notices))
        self.assertEqual(report["learning_authority"], "NONE")

    def test_ticking_never_competes_with_foreground_or_resources(self):
        d.enable(self.r, True)
        self.assertTrue(self.lab.tick())
        self.assertEqual(self.r.jobs.qsize(), 1)
        self.r.jobs.get_nowait()
        self.lab.last_tick = -1e30
        self.r.current = "turn"
        self.assertFalse(self.lab.tick())
        self.r.current = None
        self.r.sleep.resource_state = lambda: "PRESSURE"
        self.lab.last_tick = -1e30
        self.assertFalse(self.lab.tick())

    def test_hourly_quota_blocks_more_autonomous_steps(self):
        d.enable(self.r, True)
        obj, v = d.state(self.r.store)
        obj["attempts"] = [9999.] * d.MAX_ATTEMPTS_HOUR
        self.r.store.set_state(d.KEY, obj, expected=v)
        self.assertFalse(self.lab.tick())

    def test_disable_during_generation_discards_thought(self):
        d.enable(self.r, True)
        def stop_during_decode(messages, cancel, deadline, max_tokens):
            d.enable(self.r, False)
            yield "This must not be displayed"
        original = self.r.pool.get
        runner = Runner("B1_DETAIL")
        runner.generate = stop_during_decode
        self.r.pool.get = lambda role: runner
        result = self.lab.run()
        self.assertEqual(result["status"], "DISABLED")
        self.assertEqual(d.report(self.r)["history"], [])
        self.assertEqual(self.r.notices, [])
        self.assertFalse(d.report(self.r)["enabled"])

    def test_operator_accepts_only_bounded_controls(self):
        from v13.inner_dialogue import operator_command
        self.assertTrue(operator_command(self.r, ["on"])["enabled"])
        self.assertFalse(operator_command(self.r, ["off"])["enabled"])
        with self.assertRaises(ValueError):
            operator_command(self.r, ["auto-execute-tools"])


if __name__ == "__main__":
    unittest.main()
