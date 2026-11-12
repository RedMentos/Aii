import tempfile
import unittest
from pathlib import Path
from v13.private_diagnostics_bridge import DiagnosticBridge


class DiagnosticBridgeTests(unittest.TestCase):
    def test_opt_in_privacy_redaction_and_durable_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            def metrics():
                calls.append(1)
                return {"ready": True, "private_text": "secret", "queue_depth": -1}
            path = Path(tmp) / "seen.json"
            make = lambda enabled: DiagnosticBridge(path, allowed_authors={"agent"}, metrics={"HEALTH": metrics}, enabled=enabled)
            msg = {"id": "request_123456", "command": "HEALTH", "author": "agent", "expires_at": 120}
            self.assertEqual(make(False).handle(msg, private_relay=True, authenticated_author="agent", now=100)["status"], "DENIED")
            bridge = make(True)
            self.assertEqual(bridge.handle(msg, private_relay=False, authenticated_author="agent", now=100)["status"], "DENIED")
            self.assertEqual(bridge.handle(msg, private_relay=True, authenticated_author="other", now=100)["status"], "DENIED")
            self.assertEqual(bridge.handle(msg, private_relay=True, authenticated_author="agent", now=100)["metrics"], {"ready": True})
            self.assertEqual(make(True).handle(msg, private_relay=True, authenticated_author="agent", now=100)["status"], "DUPLICATE")
            self.assertEqual(make(True).handle(dict(msg, expires_at=121), private_relay=True, authenticated_author="agent", now=100)["status"], "REPLAY_CONFLICT")
            self.assertEqual(len(calls), 1)

    def test_strict_schema_expiry_and_invalid_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = DiagnosticBridge(Path(tmp) / "state", allowed_authors={"a"}, metrics={}, enabled=True)
            msg = {"id": "request_123456", "command": "HEALTH", "author": "a", "expires_at": 100}
            for change, expected in [({"command": "SHELL"}, "INVALID"), ({"command": []}, "INVALID"),
                                     ({"expires_at": 1000}, "EXPIRED"), ({"author": "b"}, "DENIED"),
                                     ({"extra": "x"}, "INVALID")]:
                self.assertEqual(bridge.handle(dict(msg, **change), private_relay=True, authenticated_author="a", now=100)["status"], expected)
