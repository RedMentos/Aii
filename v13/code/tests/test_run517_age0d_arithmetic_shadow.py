"""Run517: live SHA-bound Run134 Age0d arithmetic SHADOW hook, no models."""
import tempfile
import unittest
from pathlib import Path

from v13 import age as agectl
from v13 import neuromod as N
from v13 import selfmodel as S
from v13.agi.answer_arithmetic_shadow import evaluate
from v13.runtime import Runtime


class ExistingRun134NotReimplemented(unittest.TestCase):
    def test_existing_answer_visible_evaluator(self):
        self.assertEqual(evaluate("Compute 2 plus 2.", "4")["status"], "CORRECT")
        self.assertEqual(evaluate("Compute 2 plus 2.", "5")["status"], "MISMATCH")
        self.assertEqual(evaluate("Compute 2 plus 2.", "I don't know")["status"],
                         "ABSTAIN")
        self.assertFalse(evaluate("Compute 2 plus 2.", "5")["may_deliver"])


class LiveShadowIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.r = Runtime(Path(self.tmp.name))
        self.addCleanup(self.r.close)
        self.system = S.SelfSystem(self.r, agectl.controller(self.r),
                                   N.Neuromod(self.r.store),
                                   clock=lambda: 1000.)
        self.event = self.r.store.event(self.r.session, "Compute 2 plus 2.")
        self.offer = {
            "role": "B2_GIST", "event_id": self.event["event_id"],
            "offer": {"summary": "", "needs_reentry": False},
            "evidence_refs": [],
        }

    def ring(self):
        return self.r.store.state(S.ARITH_SHADOW_KEY, [])[0]

    def commit(self, text, status="FINAL", session=None, event_id=None):
        mid = self.r.store.message(
            session or self.r.session, event_id or self.event["event_id"],
            "assistant")
        self.r.store.append_message(mid, text)
        self.r.store.finish_message(mid, status, {"model_generated": False})
        return mid

    def test_wrong_answer_source_verified_and_shadow_only(self):
        said = []
        self.r.notice = said.append
        self.commit("5")
        result = self.system.late_offer(self.event["event_id"], self.offer, "5")
        self.assertIsNone(result)
        rows = self.ring()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "MISMATCH_SHADOW_ONLY")
        self.assertEqual((rows[0]["expected"], rows[0]["claimed"]), ("4", "5"))
        self.assertFalse(rows[0]["user_notified"])
        self.assertFalse(rows[0]["learning_authorized"])
        self.assertFalse(rows[0]["age_reopen_authorized"])
        self.assertEqual(said, [])
        self.assertNotIn("Compute 2 plus 2.", str(rows))

    def test_correct_and_ambiguous_answer_do_not_trigger(self):
        self.commit("4")
        self.system.late_offer(self.event["event_id"], self.offer, "4")
        self.commit("Maybe 4 or 5")
        self.system.late_offer(self.event["event_id"], self.offer, "Maybe 4 or 5")
        self.assertEqual(self.ring(), [])

    def test_repeated_late_offer_deduplicated(self):
        self.commit("5")
        for _ in range(3):
            self.system.late_offer(self.event["event_id"], self.offer, "5")
        self.assertEqual(len(self.ring()), 1)

    def test_missing_event_and_forged_offer_event_id_abstain(self):
        self.system.late_offer("nonexistent", self.offer, "5")
        self.assertEqual(self.ring(), [])
        forged = dict(self.offer, event_id="another-event")
        self.system.late_offer(self.event["event_id"], forged, "5")
        self.assertEqual(self.ring(), [])

    def test_tampered_source_blob_abstains(self):
        self.commit("5")
        ref = self.event["source_ref"]
        blob = Path(self.tmp.name) / "data" / "blobs" / ref["sha256"]
        blob.write_text("tampered source", encoding="utf-8")
        self.system.late_offer(self.event["event_id"], self.offer, "5")
        self.assertEqual(self.ring(), [])

    def test_cross_session_event_abstains(self):
        other = self.r.store.new_session()
        event = self.r.store.event(other, "Compute 3 plus 3.")
        offer = dict(self.offer, event_id=event["event_id"])
        self.commit("7", session=other, event_id=event["event_id"])
        self.system.late_offer(event["event_id"], offer, "7")
        self.assertEqual(self.ring(), [])

    def test_forged_output_not_equal_to_final_message_abstains(self):
        self.commit("4")
        self.system.late_offer(self.event["event_id"], self.offer, "5")
        self.assertEqual(self.ring(), [])

    def test_missing_draft_streaming_and_cancelled_message_abstain(self):
        self.system.late_offer(self.event["event_id"], self.offer, "5")
        self.assertEqual(self.ring(), [])
        mid = self.r.store.message(
            self.r.session, self.event["event_id"], "assistant")
        self.system.late_offer(self.event["event_id"], self.offer, "5")
        self.assertEqual(self.ring(), [])
        self.r.store.append_message(mid, "5")
        self.system.late_offer(self.event["event_id"], self.offer, "5")
        self.assertEqual(self.ring(), [])
        self.r.store.finish_message(mid, "CANCELLED", {})
        self.system.late_offer(self.event["event_id"], self.offer, "5")
        self.assertEqual(self.ring(), [])

    def test_latest_nonfinal_message_blocks_stale_final_fallback(self):
        self.commit("5")
        self.r.store.message(self.r.session, self.event["event_id"], "assistant")
        self.system.late_offer(self.event["event_id"], self.offer, "5")
        self.assertEqual(self.ring(), [])

    def test_committed_mismatch_ring_persists_after_runtime_restart(self):
        self.commit("5")
        self.system.late_offer(self.event["event_id"], self.offer, "5")
        self.assertEqual(len(self.ring()), 1)
        other = Runtime(Path(self.tmp.name))
        try:
            self.assertEqual(other.store.state(S.ARITH_SHADOW_KEY, [])[0], self.ring())
        finally:
            other.close()

    def test_off_and_deliver_do_not_add_new_diagnostic(self):
        self.commit("5")
        said = []
        self.r.notice = said.append
        for mode in ("off", "deliver"):
            self.system.set_correction_mode(mode)
            self.system.late_offer(self.event["event_id"], self.offer, "5")
        self.assertEqual(self.ring(), [])
        self.assertEqual(said, [])


if __name__ == "__main__":
    unittest.main()
