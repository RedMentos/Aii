"""Run13I actual Context OS -> JEF exact source -> C3 SHADOW prompt bridge."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tests.test_context_source_link_budget_run13e import prepare
from v13.agi.context_source_link_budget_run13e import propose_pointer
from v13.agi import jef_c3_shadow_prompt_run13i as bridge
from v13.runtime import Runtime


class Run13IJefC3Shadow(unittest.TestCase):
    def _assert_no_authority(self, got):
        self.assertEqual(got["status"], "SHADOW_NO_AUTHORITY")
        self.assertEqual(got["consumer_role"], "C3_LANGUAGE")
        self.assertEqual(got["delivery_authority"], 0)
        self.assertEqual(got["context_authority"], 0)
        self.assertEqual(got["native_calls"], 0)
        self.assertFalse(got["model_called"])
        self.assertFalse(got["weight_updates"])
        self.assertEqual(got["learning_mode"], "RECORD_ONLY")
        self.assertEqual(got["step2_status"], "UTILITY_FAIL")
        self.assertEqual(got["b3_status"], "NO_PROMOTION")
        self.assertEqual(got["jepa_weight"], 0)
        self.assertFalse(got["whole_system_complete"])

    def test_actual_source_link_becomes_bounded_c3_candidate_without_native_or_writes(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                source, query, plan, _ = prepare(runtime)
                store = runtime.store
                before = store.one("SELECT count(*) AS n FROM sources")["n"]
                messages = store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
                with patch.object(runtime.pool, "get",
                                  side_effect=AssertionError("NATIVE_CALLED")):
                    got = bridge.propose_c3_context(
                        store, plan["packet_id"], query, source)
                self._assert_no_authority(got)
                self.assertEqual(got["reason"], "VERIFIED_JEF_TO_C3_SHADOW_CANDIDATE")
                self.assertEqual(got["context_plan_packet_id"], plan["packet_id"])
                self.assertIn("Cedar leaves 169 Euro remaining.", got["answer"])
                self.assertIn("Quartz leaves 58 Euro remaining.", got["answer"])
                self.assertIn("Quartz finishes sooner.", got["answer"])
                self.assertTrue(got["candidate_prompt"].startswith(bridge.PREFIX))
                self.assertIn(got["answer"], got["candidate_prompt"])
                self.assertNotIn("Everything stays local", got["candidate_prompt"])
                self.assertLessEqual(len(got["candidate_prompt"].encode()),
                                     bridge.MAX_PROMPT_BYTES)
                self.assertEqual(bridge._digest(got["answer"]), got["answer_sha256"])
                self.assertEqual(bridge._digest(got["candidate_prompt"]),
                                 got["prompt_sha256"])
                self.assertEqual(before, store.one(
                    "SELECT count(*) AS n FROM sources")["n"])
                self.assertEqual(messages, store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"])
                self.assertEqual(bridge.audit_c3_text(got, got["answer"])["status"],
                                 "EXACT_COPY")
                self.assertEqual(bridge.audit_c3_text(
                    got, got["answer"] + " Extra claim.")["status"], "NOT_VERIFIED")
            finally:
                runtime.close()

    def test_wrong_plan_cross_session_and_revoked_source_abstain(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                source, query, plan, _ = prepare(runtime)
                got = bridge.propose_c3_context(
                    runtime.store, "bad-packet", query, source)
                self._assert_no_authority(got)
                self.assertIsNone(got["candidate_prompt"])
                with runtime.store.tx() as db:
                    db.execute("UPDATE sources SET deleted=1 WHERE id="
                               "(SELECT source_id FROM events WHERE id=?)",
                               (source,))
                got = bridge.propose_c3_context(
                    runtime.store, plan["packet_id"], query, source)
                self._assert_no_authority(got)
                self.assertIsNone(got["answer"])
            finally:
                runtime.close()
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                source, query, plan, _ = prepare(runtime, foreign_source=True)
                got = bridge.propose_c3_context(
                    runtime.store, plan["packet_id"], query, source)
                self._assert_no_authority(got)
                self.assertIsNone(got["candidate_prompt"])
            finally:
                runtime.close()

    def test_duplicate_source_pointer_abstains(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                source, query, plan, _ = prepare(runtime)
                payload = dict(plan["plan"])
                pointer = next(x for x in payload["items"]
                               if x.get("item_id") == source)
                payload["items"] = list(payload["items"]) + [dict(pointer)]
                with runtime.store.tx() as db:
                    db.execute("UPDATE packets SET payload=? WHERE id=?",
                               (json.dumps(payload), plan["packet_id"]))
                got = bridge.propose_c3_context(
                    runtime.store, plan["packet_id"], query, source)
                self._assert_no_authority(got)
                self.assertIsNone(got["candidate_prompt"])
            finally:
                runtime.close()

    def test_second_witness_mismatch_never_returns_prompt(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                source, query, plan, _ = prepare(runtime)
                first = propose_pointer(
                    runtime.store, plan["packet_id"], query, source)
                self.assertIsNotNone(first["answer"])
                changed = dict(first, answer_sha256="0" * 64)
                with patch.object(bridge, "propose_pointer",
                                  side_effect=[first, changed]):
                    got = bridge.propose_c3_context(
                        runtime.store, plan["packet_id"], query, source)
                self._assert_no_authority(got)
                self.assertEqual(got["reason"], "SOURCE_CHANGED_BEFORE_C3_SHADOW")
                self.assertIsNone(got["candidate_prompt"])
            finally:
                runtime.close()

    def test_auditor_rejects_tampered_context_and_never_grants_authority(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                source, query, plan, _ = prepare(runtime)
                got = bridge.propose_c3_context(
                    runtime.store, plan["packet_id"], query, source)
                self.assertIsNotNone(got["answer"])
                for bad in (
                    dict(got, prompt_sha256="f" * 64),
                    dict(got, delivery_authority=1),
                    dict(got, answer=got["answer"] + " altered"),
                    dict(got, model_called=True),
                ):
                    with self.subTest(bad=tuple(set(bad.items()) - set(got.items()))):
                        audited = bridge.audit_c3_text(bad, got["answer"])
                        self.assertEqual(audited["status"], "INTEGRITY_RED")
                        self.assertEqual(audited["delivery_authority"], 0)
                self.assertEqual(bridge.audit_c3_text(got, None)["status"],
                                 "INTEGRITY_RED")
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
