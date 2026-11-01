"""Run117CU pinned model-swap real-Store C3 source-only preflight, no native."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117cu_qwen_c3_source_only_preflight as C
from v13.runtime import Runtime


class NoNativeRuntime(Runtime):
    def __init__(self, home):
        super().__init__(home)
        def forbid(*args, **kwargs):
            raise AssertionError("NATIVE_MODEL_CALL_FORBIDDEN")
        self.pool.get = forbid


class C3ModelSwapPreflight(unittest.TestCase):
    def test_exact_model_pins_and_licenses(self):
        models = C.pinned_models()
        self.assertEqual([m["id"] for m in models],
                         ["lfm25_350m", "qwen35_0p8b"])
        self.assertEqual([m["size"] for m in models],
                         [219312832, 563036064])
        self.assertEqual([m["license_id"] for m in models],
                         ["LFM Open License 1.0", "Apache-2.0"])
        self.assertEqual(models[1]["sha256"],
                         "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf")

    def test_model_hash_change_or_missing_spec_fails_closed(self):
        original = json.loads(C.SPEC_PATH.read_text())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "spec.json"
            bad = json.loads(json.dumps(original))
            next(x for x in bad["candidates"] if x["id"] == "qwen35_0p8b")["sha256"] = "0" * 64
            path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError, "MODEL_SPEC_CHANGED_RED"):
                C.pinned_models(path)
            bad["candidates"] = [x for x in bad["candidates"]
                                 if x["id"] != "qwen35_0p8b"]
            path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError, "MODEL_SPEC_MISSING_RED"):
                C.pinned_models(path)

    def test_real_store_all_nine_sources_no_native_or_oracle(self):
        rows = C.build_envelopes(NoNativeRuntime)
        self.assertEqual(len(rows), 9)
        self.assertEqual([r["project"] for r in rows],
                         [x[0] for x in C.frozen.TABLE])
        for row in rows:
            self.assertTrue(row["source_only"])
            self.assertFalse(row["typed_jef_action_visible"])
            self.assertFalse(row["oracle_visible_to_native"])
            self.assertEqual((row["model_calls"], row["native_calls"], row["authority"]),
                             (0, 0, 0))
            self.assertEqual([m["role"] for m in row["messages"]],
                             ["system", "user"])
            self.assertEqual(C.sha(C.dumps(row["messages"]).encode()),
                             row["messages_sha256"])
            payload = json.loads(row["messages"][1]["content"])
            self.assertFalse(payload["typed_jef_action_visible"])
            self.assertEqual(payload["task"], "SOURCE_ONLY_INDEPENDENT_RULE_PROBE")
            for key in ("expected_action", "oracle", "suggested_action",
                        "typed_jef_action", "wrong_typed_action_synthetic_only"):
                self.assertNotIn(key, payload)
            self.assertEqual(payload["current"]["text"],
                             C.frozen.fixtures()[row["index"]]["current"])

    def test_preflight_receipt_negative_gates_and_no_model_call(self):
        result = C.preflight(NoNativeRuntime)
        self.assertEqual(result["status"], "SOURCE_ONLY_MODEL_SWAP_PREFLIGHT_NO_NATIVE")
        self.assertEqual(result["table_sha256"], C.frozen.TABLE_SHA256)
        self.assertEqual(result["seed"], 117041)
        self.assertEqual(result["planned_serial_native_calls"], 18)
        self.assertEqual((result["native_calls"], result["model_calls"],
                          result["learning_authority"], result["delivery_authority"],
                          result["tool_dispatches"], result["jepa_weight"]),
                         (0, 0, 0, 0, 0, 0))
        self.assertEqual(result["age0"], "RECORD_ONLY")
        self.assertEqual(result["step2"], "UTILITY_FAIL")
        self.assertEqual(result["b3"], "NO_PROMOTION")
        self.assertEqual(result["body_jepa"], "UNAVAILABLE")
        self.assertFalse(result["output_committed"])
        self.assertFalse(result["whole_system_complete"])

    def test_mutated_oracle_payload_and_message_digest_rejected(self):
        original = C.source_only.build
        def oracle_injected(*args, **kwargs):
            result = original(*args, **kwargs)
            if result.get("status") == C.source_only.STATUS:
                payload = json.loads(result["messages"][1]["content"])
                payload["oracle"] = "A"
                result["messages"][1]["content"] = json.dumps(payload)
            return result
        with patch.object(C.source_only, "build", side_effect=oracle_injected):
            with self.assertRaisesRegex(ValueError, "MESSAGE_DIGEST_RED"):
                C.build_envelopes(NoNativeRuntime)

    def test_injected_oracle_with_rehashed_messages_still_rejected(self):
        original = C.source_only.build
        def oracle_injected(*args, **kwargs):
            result = original(*args, **kwargs)
            if result.get("status") == C.source_only.STATUS:
                payload = json.loads(result["messages"][1]["content"])
                payload["oracle"] = "A"
                result["messages"][1]["content"] = C.dumps(payload)
                result["messages_sha256"] = C.sha(C.dumps(result["messages"]).encode())
            return result
        with patch.object(C.source_only, "build", side_effect=oracle_injected):
            with self.assertRaisesRegex(ValueError, "ORACLE_LEAK_RED"):
                C.build_envelopes(NoNativeRuntime)


if __name__ == "__main__":
    unittest.main()
