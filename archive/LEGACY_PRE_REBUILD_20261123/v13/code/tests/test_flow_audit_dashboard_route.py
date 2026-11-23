"""Local-only, token-scoped, read-only flow-audit dashboard endpoint."""
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import urllib.error
import urllib.request
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from v13 import mobile_dashboard as d
from v13.store import Store


class FlowAuditDashboardRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.data = root / "v13"
        self.private = root / "priv"
        (self.data / "exports").mkdir(parents=True)
        (self.data / "bin").mkdir()
        self.private.mkdir(mode=0o700)
        self.old_data, self.old_private = d.DATA, d.PRIVATE
        d.DATA, d.PRIVATE = self.data, self.private
        self.addCleanup(self.restore)

    def restore(self):
        d.DATA, d.PRIVATE = self.old_data, self.old_private

    def test_flow_audit_http_route_is_token_scoped_local_and_read_only(self):
        # Store expects its private data root before opening coordinator.lock.
        (self.data / "data" / "db").mkdir(parents=True, exist_ok=True)
        (self.data / "data" / "blobs").mkdir(parents=True, exist_ok=True)
        store = Store(self.data)
        try:
            session = store.new_session("dashboard fixture")
            event = store.event(session, "PRIVATE_EVENT_TEXT_SENTINEL")
            store.message(
                session, event["event_id"], "assistant", "PRIVATE_ASSISTANT_TEXT_SENTINEL",
                status="FINAL", metadata={
                    "runner": {
                        "role": "C3_LANGUAGE", "status": "FINAL",
                        "actual_model": "fixture-c3", "prompt_tokens": 8,
                        "generated_tokens": 3, "ttft_s": 0.5,
                        "duration_s": 1.0, "synthetic": True,
                    }
                },
            )
        finally:
            store.close()

        db = self.data / "data" / "db" / "brain.sqlite3"
        before = db.read_bytes()
        token, csrf = "f" * 48, "e" * 48
        servers, errors = [], []
        original_server = d.ThreadingHTTPServer

        class CaptureServer(original_server):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                servers.append(self)

        class NoopThread:
            def __init__(self, *args, **kwargs):
                pass

            def start(self):
                return None

        def run_server():
            try:
                d.serve(open_browser=False)
            except BaseException as exc:
                errors.append(exc)

        with patch.object(d, "ThreadingHTTPServer", CaptureServer), \
             patch.object(d, "_ui_singleton_lock", lambda: 0), \
             patch.object(d, "threading", SimpleNamespace(Lock=threading.Lock, Thread=NoopThread)), \
             patch.dict(os.environ, {
                 "V13_UI_RESTART_TOKEN": token,
                 "V13_UI_RESTART_CSRF": csrf,
                 "V13_UI_RESTART_PORT": "",
                 "V13_UI_PORT": "0",
                 "V13_UI_NO_AUTO_OPEN": "1",
             }, clear=False):
            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()
            for _ in range(100):
                if servers or errors:
                    break
                time.sleep(0.01)
            self.assertFalse(errors, errors)
            self.assertTrue(servers)
            server = servers[0]
            try:
                self.assertEqual(server.server_address[0], "127.0.0.1")
                port = server.server_port
                url = f"http://127.0.0.1:{port}/t/{token}/flow-audit"
                with urllib.request.urlopen(url, timeout=3) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn("no-store", response.headers.get("Cache-Control", ""))
                    self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
                    payload = json.loads(response.read().decode("utf-8"))

                rendered = json.dumps(payload)
                self.assertEqual(payload["availability"], "AVAILABLE")
                self.assertEqual(payload["selection_scope"], "LATEST_COMPLETED_TURN_ALL_SESSIONS")
                self.assertEqual(payload["redmi_status"], "REDMI_UNVERIFIED")
                self.assertIs(payload["latent"]["native_injection_proven"], False)
                self.assertNotIn(event["event_id"], rendered)
                self.assertNotIn(session, rendered)
                self.assertNotIn("PRIVATE_EVENT_TEXT_SENTINEL", rendered)
                self.assertNotIn("PRIVATE_ASSISTANT_TEXT_SENTINEL", rendered)

                for bad_url in (
                    f"http://127.0.0.1:{port}/flow-audit",
                    f"http://127.0.0.1:{port}/t/{'a' * 48}/flow-audit",
                ):
                    with self.assertRaises(urllib.error.HTTPError) as denied:
                        urllib.request.urlopen(bad_url, timeout=3)
                    self.assertEqual(denied.exception.code, 404)

                bad_host = urllib.request.Request(
                    url, headers={"Host": f"attacker.invalid:{port}"}
                )
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    urllib.request.urlopen(bad_host, timeout=3)
                self.assertEqual(denied.exception.code, 403)

                post = urllib.request.Request(url, data=b"", method="POST")
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    urllib.request.urlopen(post, timeout=3)
                self.assertEqual(denied.exception.code, 404)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())

        self.assertEqual(before, db.read_bytes())


if __name__ == "__main__":
    unittest.main()
