"""No real models: additive overflow-companion contracts."""
import unittest
from v13 import overflow_companion as C

HISTORY = [{"event_id": "old", "role": "user", "text": "The answer was 4271."},
           {"event_id": "new", "role": "user", "text": "New input must remain raw."}]
PLAN = {"items": [{"item_id": "old", "layer": "SOURCE_LINKS", "form": "POINTER"},
                  {"item_id": "new", "layer": "RAW_HISTORY", "form": "RAW"}]}
OK = lambda eid, row: eid == "old"

class Contracts(unittest.TestCase):
    def test_no_overflow_never_calls_model(self):
        r = C.propose("PIN", {"items":[]}, HISTORY, "q", lambda _: 1/0, OK)
        self.assertEqual(r["status"], "NO_OVERFLOW")

    def test_source_validation_is_mandatory(self):
        r = C.propose("PIN", PLAN, HISTORY, "q", lambda _: "4271")
        self.assertEqual(r["status"], "SOURCE_VALIDATOR_REQUIRED")
        self.assertFalse(r["applied"])

    def test_fixed_header_and_existing_volatile_unchanged(self):
        stable = "LOCKED HEADER"
        original = [("ACTIVE_VIEW", "\nMEM:", {"prior": "keep"})]
        r = C.propose(stable, PLAN, HISTORY, "what?", lambda _: "The answer was 4271.", OK)
        self.assertEqual(r["status"], "PROPOSED")
        self.assertEqual(r["source_event_ids"], ["old"])
        self.assertEqual(C.add_volatile(original, r), original)
        v = C.add_volatile(original, r, explicitly_approved=True, ctxos_active=True)
        self.assertEqual(v[0], original[0])
        self.assertEqual(v[1][0], "ADDITIONAL_CONTEXT")
        self.assertEqual(stable, "LOCKED HEADER")

    def test_rejects_invented_exact_number(self):
        r = C.propose("PIN", PLAN, HISTORY, "q", lambda _: "The answer was 9999.", OK)
        self.assertEqual(r["status"], "UNSUPPORTED_EXACT")
        self.assertEqual(r["text"], "")

    def test_missing_source_fails_closed(self):
        r = C.propose("PIN", PLAN, HISTORY, "q", lambda _: "4271",
                      lambda eid, row: False)
        self.assertEqual(r["status"], "NO_VERIFIED_SOURCES")
        self.assertEqual(C.add_volatile([], r, explicitly_approved=True, ctxos_active=True), [])

    def test_model_exception_fails_closed(self):
        def unavailable(_): raise TimeoutError("worker unavailable")
        r = C.propose("PIN", PLAN, HISTORY, "q", unavailable, OK)
        self.assertEqual(r["status"], "MODEL_ERROR")
        self.assertEqual(r["error"], "TimeoutError")

if __name__ == "__main__":
    unittest.main()
