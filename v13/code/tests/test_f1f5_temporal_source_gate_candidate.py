"""Real Runtime/SQLite F1/F5 temporal source gate adversarial software tests."""
from pathlib import Path
import tempfile
import time
import unittest

from v13.runtime import Runtime
from v13 import f1f5_temporal_source_gate_candidate as temporal
from scripts.run51_f1f5_second_attempt_native import load_fixture
from tests.test_runtime_c3_atomic_draft_candidate import FakeC3

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run51_f1f5_second_attempt_seed467.json"


class TemporalSourceGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name))
        self.f = load_fixture(FIXTURE)["fixtures"][0]
        self.c3 = FakeC3()
        self.roles = []
        self.releases = []
        self.r.pool.get = lambda role: (self.roles.append(role), self.c3)[1]
        self.r.pool.unload = lambda: self.releases.append("UNLOADED")

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def correction(self, value=None, permission="record"):
        e = self.r.store.event(self.r.session, self.f["correction_event"])
        return self.r.memory.feedback(
            e["event_id"], "fact", value or self.f["value"],
            permission=permission, key=self.f["key"], scope="session")

    def current(self):
        return self.r.store.event(self.r.session, self.f["followup"])

    def stage(self, event, opt=True, model_opt=True, tokens=96):
        return temporal.stage_temporal_runtime_c3_draft(
            self.r, event["event_id"], time.monotonic()+30,
            operator_opt_in=opt, model_call_opt_in=model_opt,
            max_tokens=tokens)

    def counts(self):
        return (
            self.r.store.one("SELECT COUNT(*) AS n FROM actions")["n"],
            self.r.store.one("SELECT COUNT(*) AS n FROM messages "
                             "WHERE role='assistant'")["n"],
        )

    def test_prior_human_correction_allows_one_uncommitted_c3_draft(self):
        self.correction()
        current = self.current()
        before = self.counts()
        r = self.stage(current)
        self.assertEqual(r["status"], "RUNTIME_C3_DRAFT_BOUND_SHADOW_NO_COMMIT")
        self.assertTrue(r["temporal_source_verified"])
        self.assertEqual(self.roles, ["C3_LANGUAGE"])
        self.assertEqual(self.releases, ["UNLOADED"])
        self.assertEqual(tuple(x-y for x,y in zip(self.counts(), before)), (1,1))
        self.assertEqual(self.r.store.one(
            "SELECT status FROM messages WHERE id=?",
            (r["draft_message_id"],))["status"], "DRAFT")
        self.assertEqual(r["delivery_authority"], 0)
        self.assertFalse(r["output_committed"])
        self.assertEqual(r["learning_authority"], 0)

    def test_future_correction_cannot_answer_earlier_user_event(self):
        current = self.current()
        self.correction()
        before = self.counts()
        r = self.stage(current)
        self.assertEqual(r["status"], "TEMPORAL_SOURCE_RED")
        self.assertFalse(r["model_called"])
        self.assertEqual(self.roles, [])
        self.assertEqual(self.counts(), before)

    def test_later_replacement_correction_cannot_rewrite_earlier_query(self):
        self.correction()
        current = self.current()
        self.correction(value="73 Euro")
        before = self.counts()
        r = self.stage(current)
        self.assertEqual(r["status"], "TEMPORAL_SOURCE_RED")
        self.assertEqual(self.roles, [])
        self.assertEqual(self.counts(), before)

    def test_duplicated_user_message_refused_before_model(self):
        self.correction()
        current = self.current()
        self.r.store.message(self.r.session, current["event_id"],
                             "user", self.f["followup"], "FINAL")
        before = self.counts()
        self.assertEqual(self.stage(current)["status"], "USER_MESSAGE_LINEAGE_RED")
        self.assertEqual(self.roles, [])
        self.assertEqual(self.counts(), before)

    def test_learn_permission_not_record_refused(self):
        self.correction(permission="learn")
        current = self.current()
        before = self.counts()
        self.assertEqual(self.stage(current)["status"], "FEEDBACK_LINEAGE_RED")
        self.assertEqual(self.roles, [])
        self.assertEqual(self.counts(), before)

    def test_off_missing_correction_and_bad_token_budget_no_model(self):
        current = self.current()
        before = self.counts()
        self.assertEqual(self.stage(current, opt=False)["status"], "OFF")
        self.assertEqual(self.stage(current, model_opt=False)["status"], "OFF")
        self.assertEqual(self.stage(current, tokens=0)["status"], "INVALID_OR_EXPIRED_INPUT")
        self.assertEqual(self.stage(current)["status"], "CLARIFY")
        self.assertEqual(self.roles, [])
        self.assertEqual(self.counts(), before)

    def test_foreign_session_and_deleted_current_source_refused(self):
        self.correction()
        current = self.current()
        original_session = self.r.session
        self.r.session = self.r.store.new_session("foreign")
        self.assertEqual(self.stage(current)["status"], "EVENT_OR_SOURCE_RED")
        self.r.session = original_session
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (current["source_ref"]["source_id"],))
        self.assertEqual(self.stage(current)["status"], "EVENT_OR_SOURCE_RED")
        self.assertEqual(self.roles, [])


if __name__ == "__main__":
    unittest.main()
