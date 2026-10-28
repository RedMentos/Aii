"""Run13 RED-first synthetic review: B2 source identity ambiguity must fail closed."""
import hashlib
import unittest

from scripts import run12_b2_context_identity_candidate as original
from scripts import run13_b2_identity_ambiguity_guard as guard

CUR = "Project Aquila. Use the earlier binding project rules and latest supplier sheet."
NOTE = "Project Aquila kickoff memo. Budget 134 euros. Deadline 9 days. Local-only requirement: true."
ATLAS = "Project Atlas archive. Budget 999 euros. Deadline 1 day. Local-only requirement: false."
SHEET = "Project Aquila supplier sheet. Option A: 91 euros. Option B: 105 euros."
MIXED = "Project Aquila memo comparing Project Atlas archive. Budget 999 euros. Deadline 1 day. Local-only requirement: false."


def offer(text, n, **overrides):
    ref = {"source_id": "src_" + str(n), "sha256": hashlib.sha256(text.encode()).hexdigest(),
           "char_start": 0, "char_end": len(text), "modality": "text"}
    o = {"offer_id": "pkt_" + str(n), "role": "B2_GIST", "event_id": "evt_" + str(n),
         "session": "s1", "generation": "g1", "model_revision": "m1",
         "source_ref": ref, "hypothesis": "untrusted"}
    o.update(overrides)
    return o


def reader_for(items, texts, revoked=()):
    table = {x["source_ref"]["source_id"]: t for x, t in zip(items, texts)}
    def read(ref):
        if ref["source_id"] in revoked:
            raise ValueError("TOMBSTONED")
        t = table[ref["source_id"]]
        if hashlib.sha256(t.encode()).hexdigest() != ref["sha256"]:
            raise ValueError("CHANGED")
        return t[ref["char_start"]:ref["char_end"]]
    return read


def select(current, items, texts, **kw):
    return guard.select_context(current, "current", "s1", "g1", "m1",
                                items, reader_for(items, texts), **kw)


class B2IdentityAdversarial(unittest.TestCase):
    def test_original_cross_project_counterexample(self):
        current = "Project Aquila; ignore Project Atlas. Use earlier project rules."
        items = [offer(ATLAS, 2)]
        got = original.select_context(current, "current", "s1", "g1", "m1",
                                      items, reader_for(items, [ATLAS]))
        self.assertEqual(len(got["items"]), 1, "v1 unexpectedly fixed; revisit prereg")
        self.assertFalse(got["canonical_gate_pass"])

    def test_ambiguous_current_refuses_both_projects(self):
        items = [offer(ATLAS, 2), offer(NOTE, 1)]
        got = select("Project Aquila; ignore Project Atlas. Use earlier project rules.",
                     items, [ATLAS, NOTE])
        self.assertEqual(got["items"], [])
        self.assertEqual(got["reasons"].get("AMBIGUOUS_CURRENT_IDENTITY"), 2)

    def test_incidental_other_project_refused(self):
        items = [offer(MIXED, 3), offer(NOTE, 1)]
        got = select(CUR, items, [MIXED, NOTE])
        self.assertEqual([i["source_ref"]["source_id"] for i in got["items"]], ["src_1"])
        self.assertEqual(got["reasons"].get("AMBIGUOUS_SOURCE_IDENTITY"), 1)

    def test_original_rule_priority_and_cap_retained(self):
        items = [offer(SHEET, 3), offer(ATLAS, 2), offer(NOTE, 1)]
        got = select(CUR, items, [SHEET, ATLAS, NOTE], cap=768, slots=3)
        self.assertEqual([i["source_ref"]["source_id"] for i in got["items"]],
                         ["src_1", "src_3"])
        self.assertEqual(got["authority"], "SOURCE_POINTER_ONLY")
        self.assertFalse(got["canonical_gate_pass"])

    def test_slot_horizon_never_expands_after_rejection(self):
        items = [offer(MIXED, 3), offer(SHEET, 2), offer(NOTE, 1)]
        got = select(CUR, items, [MIXED, SHEET, NOTE], slots=2)
        self.assertEqual([i["source_ref"]["source_id"] for i in got["items"]], ["src_2"])
        self.assertEqual(got["reasons"].get("AMBIGUOUS_SOURCE_IDENTITY"), 1)

    def test_deleted_source_and_changed_digest_refused(self):
        item = offer(NOTE, 1)
        gone = guard.select_context(CUR, "current", "s1", "g1", "m1",
                                    [item], reader_for([item], [NOTE], revoked={"src_1"}))
        self.assertEqual(gone["items"], [])
        self.assertGreaterEqual(gone["reasons"].get("SOURCE_UNAVAILABLE", 0), 1)
        changed = guard.select_context(CUR, "current", "s1", "g1", "m1",
                                       [item], reader_for([item], [NOTE + " changed"]))
        self.assertEqual(changed["items"], [])

    def test_cross_session_source_not_read(self):
        item = offer(NOTE, 1, session="another")
        def no_read(ref):
            raise AssertionError("cross-session read attempted")
        got = guard.select_context(CUR, "current", "s1", "g1", "m1", [item], no_read)
        self.assertEqual(got["items"], [])
        self.assertEqual(got["reasons"].get("OUT_OF_SCOPE"), 1)

    def test_bad_bounds_and_input_rejected(self):
        item = offer(NOTE, 1)
        with self.assertRaisesRegex(ValueError, "BOUNDS"):
            select(CUR, [item], [NOTE], cap=20)
        with self.assertRaisesRegex(ValueError, "UNBOUNDED"):
            guard.select_context(CUR, "current", "s1", "g1", "m1", [item] * 65, lambda _: NOTE)

    def test_malformed_digest_never_reaches_source_reader(self):
        item = offer(NOTE, 1)
        item["source_ref"]["sha256"] = "not-a-sha256"
        def no_read(ref):
            raise AssertionError("malformed digest passed to source reader")
        got = guard.select_context(CUR, "current", "s1", "g1", "m1", [item], no_read)
        self.assertEqual(got["items"], [])
        self.assertEqual(got["reasons"].get("BAD_REF"), 1)

    def test_invalid_source_span_never_reaches_source_reader(self):
        item = offer(NOTE, 1)
        item["source_ref"]["char_start"] = -1
        def no_read(ref):
            raise AssertionError("negative span passed to source reader")
        got = guard.select_context(CUR, "current", "s1", "g1", "m1", [item], no_read)
        self.assertEqual(got["items"], [])
        self.assertEqual(got["reasons"].get("BAD_REF"), 1)



if __name__ == "__main__":
    unittest.main()
