"""Actual Runtime/Store F1/F5 -> synthetic C3 -> C5/C6 DRAFT integration tests."""
import hashlib
from pathlib import Path
import tempfile
import time
import unittest

from v13.runtime import Runtime
from v13 import runtime_c3_atomic_draft_candidate as bridge
from scripts.run51_f1f5_second_attempt_native import load_fixture

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run51_f1f5_second_attempt_seed467.json"


class FakeC3:
    def __init__(self):
        self.last_metrics = {"status": "FINAL", "synthetic": True}
        self.calls = []
        self.output = "Project Cypress budget is 64 Euro."
        self.on_generate = None

    def generate(self, messages, cancel, deadline, max_tokens, schema, *, seed):
        self.calls.append((messages, max_tokens, schema, seed))
        if self.on_generate:
            self.on_generate()
        return [self.output]


class RuntimeC3DraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.f = load_fixture(FIXTURE)["fixtures"][0]
        self.current = self.r.store.event(self.r.session, self.f["followup"])
        self.c3 = FakeC3()
        self.roles = []
        self.releases = []
        self.r.pool.get = self.get
        self.r.pool.unload = lambda: self.releases.append("UNLOADED")

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def get(self, role):
        self.roles.append(role)
        if role != "C3_LANGUAGE":
            raise AssertionError("wrong role")
        return self.c3

    def correction(self):
        event = self.r.store.event(self.r.session, self.f["correction_event"])
        return self.r.memory.feedback(
            event["event_id"], "fact", self.f["value"], permission="record",
            key=self.f["key"], scope="session")

    def run(self, opt=True, model_opt=True, deadline=None, tokens=96):
        return bridge.stage_runtime_c3_draft(
            self.r, self.current["event_id"],
            time.monotonic()+30 if deadline is None else deadline,
            operator_opt_in=opt, model_call_opt_in=model_opt,
            max_tokens=tokens)

    def counts(self):
        return (
            self.r.store.one("SELECT COUNT(*) AS n FROM actions")["n"],
            self.r.store.one("SELECT COUNT(*) AS n FROM packets WHERE kind IN "
                             "('ActionIntent','CorollaryCopy')")["n"],
            self.r.store.one("SELECT COUNT(*) AS n FROM messages "
                             "WHERE role='assistant'")["n"],
        )

    def test_runtime_c3_f1f5_atomic_draft_no_delivery(self):
        self.correction()
        before = self.counts()
        r = self.run()
        self.assertEqual(r["status"], "RUNTIME_C3_DRAFT_BOUND_SHADOW_NO_COMMIT")
        self.assertEqual(self.roles, ["C3_LANGUAGE"])
        self.assertEqual(len(self.c3.calls), 1)
        messages, tokens, schema, seed = self.c3.calls[0]
        self.assertEqual((tokens, schema, seed), (96, None, 13))
        self.assertTrue(any("64 Euro" in m["content"] for m in messages))
        self.assertEqual(self.releases, ["UNLOADED"])
        self.assertEqual(tuple(a-b for a,b in zip(self.counts(), before)), (1,2,1))
        self.assertEqual(r["candidate_sha256"], hashlib.sha256(
            self.c3.output.encode()).hexdigest())
        self.assertNotIn("candidate_text", r)
        self.assertFalse(r["native_proof"])
        self.assertEqual(r["delivery_authority"], 0)
        self.assertFalse(r["output_committed"])
        self.assertEqual(r["tool_dispatches"], 0)
        self.assertEqual(r["learning_authority"], 0)
        row = self.r.store.one("SELECT status,text FROM messages WHERE id=?",
                               (r["draft_message_id"],))
        self.assertEqual(row, {"status":"DRAFT","text":self.c3.output})
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"], 0)

    def test_missing_human_correction_never_calls_c3_or_stages(self):
        before = self.counts()
        r = self.run()
        self.assertEqual(r["status"], "CLARIFY")
        self.assertFalse(r["model_called"])
        self.assertEqual(self.roles, [])
        self.assertEqual(self.counts(), before)

    def test_two_strict_optins_and_invalid_deadline_token_budget(self):
        self.correction()
        before = self.counts()
        for opt, model in [(False, True), (True, False), (1, True),
                           (True, "yes"), (None, None)]:
            self.assertEqual(self.run(opt=opt, model_opt=model)["status"], "OFF")
        for tokens in (0, 257, True, 1.5):
            self.assertEqual(self.run(tokens=tokens)["status"], "INVALID_INPUT")
        self.assertEqual(self.run(deadline=time.monotonic()-1)["status"],
                         "DEADLINE_EXPIRED")
        self.assertEqual(self.roles, [])
        self.assertEqual(self.counts(), before)

    def test_busy_and_cancelled_runtime_reject_before_model(self):
        self.correction()
        before = self.counts()
        self.r.current = object()
        self.assertEqual(self.run()["status"], "RUNTIME_NOT_IDLE")
        self.r.current = None
        self.r.cancel_event.set()
        self.assertEqual(self.run()["status"], "RUNTIME_NOT_IDLE")
        self.r.cancel_event.clear()
        self.assertEqual(self.roles, [])
        self.assertEqual(self.counts(), before)

    def test_nonfinal_bad_candidate_and_generator_error_no_stage(self):
        self.correction()
        before = self.counts()
        self.c3.last_metrics = {"status": "ERROR", "synthetic": True}
        self.assertEqual(self.run()["status"], "GENERATION_ERROR")
        self.assertEqual(self.counts(), before)
        self.c3.last_metrics = {"status": "FINAL", "synthetic": True}
        self.c3.output = ""
        self.assertEqual(self.run()["status"], "INVALID_CANDIDATE")
        self.assertEqual(self.counts(), before)
        def fail():
            raise RuntimeError("fake native failure")
        self.c3.on_generate = fail
        self.assertEqual(self.run()["status"], "GENERATION_ERROR")
        self.assertEqual(self.counts(), before)
        self.assertEqual(len(self.releases), 3)

    def test_revocation_during_c3_and_deleted_current_source_no_stage(self):
        mid = self.correction()
        before = self.counts()
        self.c3.on_generate = lambda: self.r.memory.forget(mid)
        self.assertEqual(self.run()["status"], "SOURCE_CHANGED_BEFORE_DRAFT")
        self.assertEqual(self.counts(), before)
        self.c3.on_generate = None
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.current["source_ref"]["source_id"],))
        self.assertEqual(self.run()["status"], "EVENT_OR_SOURCE_RED")
        self.assertEqual(self.counts(), before)

    def test_restart_interrupts_draft_and_does_not_promote(self):
        self.correction()
        r = self.run()
        self.assertEqual(r["status"], "RUNTIME_C3_DRAFT_BOUND_SHADOW_NO_COMMIT")
        mid = r["draft_message_id"]
        session = self.r.session
        self.r.close()
        self.r = Runtime(self.home)
        self.r.session = session
        self.assertEqual(self.r.store.one(
            "SELECT status FROM messages WHERE id=?", (mid,))["status"],
            "INTERRUPTED")
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
            "AND status='FINAL'")["n"], 0)


if __name__ == "__main__":
    unittest.main()
