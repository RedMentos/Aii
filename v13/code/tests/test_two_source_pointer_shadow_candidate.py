"""Real SQLite/SourceRef adversarial tests; zero native/egress authority."""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.two_source_pointer_shadow_candidate import bind_two_source


class TwoSourcePointerCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name) / "home")
        self.prior = self.r.store.event(
            self.r.session, "Project Alder. Budget 200 euros. Deadline 6 days. Local only true.")
        self.current = self.r.store.event(
            self.r.session, "Project Alder. Option A costs 180 euros, takes 5 days. Option B costs 160 euros, takes 7 days.")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def read(self, prior=None, current=None, **kwargs):
        return bind_two_source(self.r, self.prior if prior is None else prior,
                               self.current if current is None else current, **kwargs)

    def test_default_off_has_zero_authority_and_no_sources(self):
        result = self.read()
        self.assertEqual(result["status"], "OFF")
        self.assertNotIn("sources", result)
        self.assertFalse(result["body_model_quote_verified"])
        self.assertEqual(result["native_calls"], 0)

    def test_exact_two_source_transport_is_not_body_quote_proof(self):
        before = self.r.store.db.total_changes
        result = self.read(operator_opt_in=True)
        self.assertEqual(result["status"], "SHADOW_TWO_SOURCE_POINTER_VERIFIED")
        self.assertEqual(result["project_scope"], "alder")
        self.assertEqual([s["lane"] for s in result["sources"]],
                         ["B2_PRIOR_USER_SOURCE", "B1_CURRENT_USER_SOURCE"])
        for entry, event in zip(result["sources"], (self.prior, self.current)):
            self.assertEqual(entry["source_ref"], event["source_ref"])
            self.assertEqual(entry["text"], self.r.store.read_source(event["source_ref"]))
            self.assertEqual(entry["origin"], "STORE_EXACT_USER_NOT_MODEL_QUOTE")
        self.assertEqual(self.r.store.db.total_changes, before)
        for key in ("body_model_quote_verified", "body_model_called", "jef_model_called",
                    "output_committed", "source_semantic_truth_authority"):
            self.assertIs(result[key], False)
        for key in ("native_calls", "tool_dispatches", "learning_authority",
                    "delivery_authority", "jepa_weight"):
            self.assertEqual(result[key], 0)
        self.assertEqual(result["step2_exit"], "EVIDENCE_NOT_PASSING")

    def test_stale_authoritative_user_correction_refuses(self):
        self.r.store.event(self.r.session, "Project Alder. Cancel all options now.")
        self.assertEqual(self.read(operator_opt_in=True)["status"], "SOURCE_POINTER_REFUSED_RED")

    def test_cross_project_and_generic_scope_refuse(self):
        other = self.r.store.event(self.r.session, "Project Birch. Option C costs 10 euros.")
        self.assertEqual(self.read(current=other, operator_opt_in=True)["status"],
                         "SOURCE_POINTER_REFUSED_RED")
        self.r.store.event(self.r.session, "Apply the earlier project rules.")
        generic = self.r.store.event(self.r.session, "No explicit project name.")
        self.assertEqual(self.read(current=generic, operator_opt_in=True)["status"],
                         "SOURCE_POINTER_REFUSED_RED")

    def test_reversed_order_refuses(self):
        self.assertEqual(self.read(prior=self.current, current=self.prior,
                                   operator_opt_in=True)["status"], "SOURCE_POINTER_REFUSED_RED")

    def test_deleted_prior_source_refuses(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.prior["source_ref"]["source_id"],))
        self.assertEqual(self.read(operator_opt_in=True)["status"], "SOURCE_POINTER_REFUSED_RED")

    def test_tampered_source_ref_refuses(self):
        wrong = dict(self.current, source_ref=dict(self.current["source_ref"], sha256="0"*64))
        self.assertEqual(self.read(current=wrong, operator_opt_in=True)["status"],
                         "SOURCE_POINTER_REFUSED_RED")

    def test_foreign_session_refuses(self):
        self.r.session = self.r.store.new_session("foreign")
        self.assertEqual(self.read(operator_opt_in=True)["status"], "SOURCE_POINTER_REFUSED_RED")

    def test_user_message_status_tamper_refuses(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE messages SET status='ERROR' WHERE event_id=? AND role='user'",
                       (self.prior["event_id"],))
        self.assertEqual(self.read(operator_opt_in=True)["status"], "SOURCE_POINTER_REFUSED_RED")


if __name__ == "__main__":
    unittest.main()
