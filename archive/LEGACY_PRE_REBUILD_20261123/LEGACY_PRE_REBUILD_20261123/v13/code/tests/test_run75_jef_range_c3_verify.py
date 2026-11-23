"""Run75 software-only synthetic verifier tests; not native C3 evidence."""
import copy
import json
import unittest

from scripts import jef_range_native_fixture_773 as f
from scripts import run75_jef_range_c3_verify as verify
from v13.common import dumps
from v13.jef_range_c3_typed_envelope_shadow import SYSTEM


def synthetic_report():
    report = {
        "schema": verify.REPORT_SCHEMA,
        "seed": f.SEED, "temperature": 0.0, "max_tokens": 32,
        "table_sha256": f.TABLE_SHA256,
        "model_sha256_required": f.MODEL_SHA256,
        "runner_sha256_required": f.RUNNER_SHA256,
        "model_sha256_observed": f.MODEL_SHA256,
        "runner_sha256_observed": f.RUNNER_SHA256,
        "formatter_only": True, "typed_answer_visible": True,
        "independent_source_reasoning_proven": False,
        "native_call_count": 6, "closed_store_ok": True,
        "no_live_output": True,
        "delivery_authority": 0, "tool_dispatches": 0,
        "learning_authority": 0, "tty_approved": False,
        "output_committed": False, "age0": "RECORD_ONLY",
        "step2": "UTILITY_FAIL", "b3": "NO_PROMOTION",
        "body_jepa": "UNAVAILABLE", "world_jepa": "SHADOW",
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False,
        "cases": [], "strict": 6, "status": "FORMATTER_SMALL_SYNTHETIC_PASS",
    }
    for row in f.fixtures():
        payload = {
            "typed_jef_action": row["expected"],
            "human_source_lineage_verified": True,
            "source_ref_sha256": ["a" * 64, "b" * 64],
            "current_source_ref_sha256": "c" * 64,
            "rule_parser_revision": "jef-mixed-range-policy-shadow-run73-v1",
        }
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": dumps(payload)}]
        output = json.dumps({"action": row["expected"]})
        report["cases"].append({
            "index": row["index"],
            "project_sha256": f.sha(row["project"].encode()),
            "expected": row["expected"],
            "typed_jef_action": row["expected"],
            "source_sha256": {
                k: f.sha(row[k].encode("utf-8"))
                for k in ("current", "policy_source", "sheet_source")},
            "input_messages": messages,
            "input_sha256": f.sha(dumps(messages).encode()),
            "output": output,
            "output_sha256": f.sha(output.encode()),
            "output_bytes": len(output.encode()),
            "parsed_action": row["expected"],
            "strict": 1,
            "native_final": True,
            "process_reaped": True,
            "post_source_rechecked": True,
            "actual_model": verify.EXPECTED_MODEL,
            "status": "RECORDED",
        })
    return report


class Run75VerifierSoftware(unittest.TestCase):
    def test_fixture_oracle_and_synthetic_structural_verifier(self):
        self.assertEqual([r["expected"] for r in f.fixtures()],
                         ["A", "B", "NONE", "A", "B", "NONE"])
        self.assertEqual(verify.verify(synthetic_report())["strict"], 6)

    def test_native_output_hash_tamper(self):
        r = synthetic_report()
        r["cases"][0]["output_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "NATIVE_OUTPUT_RED"):
            verify.verify(r)

    def test_prompt_typed_action_tamper(self):
        r = synthetic_report()
        r["cases"][0]["input_messages"][1]["content"] = dumps(
            {"typed_jef_action": "B"})
        r["cases"][0]["input_sha256"] = f.sha(dumps(
            r["cases"][0]["input_messages"]).encode())
        with self.assertRaisesRegex(ValueError, "PROMPT_SOURCE_RED"):
            verify.verify(r)

    def test_model_final_or_process_reaping_missing(self):
        for key in ("native_final", "process_reaped",
                    "post_source_rechecked"):
            r = synthetic_report()
            r["cases"][1][key] = False
            with self.assertRaisesRegex(ValueError, "CASE_BINDING_RED"):
                verify.verify(r)

    def test_no_live_output_or_tty_forgery(self):
        for key, value in (("no_live_output", False),
                           ("tty_approved", True),
                           ("learning_authority", 1)):
            r = synthetic_report()
            r[key] = value
            with self.assertRaisesRegex(ValueError, "BOUNDARY_RED"):
                verify.verify(r)

    def test_wrong_score_and_status_forgery(self):
        r = synthetic_report()
        r["strict"] = 5
        with self.assertRaisesRegex(ValueError, "SCORE_REPARSE_RED"):
            verify.verify(r)
        r = synthetic_report()
        r["status"] = "WHOLE_SYSTEM_COMPLETE"
        with self.assertRaisesRegex(ValueError, "STATUS_REPARSE_RED"):
            verify.verify(r)


if __name__ == "__main__":
    unittest.main()
