"""Run14K test-first: exact structured C3 slots must remain source-bound SHADOW."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run13l_c3_system_native as l
from scripts import run13j_c3_jef_native as j
from v13.agi import jef_c3_shadow_fallback_run13v as mux
from v13.agi.c3_source_fidelity_shadow_run13m import TRUSTED
from v13.runtime import Runtime

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run13l_c3_system_seed251_20261030.json"
SYSTEM = ("You are a strict data extraction engine. Return only one JSON object "
          "with six exact fields; no commentary or invented facts.")
PREFIX = ("Extract project, option_a, remaining_a, option_b, remaining_b, faster "
          "from these verified facts. Return JSON with exactly those six keys; "
          "amounts must be integers.\nVERIFIED_FACTS:\n")


class C3StructuredSourceShadow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.case = l.load_fixture(FIXTURE)[0]
        self.data = j.prepare_case(self.runtime, self.case)
        self.linked = self.data["linked"]
        self.ids = (self.data["plan_packet_id"], self.data["query_event_id"],
                    self.data["source_event_id"])
        m = TRUSTED.fullmatch(self.linked["answer"])
        self.assertIsNotNone(m)
        self.fields = {"project": m.group("project"), "option_a": m.group("a"),
                       "remaining_a": int(m.group("na")), "option_b": m.group("b"),
                       "remaining_b": int(m.group("nb")), "faster": m.group("faster")}

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def raw(self, fields=None):
        return json.dumps(self.fields if fields is None else fields, separators=(",", ":"), sort_keys=True)

    def receipt(self, output, *, prompt=None, system=None):
        return {"native_role": "C3_LANGUAGE", "native_status": "FINAL",
                "native_calls": 1, "native_reaped": True, "native_pid": 12345,
                "native_release": {"process_reaped": True},
                "model_sha256": mux.MODEL_SHA, "model_revision": mux.MODEL_REVISION,
                "source_event_id": self.ids[2], "query_event_id": self.ids[1],
                "context_plan_packet_id": self.ids[0],
                "answer_sha256": self.linked["answer_sha256"],
                "prompt_sha256": mux._sha(PREFIX + self.linked["answer"]) if prompt is None else prompt,
                "system_sha256": mux._sha(SYSTEM) if system is None else system,
                "native_output_sha256": mux._sha(output),
                "native_output_bytes": len(output.encode("utf-8"))}

    def select(self, output, receipt=None):
        return mux.select_shadow(self.runtime.store, *self.ids, self.linked,
                                 c3_text=output, native_receipt=receipt)

    def assert_shadow(self, result):
        self.assertEqual(result["status"], "SHADOW_NO_AUTHORITY")
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(result["context_authority"], 0)
        self.assertEqual(result["native_calls_by_mux"], 0)
        self.assertFalse(result["model_called_by_mux"])
        self.assertEqual(result["store_writes_by_mux"], 0)
        self.assertFalse(result["weight_updates"])
        self.assertEqual(result["learning_mode"], "RECORD_ONLY")
        self.assertEqual(result["step2_status"], "UTILITY_FAIL")
        self.assertFalse(result["utility_gate_pass"])
        self.assertFalse(result["whole_system_complete"])

    def test_exact_six_slots_select_only_trusted_jef_answer_with_valid_receipt(self):
        raw = self.raw()
        before = (self.runtime.store.one("SELECT count(*) n FROM messages")["n"],
                  self.runtime.store.one("SELECT count(*) n FROM sources")["n"])
        with patch.object(self.runtime.pool, "get", side_effect=AssertionError("NATIVE_CALLED")):
            result = self.select(raw, self.receipt(raw))
        self.assert_shadow(result)
        self.assertEqual(result["selected_provenance"], "C3_STRUCTURED_FACTS_VERIFIED_SHADOW")
        self.assertEqual(result["selected_text"], self.linked["answer"])
        self.assertEqual(result["selected_text_sha256"], self.linked["answer_sha256"])
        self.assertTrue(result["source_revalidated"])
        self.assertTrue(result["native_receipt_bound"])
        self.assertEqual(before, (self.runtime.store.one("SELECT count(*) n FROM messages")["n"],
                                  self.runtime.store.one("SELECT count(*) n FROM sources")["n"]))

    def test_prompt_is_deterministic_source_bound_and_bounded(self):
        from v13.agi.c3_structured_source_shadow_run14k import prompt_for
        system, user = prompt_for(self.linked)
        self.assertEqual((system, user), (SYSTEM, PREFIX + self.linked["answer"]))
        self.assertLessEqual(len(user.encode("utf-8")), 1200)

    def test_wrong_or_ambiguous_json_always_falls_back_to_verified_jef(self):
        variants = [
            dict(self.fields, remaining_a=self.fields["remaining_a"] + 1),
            dict(self.fields, faster=self.fields["option_b"] if self.fields["faster"] == self.fields["option_a"] else self.fields["option_a"]),
            dict(self.fields, project="OtherProject"),
            dict(self.fields, remaining_a=True),
            dict(self.fields, extra="claim"),
        ]
        invalid = [self.raw(v) for v in variants]
        invalid += [self.raw() + " explanation",
                    "~~~json\n" + self.raw() + "\n~~~",
                    self.raw().replace('"option_a":', '"option_a":"WRONG","option_a":', 1),
                    "[]", "null", "", "X" * 800]
        for raw in invalid:
            with self.subTest(raw=raw[:45]):
                result = self.select(raw, self.receipt(raw) if raw else None)
                self.assert_shadow(result)
                self.assertEqual(result["selected_provenance"], "JEF_VERIFIED_FALLBACK_SHADOW")
                self.assertEqual(result["selected_text"], self.linked["answer"])

    def test_wrong_model_system_prompt_or_output_receipt_never_selects_c3(self):
        raw = self.raw()
        receipt = self.receipt(raw)
        variants = [
            dict(receipt, model_sha256="0" * 64),
            dict(receipt, prompt_sha256="0" * 64),
            dict(receipt, system_sha256="0" * 64),
            dict(receipt, native_output_sha256="0" * 64),
            dict(receipt, native_pid=True),
        ]
        for bad in variants:
            with self.subTest(bad=next(k for k in bad if bad[k] != receipt[k])):
                result = self.select(raw, bad)
                self.assert_shadow(result)
                self.assertEqual(result["selected_provenance"], "JEF_VERIFIED_FALLBACK_SHADOW")

    def test_revoked_source_abstains_even_with_structured_native_receipt(self):
        raw = self.raw()
        with self.runtime.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id="
                       "(SELECT source_id FROM events WHERE id=?)", (self.ids[2],))
        result = self.select(raw, self.receipt(raw))
        self.assert_shadow(result)
        self.assertIsNone(result["selected_text"])
        self.assertEqual(result["selected_provenance"], "NONE")


if __name__ == "__main__":
    unittest.main()
