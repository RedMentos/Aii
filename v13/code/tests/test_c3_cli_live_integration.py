"""Cross-branch software integration of live C3 source rendering and no-worker CLI."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13 import source_consumer
from scripts.ask_verified_budget import BudgetContext, query


class FakeC3:
    def __init__(self):
        self.calls = 0
        self.last_metrics = {"status": "FINAL"}

    def generate(self, messages, cancel, deadline, *, max_tokens, seed):
        self.calls += 1
        assert seed == 13 and max_tokens <= 128
        yield "The budget for Project Elyra is 615 Euro."


class IntegratedC3SourceCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        r = Runtime(self.home)
        r.sleep.cycle.set_policy("enabled", "off")
        self.session = r.session
        event = r.store.event(self.session, "Project Elyra budget")
        r.memory.feedback(event["event_id"], "fact", "615 Euro",
                          key="Project Elyra budget", permission="record")
        r.close()
        self.ctx = BudgetContext(self.home)
        self.question = "What is the budget for Project Elyra?"

    def tearDown(self):
        self.ctx.close()
        self.tmp.cleanup()

    def test_no_worker_live_source_preflight(self):
        self.assertFalse(hasattr(self.ctx, "worker"))
        with patch.object(self.ctx.pool, "get", side_effect=AssertionError("native called")):
            result = query(self.ctx, self.question, self.session)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["native_calls"], 0)

    def test_revocation_between_first_and_second_recall_refuses(self):
        original = self.ctx.memory.recall
        counter = [0]
        def disappear(*args, **kwargs):
            counter[0] += 1
            return original(*args, **kwargs) if counter[0] == 1 else []
        with patch.object(self.ctx.memory, "recall", side_effect=disappear), \
             patch.object(self.ctx.pool, "get", side_effect=AssertionError("native called")):
            result = query(self.ctx, self.question, self.session, native=True)
        self.assertGreaterEqual(counter[0], 2)
        self.assertEqual(result["status"], "CLARIFY")
        self.assertEqual(result["reason"], "SOURCE_REVALIDATION_FAILED")
        self.assertEqual(result["native_calls"], 0)

    def test_conflict_inserted_at_render_boundary_refuses(self):
        original = source_consumer.render_messages
        inserted = [False]
        def inject(*args, **kwargs):
            if not inserted[0]:
                inserted[0] = True
                event = self.ctx.store.event(self.session, "Project Elyra budgets")
                self.ctx.memory.feedback(event["event_id"], "fact", "700 Euro",
                                         key="Project Elyra budgets", permission="record")
            return original(*args, **kwargs)
        with patch.object(source_consumer, "render_messages", side_effect=inject), \
             patch.object(self.ctx.pool, "get", side_effect=AssertionError("native called")):
            result = query(self.ctx, self.question, self.session, native=True)
        self.assertTrue(inserted[0])
        self.assertEqual(result["status"], "CLARIFY")
        self.assertEqual(result["reason"], "SOURCE_REVALIDATION_FAILED")
        self.assertEqual(result["native_calls"], 0)

    def test_fake_native_one_call_after_live_source_and_exact_model_pin_seam(self):
        runner = FakeC3()
        with patch("scripts.ask_verified_budget._pinned_c3", return_value=True), \
             patch.object(self.ctx.models, "verify", return_value={
                 "language": {"ok": True, "hash_checked": True}}), \
             patch.object(self.ctx.models, "path_for", return_value=Path("fake.gguf")), \
             patch.object(self.ctx.pool, "get", return_value=runner), \
             patch.object(self.ctx.pool, "unload", return_value={"process_reaped": True}) as unload:
            result = query(self.ctx, self.question, self.session, native=True)
        self.assertEqual(result["status"], "FINAL")
        self.assertEqual(result["native_calls"], 1)
        self.assertEqual(runner.calls, 1)
        unload.assert_called_once_with("C3_LANGUAGE")


if __name__ == "__main__":
    unittest.main()
