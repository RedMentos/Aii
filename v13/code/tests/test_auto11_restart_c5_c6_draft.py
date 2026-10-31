"""Real Store close/reopen C6 persisted provenance tests, no native calls."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from tests.test_run82_jef_b1b2_c3_dual_source import DualSourceEnvelopeTests
from v13 import jef_b1b2_c3_c5c6_draft_shadow as bridge
from v13 import jef_b1b2_c3_c5c6_restart_preflight_shadow as replay
from v13.common import dumps


class RestartDraftTests(unittest.TestCase):
    setUp = DualSourceEnvelopeTests.setUp
    tearDown = DualSourceEnvelopeTests.tearDown

    def stage(self):
        calls = [0]

        def callback(messages, schema):
            calls[0] += 1
            action = json.loads(messages[1]["content"])["typed_jef_action"]
            return dumps({"action": action})
        r = bridge.evaluate(
            self.r, self.event, self.offers, self.ids, callback,
            operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(r["status"], bridge.STATUS, r)
        self.assertEqual(calls, [1])
        self.assertTrue(r["callback_output_json_persisted"])
        return r

    def reopen(self):
        session = self.r.session
        self.r.close()
        self.r = FakeRuntime(Path(self.tmp.name))
        self.r.cfg.update(OVERRIDES)
        self.r.session = session

    def check(self, staged, *, opt=True, receipt=None):
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NO_NATIVE_REPLAY")):
            return replay.preflight(
                self.r, self.event, self.offers, self.ids,
                staged["draft_message_id"], staged["c5_action_id"],
                operator_opt_in=opt, approval_receipt=receipt)

    def mutate_meta(self, staged, change):
        row = self.r.store.one(
            "SELECT metadata FROM messages WHERE id=?",
            (staged["draft_message_id"],))
        meta = json.loads(row["metadata"])
        change(meta)
        self.r.store.db.execute(
            "UPDATE messages SET metadata=? WHERE id=?",
            (dumps(meta), staged["draft_message_id"]))
        self.r.store.db.commit()

    def test_real_store_restart_replays_exact_callback_without_model(self):
        staged = self.stage()
        self.reopen()
        r = self.check(staged)
        self.assertEqual(r["status"], replay.STATUS, r)
        self.assertTrue(r["callback_json_digest_replayed"])
        self.assertTrue(r["c6_preflight_only"])
        self.assertFalse(r["real_tty_approved"])
        self.assertFalse(r["output_committed"])
        self.assertFalse(r["callback_invoked"])
        self.assertFalse(r["native_proof"])
        self.assertEqual(self.r.store.one(
            "SELECT status FROM actions WHERE id=?",
            (staged["c5_action_id"],))["status"], "SHADOW_DRAFT")

    def test_restart_off_and_fake_tty_denied(self):
        staged = self.stage()
        self.reopen()
        self.assertEqual(self.check(staged, opt=False)["status"], "OFF")
        self.assertEqual(self.check(staged, opt=1)["status"], "OFF")
        self.assertEqual(self.check(staged, receipt={"approved": True})[
            "status"], "REAL_TTY_APPROVAL_UNSUPPORTED")

    def test_tampered_callback_json_without_hash_change_rejected(self):
        staged = self.stage()
        self.reopen()
        self.mutate_meta(staged, lambda m: m.update(
            callback_output_json='{"action":"B"}'))
        self.assertEqual(self.check(staged)["status"],
                         "CALLBACK_OUTPUT_REPLAY_RED")

    def test_forged_hash_with_wrong_callback_action_rejected(self):
        staged = self.stage()
        self.reopen()
        def forge(m):
            raw = '{"action":"B"}'
            m["callback_output_json"] = raw
            m["callback_output_sha256"] = hashlib.sha256(
                raw.encode()).hexdigest()
        self.mutate_meta(staged, forge)
        self.assertEqual(self.check(staged)["status"],
                         "CALLBACK_OUTPUT_REPLAY_RED")

    def test_duplicate_json_key_with_matching_hash_rejected(self):
        staged = self.stage()
        self.reopen()
        def forge(m):
            raw = '{"action":"A","action":"A"}'
            m["callback_output_json"] = raw
            m["callback_output_sha256"] = hashlib.sha256(
                raw.encode()).hexdigest()
        self.mutate_meta(staged, forge)
        self.assertEqual(self.check(staged)["status"],
                         "CALLBACK_OUTPUT_REPLAY_RED")

    def test_extra_metadata_key_rejected(self):
        staged = self.stage()
        self.reopen()
        self.mutate_meta(staged, lambda m: m.update(user_approved=True))
        self.assertEqual(self.check(staged)["status"],
                         "DRAFT_METADATA_SHAPE_RED")

    def test_newer_user_after_restart_denies(self):
        staged = self.stage()
        self.reopen()
        self.r.store.event(self.r.session, "newer user request")
        self.assertEqual(self.check(staged)["status"],
                         "SOURCE_CHANGED_AFTER_RESTART")

    def test_human_memory_forget_after_restart_denies(self):
        staged = self.stage()
        self.reopen()
        self.r.memory.forget(self.ids[0])
        self.assertEqual(self.check(staged)["status"],
                         "SOURCE_CHANGED_AFTER_RESTART")

    def test_action_promoted_to_dispatched_after_restart_denies(self):
        staged = self.stage()
        self.reopen()
        self.r.store.db.execute(
            "UPDATE actions SET status='DISPATCHED' WHERE id=?",
            (staged["c5_action_id"],))
        self.r.store.db.commit()
        self.assertEqual(self.check(staged)["status"],
                         "C5_F3_OR_DRAFT_BINDING_RED")

    def test_missing_draft_after_restart_denies(self):
        staged = self.stage()
        self.reopen()
        self.r.store.db.execute(
            "DELETE FROM messages WHERE id=?", (staged["draft_message_id"],))
        self.r.store.db.commit()
        self.assertEqual(self.check(staged)["status"], "DRAFT_MISSING")

    def test_wrong_session_after_restart_denies(self):
        staged = self.stage()
        self.reopen()
        self.r.session = self.r.store.new_session()
        self.assertEqual(self.check(staged)["status"],
                         "SOURCE_CHANGED_AFTER_RESTART")


if __name__ == "__main__":
    unittest.main()
