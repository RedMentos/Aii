"""Run13S real Store->JEF->C3 source-revalidated SHADOW preview, no native calls."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_context_source_link_budget_run13e import prepare
from v13.agi.jef_c3_shadow_prompt_run13i import propose_c3_context
from v13.agi import jef_c3_revalidated_preview_run13s as p
from v13.runtime import Runtime


class Run13SRevalidatedPreview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.source, self.query, self.plan, _ = prepare(self.r)
        self.pid = self.plan["packet_id"]
        self.linked = propose_c3_context(
            self.r.store, self.pid, self.query, self.source)
        self.assertEqual(self.linked["reason"],
                         "VERIFIED_JEF_TO_C3_SHADOW_CANDIDATE")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def preview(self, candidate, **changes):
        kw = {"native_status": "FINAL", "native_reaped": True,
              "native_role": "C3_LANGUAGE", "native_calls": 1}
        kw.update(changes)
        return p.preview_after_native(
            self.r.store, self.pid, self.query, self.source,
            self.linked, candidate, **kw)

    def assert_guard(self, result):
        self.assertEqual(result["status"], "SHADOW_NO_AUTHORITY")
        self.assertTrue(result["operator_only"])
        self.assertTrue(result["no_autonomous_egress"])
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(result["context_authority"], 0)
        self.assertFalse(result["weight_updates"])
        self.assertFalse(result["model_called_by_preview"])
        self.assertEqual(result["learning_mode"], "RECORD_ONLY")
        self.assertEqual(result["step2_status"], "UTILITY_FAIL")
        self.assertEqual(result["b3_status"], "NO_PROMOTION")
        self.assertEqual(result["body_jepa_status"], "UNAVAILABLE")
        self.assertEqual(result["jepa_weight"], 0)
        self.assertFalse(result["whole_system_complete"])

    def test_real_store_exact_native_preview_no_autonomous_writes(self):
        before = (
            self.r.store.one("SELECT count(*) AS n FROM sources")["n"],
            self.r.store.one("SELECT count(*) AS n FROM messages")["n"])
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_CALLED")):
            result = self.preview(self.linked["answer"])
        self.assert_guard(result)
        self.assertEqual(result["reason"], "MODEL_VERIFIED_PREVIEW")
        self.assertEqual(result["preview_text"], self.linked["answer"])
        self.assertEqual(result["preview_origin"], "NATIVE_C3_FACTS_VERIFIED")
        self.assertTrue(result["model_facts_verified"])
        self.assertFalse(result["deterministic_fallback_used"])
        self.assertEqual(result["native_calls_observed"], 1)
        after = (
            self.r.store.one("SELECT count(*) AS n FROM sources")["n"],
            self.r.store.one("SELECT count(*) AS n FROM messages")["n"])
        self.assertEqual(before, after)

    def test_wrong_fact_extra_claim_and_overlong_candidate_fallback(self):
        answer = self.linked["answer"]
        cases = (answer.replace("169 Euro", "170 Euro"),
                 answer + "\nExtra unverified claim.",
                 "irrelevant " * 150)
        for candidate in cases:
            with self.subTest(candidate=candidate[:32]):
                result = self.preview(candidate)
                self.assert_guard(result)
                self.assertEqual(result["reason"],
                                 "SOURCE_EXACT_FALLBACK_PREVIEW")
                self.assertEqual(result["preview_text"], answer)
                self.assertEqual(result["preview_origin"],
                                 "FRESH_JEF_SOURCE_EXACT")
                self.assertFalse(result["model_facts_verified"])
                self.assertTrue(result["deterministic_fallback_used"])

    def test_revoked_or_mutated_source_never_uses_stale_fallback(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id="
                       "(SELECT source_id FROM events WHERE id=?)",
                       (self.source,))
        result = self.preview("wrong")
        self.assert_guard(result)
        self.assertEqual(result["reason"], "ABSTAIN_SOURCE_RED")
        self.assertIsNone(result["preview_text"])

    def test_sqlite_fault_and_changed_second_witness_fail_closed(self):
        with patch.object(self.r.store, "one",
                          side_effect=sqlite3.OperationalError("DB unavailable")):
            result = self.preview("wrong")
        self.assertEqual(result["reason"], "ABSTAIN_SOURCE_RED")
        self.assertIsNone(result["preview_text"])
        bad = dict(self.linked, answer_sha256="0" * 64)
        with patch.object(p, "propose_c3_context", return_value=bad):
            result = self.preview("wrong")
        self.assertEqual(result["reason"], "ABSTAIN_SOURCE_RED")
        self.assertIsNone(result["preview_text"])

    def test_native_receipt_nonfinal_unreaped_wrong_role_nontext_and_unicode(self):
        cases = (
            ("wrong", {"native_status": "ERROR"}),
            ("wrong", {"native_reaped": False}),
            ("wrong", {"native_role": "B1_DETAIL"}),
            ("wrong", {"native_calls": 0}),
            (None, {}),
            ("\ud800", {}),
        )
        for candidate, changes in cases:
            with self.subTest(changes=changes, candidate=repr(candidate)):
                result = self.preview(candidate, **changes)
                self.assert_guard(result)
                self.assertEqual(result["reason"], "ABSTAIN_NATIVE_RED")
                self.assertIsNone(result["preview_text"])

    def test_wrong_plan_or_tampered_prior_witness_abstains(self):
        bad = dict(self.linked, prompt_sha256="0" * 64)
        with patch.object(p, "propose_c3_context",
                          side_effect=AssertionError("SHOULD_NOT_READ")):
            result = p.preview_after_native(
                self.r.store, self.pid, self.query, self.source,
                bad, "wrong", native_status="FINAL", native_reaped=True,
                native_role="C3_LANGUAGE", native_calls=1)
        self.assertEqual(result["reason"], "ABSTAIN_SOURCE_RED")
        self.assertIsNone(result["preview_text"])


if __name__ == "__main__":
    unittest.main()
