"""Local graceful update handoff: stop, explicit acknowledgement, durable resume.

No Android/system dependencies; tests use simulated UI console and fake
runtime visibility. Never signal arbitrary OS processes.
"""
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest import mock

from v13 import lifecycle as life


class FakeConsole:
    def __init__(self, *, exit_on_shutdown=True):
        self.running = True
        self.exit_on_shutdown = exit_on_shutdown
        self.shutdown_calls = 0
        self.cancel_calls = 0
        self.starts = 0

    def state(self):
        return {"running": self.running}

    def shutdown(self):
        self.shutdown_calls += 1
        if self.exit_on_shutdown:
            self.running = False
        return {"status": "SENT"}

    def cancel(self):
        self.cancel_calls += 1
        self.running = False

    def start(self):
        self.starts += 1
        self.running = True
        return {"status": "STARTED"}


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        private = Path(directory.name)
        private.chmod(0o700)
        for name, val in [
            ("PRIVATE", private),
            ("STOP_REQUEST", private / "stop.json"),
            ("STOP_ACK", private / "ack.json"),
            ("RESUME", private / "resume.json"),
        ]:
            change = mock.patch.object(life, name, val)
            change.start()
            self.addCleanup(change.stop)

    def test_stop_is_graceful_and_resume_exactly_once(self):
        console = FakeConsole()
        result = []
        def watcher():
            expiry = time.monotonic() + 4
            while time.monotonic() < expiry and not life.STOP_REQUEST.is_file():
                time.sleep(.01)
            life.service_stop(console, shutdown_wait=.1, interrupt_wait=.1)
        worker = threading.Thread(target=watcher)
        worker.start()
        stopped = life.request_stop(timeout=3, runtime_active=lambda:console.running)
        worker.join(timeout=3)
        self.assertFalse(worker.is_alive())
        self.assertTrue(stopped)
        self.assertEqual(console.shutdown_calls,1)
        self.assertFalse(console.running)
        life.request_resume(reason="UPDATED")
        self.assertTrue(life.service_resume(console))
        self.assertTrue(console.running)
        self.assertEqual(console.starts,1)
        self.assertFalse(life.RESUME.exists())
        self.assertFalse(life.service_resume(console))
        self.assertEqual(console.starts,1)

    def test_hung_chat_gets_bounded_interrupt_only(self):
        console=FakeConsole(exit_on_shutdown=False)
        result=[]
        def watcher():
            deadline=time.monotonic()+2
            while time.monotonic()<deadline and not life.STOP_REQUEST.is_file():
                time.sleep(.01)
            life.service_stop(console,shutdown_wait=.04,interrupt_wait=.04)
        worker=threading.Thread(target=watcher)
        worker.start()
        self.assertTrue(life.request_stop(timeout=2,runtime_active=lambda:console.running))
        worker.join(timeout=2)
        self.assertEqual(console.shutdown_calls,1)
        self.assertEqual(console.cancel_calls,1)
        self.assertFalse(console.running)

    def test_no_chat_no_request_and_no_auto_start(self):
        with mock.patch.object(life,"_write") as write:
            self.assertFalse(life.request_stop(runtime_active=lambda:False))
        write.assert_not_called()

    def test_expired_stop_request_is_refused(self):
        console=FakeConsole()
        life._write(life.STOP_REQUEST, {
            "schema":"v13.lifecycle.stop/1", "nonce":"a"*32,
            "expires":int(time.time())-60})
        self.assertFalse(life.service_stop(console))
        self.assertTrue(console.running)

    def test_unsafe_symlink_is_refused(self):
        target=life.PRIVATE/"other"
        target.write_text("secret")
        life.STOP_REQUEST.symlink_to(target)
        with self.assertRaises(life.LifecycleError):
            life._write(life.STOP_REQUEST,{"test":1})

    def test_restart_marker_persists_if_ui_start_fails(self):
        console=FakeConsole()
        console.running=False
        life.request_resume()
        def fail():
            raise RuntimeError("launcher missing")
        console.start=fail
        self.assertFalse(life.service_resume(console))
        self.assertTrue(life.RESUME.is_file())
        self.assertEqual(oct(life.RESUME.stat().st_mode & 0o777),"0o600")

    def test_busy_other_live_process_fails_closed(self):
        console=FakeConsole()
        def watcher():
            deadline=time.monotonic()+2
            while time.monotonic()<deadline and not life.STOP_REQUEST.is_file():
                time.sleep(.01)
            life.service_stop(console,shutdown_wait=.1,interrupt_wait=.1)
        worker=threading.Thread(target=watcher)
        worker.start()
        with self.assertRaises(life.LifecycleError):
            life.request_stop(timeout=2,runtime_active=lambda:True)
        worker.join(timeout=2)


if __name__=="__main__":
    unittest.main()
