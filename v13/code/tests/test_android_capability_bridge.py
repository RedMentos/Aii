"""Synthetic contract tests: no native Android execution or permission claims."""
import unittest
from v13.android_capability_bridge import (
    Capability, CapabilityRegistry, ActionRequest, AndroidActionBridge,
    ExecutionStatus, SPECS,
)

class AndroidBridgeTests(unittest.TestCase):
    def test_default_off_shadow_stop_and_t8_redaction(self):
        registry = CapabilityRegistry()
        bridge = AndroidActionBridge(registry, clock=lambda: 100)
        def request(i):
            return ActionRequest(i, Capability.SPEAK_TEXT,
                                 {"text": "private speech"}, "turn-1", 120)
        self.assertEqual(bridge.submit(request("a")).status, ExecutionStatus.OFF)
        registry.enable_shadow_for_test(Capability.SPEAK_TEXT)
        outcome = bridge.submit(request("b"))
        self.assertEqual(outcome.status, ExecutionStatus.SHADOW)
        self.assertNotIn("private speech", str(outcome.t8_record()))
        registry.stop()
        self.assertEqual(bridge.submit(request("c")).status, ExecutionStatus.OFF)

    def test_replay_expiry_and_no_native_grant(self):
        registry = CapabilityRegistry()
        registry.enable_shadow_for_test(Capability.TAP)
        bridge = AndroidActionBridge(registry, clock=lambda: 100)
        request = ActionRequest("a", Capability.TAP, {"x": 1, "y": 2}, "turn-2", 101)
        self.assertEqual(bridge.submit(request).status, ExecutionStatus.SHADOW)
        self.assertEqual(bridge.submit(request).error_code, "REPLAY")
        expired = ActionRequest("b", Capability.TAP, {}, "turn-2", 99)
        self.assertEqual(bridge.submit(expired).status, ExecutionStatus.DENIED)
        self.assertFalse(any(spec.native_verified for spec in SPECS.values()))

if __name__ == "__main__":
    unittest.main()
