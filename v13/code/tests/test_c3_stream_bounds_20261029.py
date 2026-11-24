"""Preregistered C3 output stream bound; software fake-native only."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import ask_verified_budget as V
from v13.runtime import Runtime

MAX_CHARS = 32768


class FakeStreamingRunner:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = 0
        self.last_metrics = {"status": "FINAL"}

    def generate(self, messages, cancel, deadline, *, max_tokens, seed):
        self.calls += 1
        for chunk in self.chunks:
            yield chunk


class C3StreamBoundTests(unittest.TestCase):
    def test_normal_chunks_are_preserved(self):
        self.assertEqual(V._collect_bounded_output(iter(["615", " Euro", "."])),
                         "615 Euro.")

    def test_oversized_whitespace_prefix_fails_closed(self):
        self.assertIsNone(V._collect_bounded_output(
            iter([" " * MAX_CHARS, "615 Euro."])))

    def test_non_string_chunk_fails_closed(self):
        self.assertIsNone(V._collect_bounded_output(
            iter(["615", b" Euro", "."])))

    def test_integrated_oversized_fake_native_never_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Runtime(Path(tmp))
            try:
                event = r.store.event(r.session, "Project Elyra budget")
                mid = r.memory.feedback(event["event_id"], "fact", "615 Euro",
                                        key="Project Elyra budget", permission="record")
                r.memory.candidate(mid, r.session)
                runner = FakeStreamingRunner([" " * MAX_CHARS, "615 Euro."])
                with patch.object(V, "_pinned_c3", return_value=True), \
                     patch.object(r.memory.semantic_keys, "mode", return_value="off"), \
                     patch.object(r.models, "verify", return_value={
                         "language": {"ok": True, "hash_checked": True}}), \
                     patch.object(r.models, "path_for", return_value=Path("fake.gguf")), \
                     patch.object(r.pool, "get", return_value=runner), \
                     patch.object(r.pool, "unload",
                                  return_value={"process_reaped": True}) as unload:
                    got = V.query(r, "What is the budget for Project Elyra?", native=True)
                self.assertEqual(runner.calls, 1)
                unload.assert_called_once_with("C3_LANGUAGE")
                self.assertEqual(got["status"], "UNVERIFIED_NATIVE_ANSWER")
                self.assertEqual(got["native_calls"], 1)
                self.assertNotIn("answer", got)
            finally:
                r.close()


if __name__ == "__main__":
    unittest.main()
