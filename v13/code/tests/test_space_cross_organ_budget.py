"""Real EnlightenedSpace cross-organ contract regression; no GGUF/Android claim.

Run: PYTHONPATH=v13/code python -m unittest v13.code.tests.test_space_cross_organ_budget
(or python -m unittest discover -s v13/code/tests -p 'test_space_cross_organ_budget.py')
"""
import unittest
from v13.enlightened_space import EnlightenedSpace

class MemoryStore:
    def __init__(self):
        self.states = {}
        self.sources = {}
    def state(self, key, default):
        return self.states.get(key, (default, 0))
    def set_state(self, key, value, expected):
        old, version = self.state(key, {})
        if version != expected:
            raise ValueError("Stale state write")
        self.states[key] = (value, version + 1)
    def read_source(self, ref):
        key = (ref["source_id"], ref["char_start"], ref["char_end"])
        if key not in self.sources:
            raise ValueError("revoked source")
        return self.sources[key]

class CrossOrganBudget(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.space = EnlightenedSpace(self.store, "session")
        self.event = {"event_id":"turn-1","brain_generation_id":"gen-1"}
        self.ref = {"modality":"text","source_id":"user-1","char_start":0,"char_end":11}
        self.store.sources[("user-1",0,11)] = "hello world"

    def test_real_cross_organ_source_and_budget(self):
        self.space.publish(self.event,"WORLD","SEMANTIC",
                           summary="hello world memory",source_refs=[self.ref],
                           authority="SOURCE_POINTER")
        out = self.space.consume(self.event,"C3_LANGUAGE","hello world",
                                 max_messages=1,max_chars=80)
        self.assertEqual(out["entry_count"],1)
        self.assertLessEqual(sum(len(m["semantic_cue_not_fact"]) + sum(len(s["exact_source_text"]) for s in m["exact_sources"]) for m in out["messages"]),80)
        self.assertFalse(out["trained_latent"])
        self.assertLessEqual(sum(len(m["semantic_cue_not_fact"]) +
            sum(len(s["exact_source_text"]) for s in m["exact_sources"])
            for m in out["messages"]),24)
        self.assertEqual(out["messages"][0]["from"],"WORLD")

    def test_erasure_revokes_shared_memory(self):
        self.space.publish(self.event,"MEMORY","SEMANTIC",
                           summary="hello world",source_refs=[self.ref],
                           authority="USER_MEMORY_CUE")
        del self.store.sources[("user-1",0,11)]
        out = self.space.consume(self.event,"B2_GIST","hello world")
        self.assertEqual(out["entry_count"],0)

    def test_unselected_body_offer_never_becomes_c3_fact(self):
        self.space.publish(self.event,"B1_DETAIL","SEMANTIC",
                           summary="unsupported model guess",authority="CONTROL_ONLY")
        out = self.space.consume(self.event,"C3_LANGUAGE","unsupported model guess")
        self.assertEqual(out["entry_count"],0)

    def test_cross_generation_isolation(self):
        self.space.publish(self.event,"WORLD","CONTROL",summary="old generation")
        later = {"event_id":"turn-2","brain_generation_id":"gen-2"}
        self.assertEqual(self.space.consume(later,"C3_LANGUAGE","old generation")["entry_count"],0)

    def test_no_source_pointer_without_verified_source(self):
        with self.assertRaises(ValueError):
            self.space.publish(self.event,"WORLD","SEMANTIC",
                               summary="fabricated",authority="SOURCE_POINTER")

if __name__ == "__main__":
    unittest.main()
