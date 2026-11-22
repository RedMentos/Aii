import tempfile
import unittest
from pathlib import Path
from v13.android_companion_protocol import ReceiptVerifier, CompanionDenied, SCHEMA, sign_fixture

class ReceiptTests(unittest.TestCase):
    def test_scope_auth_consent_replay_restart_stop(self):
        secret = b"k" * 32
        env = {"action_id": "a1", "capability": "back", "digest": "d" * 64}
        body = dict(schema=SCHEMA, nonce="a" * 32, action_id="a1", capability="back",
                    digest="d" * 64, issued_at=100, expires_at=130,
                    status="EXECUTED", local_consent=True)
        def signed(b):
            return {"body": b, "mac": sign_fixture(secret, b)}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipts.db"
            v = ReceiptVerifier(path, secret, clock=lambda: 110)
            with self.assertRaises(CompanionDenied):
                v.verify(env, signed(body))
            v.start()
            for change in ({"local_consent": False}, {"capability": "tap"},
                           {"expires_at": 101}, {"status": "PENDING"}):
                with self.assertRaises(CompanionDenied):
                    v.verify(env, signed(dict(body, **change)))
            tampered = signed(body)
            tampered["body"] = dict(body, digest="e" * 64)
            with self.assertRaises(CompanionDenied):
                v.verify(env, tampered)
            result = v.verify(env, signed(body))
            self.assertFalse(result["t8_authoritative"])
            with self.assertRaises(CompanionDenied):
                v.verify(env, signed(body))
            v.close()
            v = ReceiptVerifier(path, secret, clock=lambda: 110)
            v.start()
            with self.assertRaises(CompanionDenied):
                v.verify(env, signed(body))
            v.stop()
            with self.assertRaises(CompanionDenied):
                v.verify(env, signed(dict(body, nonce="b" * 32)))
            v.close()

    def test_deferred_nonce_verification_requires_atomic_consumer_commit(self):
        secret = b"d" * 32
        env = {"action_id": "b2", "capability": "back", "digest": "e" * 64}
        body = dict(schema=SCHEMA, nonce="f" * 32, action_id="b2",
                    capability="back", digest="e" * 64, issued_at=100,
                    expires_at=130, status="EXECUTED", local_consent=True)
        with tempfile.TemporaryDirectory() as tmp:
            v = ReceiptVerifier(Path(tmp) / "receipts.db", secret, clock=lambda: 110)
            v.start()
            receipt = {"body": body, "mac": sign_fixture(secret, body)}
            first = v.verify(env, receipt, consume_nonce=False)
            second = v.verify(env, receipt, consume_nonce=False)
            self.assertEqual(first["nonce"], body["nonce"])
            self.assertEqual(second["nonce"], body["nonce"])
            v.verify(env, receipt)
            with self.assertRaises(CompanionDenied):
                v.verify(env, receipt)
            v.close()


if __name__ == "__main__":
    unittest.main()
