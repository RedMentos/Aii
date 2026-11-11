"""Synthetic-only Android companion contract regression tests."""
import hashlib
import unittest

from v13.android_companion_contract import (
    ActionRequest, AndroidCompanionGateway, CapabilityRegistry, CapabilityState
)
from v13.android_control import ControlDenied, _canonical


class AndroidCompanionContractTest(unittest.TestCase):
    def request(self, capability="back", args=None, expiry=200):
        args = {} if args is None else args
        digest = hashlib.sha256(_canonical(capability, args).encode()).hexdigest()
        return ActionRequest("action-1", capability, args, digest, expiry)

    def test_all_native_capabilities_default_off(self):
        reg = CapabilityRegistry()
        self.assertTrue(reg.status())
        self.assertTrue(all(x == "OFF" for x in reg.status().values()))
        self.assertEqual(reg.get("tap").state, CapabilityState.OFF)

    def test_preview_never_claims_native_execution(self):
        gateway = AndroidCompanionGateway(clock=lambda: 100)
        outcome = gateway.preview(self.request())
        self.assertEqual(outcome.status, "DRY_RUN_ONLY")
        self.assertEqual(outcome.source, "synthetic_preview")

    def test_dispatch_never_calls_unverified_transport(self):
        gateway = AndroidCompanionGateway(clock=lambda: 100)
        class DangerousTransport:
            def dispatch(self, request):
                raise AssertionError("must not reach transport")
        with self.assertRaises(ControlDenied):
            gateway.dispatch(self.request(), DangerousTransport())

    def test_expired_and_tampered_requests_rejected(self):
        gateway = AndroidCompanionGateway(clock=lambda: 100)
        with self.assertRaises(ControlDenied):
            gateway.preview(self.request(expiry=99))
        req = self.request()
        bad = ActionRequest(req.action_id, req.capability, req.args, "0" * 64, req.expires_at)
        with self.assertRaises(ControlDenied):
            gateway.preview(bad)

    def test_unsupported_action_rejected(self):
        gateway = AndroidCompanionGateway(clock=lambda: 100)
        with self.assertRaises(ControlDenied):
            gateway.preview(self.request("shell", {}))


if __name__ == "__main__":
    unittest.main()
