"""One outward answer per user event; B1/B2 are internal and history is not replayed as new output.

These tests use mocked native inference. They do not claim phone or model-quality parity.
"""
import io
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from v13 import ui
from v13.operator import Operator
from v13.runtime import Runtime


class PlainConsoleHistory(unittest.TestCase):
    def test_history_offsets_exclude_old_assistant_text(self):
        messages=[
            {"id":1,"role":"assistant","text":"old"},
            {"id":2,"role":"user","text":"hi"},
            {"id":3,"role":"assistant","text":""},
        ]
        self.assertEqual(ui._history_offsets(messages),{1:3,3:0})

    def test_plain_console_does_not_replay_old_assistant_as_new_turn(self):
        class Store:
            messages=[{"id":1,"role":"assistant","text":"historical greeting"}]
            def history(self,session,limit):
                return self.messages[-limit:]
        class FakeRuntime:
            store=Store()
            session="test"
            stop=threading.Event()
        runtime=FakeRuntime()
        stdout=io.StringIO()
        def receive(_prompt):
            time.sleep(.14)  # let render observe the old row
            runtime.store.messages.append({"id":2,"role":"assistant","text":"new answer"})
            time.sleep(.16)  # let render emit only the new row
            raise EOFError
        with patch("v13.ui.read_block",side_effect=receive),patch("v13.ui.typing",return_value=False),patch("sys.stdout",stdout):
            ui.plain(runtime)
        displayed=stdout.getvalue()
        self.assertNotIn("historical greeting",displayed)
        self.assertIn("assistant> new answer",displayed)
        self.assertEqual(displayed.count("assistant> "),1)


class UnifiedRuntime(unittest.TestCase):
    def test_each_body_route_has_only_c3_external_voice(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        for route in ("simple","detail","gist","both"):
            with self.subTest(route=route),tempfile.TemporaryDirectory() as temp:
                runtime=Runtime(Path(temp))
                try:
                    runtime.cfg["observer_mode"]="off"
                    runtime._route=Mock(return_value=(route,{"source":"TEST"}))
                    runtime.learner.output_delta=Mock(return_value=None)
                    roles=[]
                    def get(role):
                        roles.append(role)
                        return SimpleNamespace(role=role,last_metrics={"test_seam":True},
                                               generate=lambda *a,**k:iter(["one shared answer"]))
                    runtime.pool.get=Mock(side_effect=get)
                    eid=Operator(runtime).run("A question about the plan")
                    stop_at=time.monotonic()+8
                    while not runtime.idle() and time.monotonic()<stop_at:time.sleep(.01)
                    self.assertTrue(runtime.idle())
                    rows=runtime.store.rows("SELECT * FROM messages WHERE event_id=? AND role='assistant'",(eid,))
                    self.assertEqual(len(rows),1)
                    self.assertEqual(rows[0]["status"],"FINAL")
                    self.assertEqual(rows[0]["text"],"one shared answer")
                    self.assertTrue(roles)
                    self.assertEqual(set(roles),{"C3_LANGUAGE"})
                finally:
                    runtime.close()


if __name__=="__main__":
    unittest.main()
