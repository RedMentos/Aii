"""Synthetic regression for local WebView send acknowledgement (not Redmi proof)."""
import threading
import unittest

from v13.mobile_dashboard import RuntimeControls


class StubTerminal:
    def __init__(self, receipt):
        self.receipt = receipt
        self.sent = []

    def send(self, line):
        self.sent.append(line)
        return self.receipt


class DashboardReceiptTests(unittest.TestCase):
    def controls(self, receipt):
        controls = RuntimeControls.__new__(RuntimeControls)
        controls.terminal = StubTerminal(receipt)
        controls.lock = threading.Lock()
        controls.last_action = "Keine Aktion"
        return controls

    def test_only_positive_model_receipt_is_acknowledged(self):
        for receipt in ({"status": "SENT"}, {"status": "SHUTDOWN_REQUESTED"}):
            with self.subTest(receipt=receipt):
                controls = self.controls(receipt)
                self.assertEqual(controls.send("hi"), receipt)
                self.assertEqual(controls.last_action, "Nachricht")

    def test_negative_and_malformed_receipts_never_claim_send(self):
        for receipt in ({"status": "NOT_RUNNING"}, {"status": "STOPPED_BY_USER"},
                        {"status": "PAUSED_FOR_UPDATE"},
                        {"status": "START_DEFERRED_FOR_UPDATE"},
                        {"status": "MODEL_ERROR"}, {}, None, "SENT"):
            with self.subTest(receipt=receipt):
                controls = self.controls(receipt)
                with self.assertRaises((ValueError, RuntimeError)):
                    controls.send("hi")
                self.assertEqual(controls.last_action, "Keine Aktion")

    def test_error_messages_distinguish_stop_update_and_offline(self):
        cases = (("NOT_RUNNING", "Zuerst V13 Chat starten"),
                 ("STOPPED_BY_USER", "ausgeschaltet"),
                 ("PAUSED_FOR_UPDATE", "aktualisiert"))
        for status, message in cases:
            with self.subTest(status=status):
                with self.assertRaisesRegex(ValueError, message):
                    self.controls({"status": status}).send("hi")


if __name__ == "__main__":
    unittest.main()
