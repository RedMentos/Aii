"""Real SQLite F1/F5 temporal-order atomic C5 DRAFT adversarial tests."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.config import DEFAULTS, initialize
from v13.store import Store
from v13.memory import Memory
from v13 import f1f5_temporal_atomic_draft_candidate as atomic
from scripts.run51_f1f5_second_attempt_native import load_fixture

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run51_f1f5_second_attempt_seed467.json"


class TemporalAtomicDraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.memory = Memory(self.store, DEFAULTS)
        self.f = load_fixture(FIXTURE)["fixtures"][0]
        self.calls = 0

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def correction(self, value=None):
        e = self.store.event(self.session, self.f["correction_event"])
        return self.memory.feedback(
            e["event_id"], "fact", value or self.f["value"],
            permission="record", key=self.f["key"], scope="session")

    def current(self):
        return self.store.event(self.session, self.f["followup"])

    def callback(self, messages):
        self.calls += 1
        return "Project Cypress budget is 64 Euro."

    def stage(self, event, callback=None, opt=True):
        return atomic.stage_temporal_atomic_draft(
            DEFAULTS, self.memory, self.session, event["event_id"],
            self.callback if callback is None else callback,
            operator_opt_in=opt)

    def counts(self):
        return (
            self.store.one("SELECT COUNT(*) AS n FROM packets "
                           "WHERE kind IN ('ActionIntent','CorollaryCopy')")["n"],
            self.store.one("SELECT COUNT(*) AS n FROM actions")["n"],
            self.store.one("SELECT COUNT(*) AS n FROM messages "
                           "WHERE role='assistant'")["n"])

    def test_prior_correction_stages_four_objects_atomically(self):
        self.correction()
        current = self.current()
        before = self.counts()
        r = self.stage(current)
        self.assertEqual(r["status"], "TEMPORAL_ATOMIC_DRAFT_STAGED_SHADOW_NO_COMMIT")
        self.assertEqual(tuple(x-y for x,y in zip(self.counts(), before)), (2,1,1))
        self.assertEqual(self.calls, 1)
        self.assertTrue(r["temporal_source_verified"])
        self.assertEqual(r["delivery_authority"], 0)
        self.assertFalse(r["output_committed"])
        self.assertEqual(r["learning_authority"], 0)
        self.assertEqual(self.store.one(
            "SELECT status FROM messages WHERE id=?",
            (r["draft_message_id"],))["status"], "DRAFT")
        checked = atomic.check_temporal_staged_draft(
            DEFAULTS, self.memory, self.session, current["event_id"], r)
        self.assertEqual(checked["status"],
                         "TEMPORAL_ATOMIC_DRAFT_BOUND_SHADOW_NO_COMMIT")

    def test_future_correction_abstains_before_callback_or_staging(self):
        current = self.current()
        self.correction()
        before = self.counts()
        self.assertEqual(self.stage(current)["status"], "TEMPORAL_SOURCE_RED")
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.counts(), before)

    def test_active_replacement_during_callback_rolls_back_draft(self):
        self.correction()
        current = self.current()
        before = self.counts()
        def replace(messages):
            self.calls += 1
            self.correction("73 Euro")
            return "Project Cypress budget is 64 Euro."
        r = self.stage(current, callback=replace)
        self.assertEqual(r["status"], "SOURCE_CHANGED_BEFORE_DRAFT")
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.counts(), before)

    def test_revocation_during_callback_rolls_back_draft(self):
        mid = self.correction()
        current = self.current()
        before = self.counts()
        def revoke(messages):
            self.calls += 1
            self.memory.forget(mid)
            return "Project Cypress budget is 64 Euro."
        self.assertEqual(self.stage(current, callback=revoke)["status"],
                         "SOURCE_CHANGED_BEFORE_DRAFT")
        self.assertEqual(self.counts(), before)

    def test_sql_second_packet_failure_rolls_back_all_four_objects(self):
        self.correction()
        current = self.current()
        before = self.counts()
        original = atomic.dumps
        calls = [0]
        def fail_second(value):
            calls[0] += 1
            if calls[0] == 2:
                raise RuntimeError("synthetic second packet write failure")
            return original(value)
        with patch.object(atomic, "dumps", side_effect=fail_second):
            r = self.stage(current)
        self.assertEqual(r["status"], "STORE_OR_BINDING_RED")
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.calls, 1)

    def test_duplicate_user_event_lineage_refused(self):
        self.correction()
        current = self.current()
        self.store.message(self.session, current["event_id"],
                           "user", self.f["followup"], "FINAL")
        before = self.counts()
        self.assertEqual(self.stage(current)["status"], "USER_MESSAGE_LINEAGE_RED")
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.calls, 0)

    def test_poststage_revocation_never_approves_draft(self):
        mid = self.correction()
        current = self.current()
        r = self.stage(current)
        self.memory.forget(mid)
        checked = atomic.check_temporal_staged_draft(
            DEFAULTS, self.memory, self.session, current["event_id"], r)
        self.assertNotEqual(checked["status"],
                            "TEMPORAL_ATOMIC_DRAFT_BOUND_SHADOW_NO_COMMIT")
        self.assertEqual(checked["delivery_authority"], 0)

    def test_restart_interrupts_staged_draft(self):
        self.correction()
        current = self.current()
        r = self.stage(current)
        self.store.close()
        self.store = Store(self.home)
        self.memory = Memory(self.store, DEFAULTS)
        self.assertEqual(self.store.one(
            "SELECT status FROM messages WHERE id=?",
            (r["draft_message_id"],))["status"], "INTERRUPTED")
        self.assertNotEqual(atomic.check_temporal_staged_draft(
            DEFAULTS, self.memory, self.session, current["event_id"], r)["status"],
            "TEMPORAL_ATOMIC_DRAFT_BOUND_SHADOW_NO_COMMIT")

    def test_off_missing_source_and_invalid_callback_never_stage(self):
        current = self.current()
        before = self.counts()
        self.assertEqual(self.stage(current, opt=False)["status"], "OFF")
        self.assertEqual(self.stage(current)["status"], "CLARIFY")
        self.assertEqual(self.stage(current, callback=42)["status"], "INVALID_CALLBACK")
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.calls, 0)


if __name__ == "__main__":
    unittest.main()
