"""V13 AI is a real independent local daemon, not the browser or Git updater."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from v13 import chat_service as ai


class FakeConsole:
    def __init__(self):
        self.running = False
        self.starts = 0
        self.stops = 0
        self.messages = []

    def state(self):
        return {"running": self.running, "exit_code": None,
                "last_session": "test.log", "pid":123 if self.running else None}

    def start(self):
        if self.running:
            return {"status":"ALREADY_RUNNING"}
        self.running = True
        self.starts += 1
        return {"status":"STARTED"}

    def send(self, text):
        self.messages.append(text)
        if text == ":shutdown":
            self.running = False
        return {"status":"SENT"}

    def cancel(self):
        self.running = False
        self.stops += 1
        return {"status":"CANCEL_REQUESTED"}

    def shutdown(self):
        self.running = False
        self.stops += 1
        return {"status":"SENT"}

    def output(self, limit=160000):
        return "assistant> Guten Tag."

    def transcript(self, *, all_sessions=True):
        return "du> Hallo\nassistant> Guten Tag."

    def saved_sessions(self):
        return ["test.log"]


class AIBackgroundTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        private=Path(temp.name)/"private"
        private.mkdir(mode=0o700)
        for field,path in [
            ("PRIVATE",private),("SOCKET",private/"v13-ai.sock"),
            ("LOCK",private/"v13-ai.lock"),
            ("DESIRED",private/"desired.json")]:
            p=mock.patch.object(ai,field,path)
            p.start(); self.addCleanup(p.stop)
        self.pipeline=mock.patch("v13.pipeline_agent.snapshot",
                                 return_value={"last_result":"UP_TO_DATE"})
        self.pipeline.start(); self.addCleanup(self.pipeline.stop)
        self.refresh=mock.patch("v13.pipeline_agent.refresh_requested",return_value=False)
        self.refresh.start();self.addCleanup(self.refresh.stop)
        self.stop=mock.patch.object(ai.lifecycle,"service_stop",return_value=False)
        self.stop.start();self.addCleanup(self.stop.stop)
        self.resume=mock.patch.object(ai.lifecycle,"service_resume",return_value=False)
        self.resume.start();self.addCleanup(self.resume.stop)

    def test_actual_ai_autostarts_without_browser_and_answers(self):
        ai._desired(True)
        console=FakeConsole()
        service=ai.ChatService(console)
        service.tick()
        self.assertEqual(service.command("state",{})["daemon"],"RUNNING")
        self.assertTrue(service.command("state",{})["autostart"])
        self.assertEqual(service.command("send",{"line":"Hallo V13"}),
                         {"status":"SENT"})
        self.assertEqual(console.messages,["Hallo V13"])
        self.assertIn("Guten Tag",service.command("output",{"limit":200}))
        self.assertIn("Hallo",service.command("transcript",{}))
        # New dashboard instances are only clients; they cannot kill this AI.
        service.tick()
        self.assertTrue(console.running)
        self.assertEqual(console.starts,1)

    def test_unexpected_model_exit_is_recovered_and_manual_shutdown_is_respected(self):
        ai._desired(True)
        console=FakeConsole()
        service=ai.ChatService(console)
        service.tick()
        console.running=False  # simulate model crash
        service.tick()
        self.assertEqual(service.status,"RETRY_WAIT")
        # Crash backoff must expire, not relaunch in a tight battery-draining loop.
        with mock.patch.object(ai.time,"monotonic",return_value=service.last_start+40):
            service.tick()
        self.assertTrue(console.running)
        self.assertEqual(console.starts,2)
        service.command("send",{"line":":shutdown"})
        service.tick()
        self.assertFalse(console.running)
        self.assertFalse(ai._read_desired())
        self.assertEqual(console.starts,2)
        service.command("start",{})
        self.assertTrue(console.running)
        self.assertTrue(ai._read_desired())

    def test_ai_pauses_during_update_and_resumes_after_pipeline(self):
        ai._desired(True)
        console=FakeConsole()
        service=ai.ChatService(console)
        service.tick()
        with mock.patch.object(ai.lifecycle,"service_stop",side_effect=lambda c,**kw:(
                setattr(c,"running",False) or True)), \
             mock.patch("v13.pipeline_agent.snapshot",return_value={"last_result":"CHECKING"}):
            service.tick()
        self.assertFalse(console.running)
        self.assertEqual(service.status,"PAUSED_FOR_UPDATE")
        with mock.patch.object(ai.lifecycle,"service_resume",side_effect=lambda c:(
                setattr(c,"running",True) or True)):
            service.tick()
        self.assertTrue(console.running)
        self.assertEqual(service.status,"RUNNING")

    def test_new_source_reload_marker_is_honored_before_ai_resumes(self):
        ai._desired(True)
        service=ai.ChatService(FakeConsole())
        with mock.patch("v13.pipeline_agent.refresh_requested",return_value=True):
            service.tick()
        self.assertTrue(service.reload_requested)
        self.assertEqual(service.console.starts,0)

    def test_start_is_deferred_during_update_and_then_starts_once(self):
        console = FakeConsole()
        service = ai.ChatService(console)
        with mock.patch("v13.pipeline_agent.snapshot",
                        return_value={"last_result": "CHECKING"}):
            self.assertEqual(service.command("start", {}),
                             {"status": "START_DEFERRED_FOR_UPDATE"})
            self.assertTrue(ai._read_desired())
            self.assertEqual(console.starts, 0)
            service.tick()
            self.assertEqual(console.starts, 0)
        service.tick()
        self.assertEqual(console.starts, 1)

    def test_supervisor_rechecks_update_before_model_launch(self):
        ai._desired(True)
        console = FakeConsole()
        service = ai.ChatService(console)
        # First snapshot is safe; update begins before the launch recheck.
        with mock.patch("v13.pipeline_agent.snapshot", side_effect=[
                {"last_result": "UP_TO_DATE"}, {"last_result": "CHECKING"}]):
            service.tick()
        self.assertEqual(console.starts, 0)
        self.assertEqual(service.status, "START_DEFERRED_FOR_UPDATE")
        service.tick()
        self.assertEqual(console.starts, 1)

    def test_supervisor_rechecks_explicit_off_before_model_launch(self):
        ai._desired(True)
        console = FakeConsole()
        service = ai.ChatService(console)
        original = ai._read_desired
        with mock.patch.object(ai, "_read_desired", side_effect=[True, True, False]):
            service.tick()
        self.assertEqual(console.starts, 0)
        self.assertEqual(service.status, "START_DEFERRED_FOR_UPDATE")
        self.assertTrue(original())

    def test_stop_request_defers_explicit_start(self):
        service = ai.ChatService(FakeConsole())
        with mock.patch.object(ai.lifecycle, "STOP_REQUEST", mock.Mock(exists=lambda: True)):
            self.assertEqual(service.command("start", {})["status"],
                             "START_DEFERRED_FOR_UPDATE")
        self.assertEqual(service.console.starts, 0)

    def test_explicit_off_never_consumes_update_resume(self):
        console = FakeConsole()
        service = ai.ChatService(console)
        ai._desired(False)
        with mock.patch.object(ai.lifecycle, "service_resume",
                               side_effect=AssertionError("OFF resumed")):
            service.tick()
        self.assertEqual(console.starts, 0)
        self.assertEqual(service.status, "STOPPED_BY_USER")

    def test_private_unix_socket_rpc_is_local_and_browserless(self):
        ai._desired(True)
        server=ai.Server(str(ai.SOCKET), ai.Handler)
        os.chmod(ai.SOCKET,0o600)
        server.ai=ai.ChatService(FakeConsole())
        run=threading.Thread(target=server.serve_forever,daemon=True)
        run.start()
        try:
            self.assertEqual(ai.call("start")["status"],"STARTED")
            self.assertEqual(ai.call("send",line="Hello V13")["status"],"SENT")
            self.assertTrue(ai.call("state")["running"])
            self.assertIn("Guten Tag",ai.call("output",limit=500))
            self.assertIn("test.log",ai.call("saved_sessions"))
            self.assertIn("Guten Tag",ai.call("transcript"))
            self.assertEqual(oct(ai.SOCKET.stat().st_mode & 0o777),"0o600")
            self.assertEqual(ai.call("shutdown")["status"],"SHUTDOWN_REQUESTED")
            self.assertFalse(ai.call("state")["autostart"])
        finally:
            server.shutdown()
            server.server_close()
            run.join(timeout=3)
            ai.SOCKET.unlink(missing_ok=True)

    def test_unknown_action_cannot_execute_shell(self):
        ai._desired(True)
        service=ai.ChatService(FakeConsole())
        with self.assertRaises(ValueError):
            service.command("run_shell",{"line":"rm -rf /"})
        with self.assertRaises(ValueError):
            ai.call("run_shell",line="rm -rf /")


class RealDaemonTests(unittest.TestCase):
    """A detached service and test launcher survive disconnected browser clients."""
    def test_service_survives_client_disconnect_and_normal_text(self):
        with tempfile.TemporaryDirectory() as home:
            home=Path(home)
            (home/".v13-private").mkdir(mode=0o700)
            launcher=home/"v13/bin/v13"
            launcher.parent.mkdir(parents=True)
            launcher.write_text(
                "#!/bin/sh\n"
                "echo 'V13 · Age 0 · Bereit'\n"
                "while IFS= read -r text; do\n"
                "  echo \"du> $text\"\n"
                "  echo \"assistant> Ich höre: $text\"\n"
                "  if [ \"$text\" = ':shutdown' ]; then exit 0; fi\n"
                "done\n")
            launcher.chmod(0o700)
            env={**os.environ,"HOME":str(home),
                 "PYTHONPATH":str(Path(__file__).resolve().parents[1])}
            root=Path(__file__).resolve().parents[1]
            # Enable background AI separately from the GitHub updater.
            private=home/".v13-private"
            desired=private/"v13-ai-enabled.json"
            desired.write_text(json.dumps({"enabled":True}))
            desired.chmod(0o600)
            proc=subprocess.Popen([sys.executable,"-m","v13.chat_service","serve"],
                                  env=env,cwd=str(root),stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
            sock=private/"v13-ai.sock"
            def request(method,**data):
                payload=(json.dumps({"protocol":ai.PROTOCOL, "method":method,**data})+"\n").encode()
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as channel:
                    channel.settimeout(5)
                    channel.connect(str(sock))
                    channel.sendall(payload)
                    reply=b""
                    while not reply.endswith(b"\n"):
                        block=channel.recv(8192)
                        if not block:break
                        reply+=block
                return json.loads(reply)
            try:
                deadline=time.monotonic()+8
                while time.monotonic()<deadline:
                    if sock.is_socket():
                        try:
                            if request("state")["ok"]:break
                        except (OSError,ValueError):pass
                    time.sleep(.05)
                else:
                    self.fail("independent V13 daemon did not boot")
                self.assertTrue(request("state")["result"]["running"])
                sent=request("send",line="Wie geht es dir?")
                self.assertTrue(sent["ok"])
                receipt=sent["result"]
                self.assertTrue(receipt["input_logged"])
                self.assertEqual(receipt["session"],request("state")["result"]["last_session"])
                recorded=(private/"console-logs"/receipt["session"]).read_bytes()
                self.assertTrue(recorded[receipt["offset"]:].startswith(
                    "\n[du> Wie geht es dir?]\n".encode("utf8")))
                seen=""
                for _ in range(120):
                    seen=request("output",limit=4000)["result"]
                    if "assistant> Ich höre: Wie geht es dir?" in seen:break
                    time.sleep(.05)
                self.assertIn("assistant> Ich höre: Wie geht es dir?",seen)
                # Disconnect the browser/client; daemon must remain running.
                self.assertIsNone(proc.poll())
                self.assertTrue(request("send",line="Nächste Frage")["ok"])
                transcript=request("transcript")["result"]
                self.assertIn("Wie geht es dir?",transcript)
                self.assertIn("Nächste Frage",transcript)
                self.assertTrue(request("shutdown")["ok"])
            finally:
                if proc.poll() is None:
                    proc.terminate()
                proc.communicate(timeout=5)


if __name__=="__main__":
    unittest.main()
