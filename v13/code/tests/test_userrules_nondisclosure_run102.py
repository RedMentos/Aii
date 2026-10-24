"""Run102: user prohibition on disclosure must bind SEND, not merely CONTACT.
Actual Runtime/SQLite rule persistence; SEND effect is a synthetic policy
fixture, never a real external communication or an Age/tool promotion.
"""
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13 import userrules as U


SEND_CONTACTS = {
    "actions": {"SEND", "TOOL"},
    "objects": {"CONTACTS", "CONTENT_ANY", "TOOLS"},
    "declared": True,
}
CALCULATOR = {
    "actions": {"COMPUTE", "TOOL"},
    "objects": {"CALCULATOR", "TOOLS"},
    "declared": True,
}


class UserRulesNondisclosureRun102(unittest.TestCase):
    def check_prohibition(self, line):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            r = Runtime(home)
            try:
                added = U.add(r.store, line, "USER_TYPED")
                self.assertEqual(len(added), 1)
                self.assertEqual(added[0]["kind"], "FORBID")
                stored = U.rules(r.store)
                self.assertEqual(stored[0]["status"], "ACTIVE")
                verdict = U.verdict(stored, SEND_CONTACTS)[0]
                self.assertEqual(verdict, "DENY")
                self.assertEqual(U.verdict(stored, CALCULATOR)[0], "ALLOW")
            finally:
                r.close()
            # The same rule must still apply after an actual SQLite restart.
            r = Runtime(home)
            try:
                self.assertEqual(U.verdict(U.rules(r.store), SEND_CONTACTS)[0], "DENY")
            finally:
                r.close()

    def test_expose_phone_number_cannot_be_sent(self):
        self.check_prohibition("Do not expose my phone number.")

    def test_reveal_phone_number_cannot_be_sent(self):
        self.check_prohibition("Do not reveal my phone number.")

    def test_divulge_phone_number_cannot_be_sent(self):
        self.check_prohibition("Do not divulge my phone number.")

    def test_broadcast_phone_number_cannot_be_sent(self):
        self.check_prohibition("Do not broadcast my phone number.")

    def test_existing_disclose_control_stays_denied(self):
        self.check_prohibition("Do not disclose my phone number.")

    def test_unclear_private_message_request_still_asks(self):
        with tempfile.TemporaryDirectory() as td:
            r = Runtime(Path(td))
            try:
                U.add(r.store, "Keep my messages private.", "USER_TYPED")
                self.assertEqual(U.verdict(U.rules(r.store), SEND_CONTACTS)[0], "ASK")
            finally:
                r.close()

    def test_positive_request_does_not_create_prohibition(self):
        with tempfile.TemporaryDirectory() as td:
            r = Runtime(Path(td))
            try:
                self.assertEqual(U.add(r.store, "Please reveal my phone number.", "USER_TYPED"), [])
                self.assertEqual(U.rules(r.store), [])
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
