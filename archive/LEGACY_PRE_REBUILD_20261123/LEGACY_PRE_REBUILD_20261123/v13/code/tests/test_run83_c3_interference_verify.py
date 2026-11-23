"""Run83 frozen fixture/verifier adversarial tests. Synthetic reports only."""
import copy
import unittest

from scripts import jef_body_c3_interference_fixture_839 as f
from scripts import run83_jef_body_c3_interference_native as native
from scripts import run83_jef_body_c3_interference_verify as verify
from v13.common import dumps
from v13.jef_range_c3_typed_envelope_shadow import SYSTEM as TYPED_SYSTEM
from v13.jef_b1b2_c3_dual_source_shadow import SYSTEM as DUAL_SYSTEM


def synthetic_report():
    cases = []
    for row in f.fixtures():
        for arm in row["arm_order"]:
            if arm == "TYPED_ONLY":
                payload = {
                    "typed_jef_action": row["expected"],
                    "human_source_lineage_verified": True,
                }
            else:
                payload = {
                    "typed_jef_action": row["expected"],
                    "human_source_lineage_verified": True,
                    "body_hypotheses_are_facts": False,
                    "current_source": {"text": row["current"]},
                    "body_observations": [
                        {"role": role,
                         "hypothesis_authority": "MODEL_HYPOTHESIS_NOT_FACT",
                         "hypothesis": {"summary":
                             "Synthetic body: Option "
                             + row["wrong_body_action"] + " is correct."},
                         "verified_quotes": []}
                        for role in ("B1_DETAIL", "B2_GIST")],
                }
            messages = [
                {"role": "system", "content": (
                    TYPED_SYSTEM if arm == "TYPED_ONLY" else DUAL_SYSTEM)},
                {"role": "user", "content": dumps(payload)},
            ]
            output = dumps({"action": row["expected"]})
            cases.append({
                "index": row["index"], "arm": arm,
                "project_sha256": f.sha(row["project"].encode()),
                "expected": row["expected"],
                "wrong_body_action": row["wrong_body_action"],
                "source_sha256": row["source_sha256"],
                "synthetic_body": True, "native_body": False,
                "typed_jef_action": row["expected"],
                "native_final": True, "process_reaped": True,
                "post_source_rechecked": True,
                "actual_model": native.C3_MODEL,
                "status": "RECORDED",
                "input_messages": messages,
                "input_sha256": f.sha(dumps(messages).encode()),
                "output": output, "output_sha256": f.sha(output.encode()),
                "output_bytes": len(output.encode()),
                "parsed_action": row["expected"], "strict": 1,
            })
    return {
        "schema": native.SCHEMA, "seed": f.SEED,
        "table_sha256": f.TABLE_SHA256,
        "model_sha256_required": f.MODEL_SHA256,
        "model_sha256_observed": f.MODEL_SHA256,
        "runner_sha256_required": f.RUNNER_SHA256,
        "runner_sha256_observed": f.RUNNER_SHA256,
        "temperature": 0.0, "max_tokens": 32,
        "native_call_count": 12, "body_native_call_count": 0,
        "body_observations_synthetic": True,
        "typed_answer_visible_to_c3": True,
        "independent_reasoning_proven": False,
        "closed_store_ok": True, "no_live_output": True,
        "delivery_authority": 0, "learning_authority": 0,
        "tool_dispatches": 0, "output_committed": False,
        "tty_approved": False, "age0": "RECORD_ONLY",
        "step2": "UTILITY_FAIL", "b3": "NO_PROMOTION",
        "body_jepa": "UNAVAILABLE", "world_jepa": "SHADOW",
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False, "cases": cases,
        "scores": {"TYPED_ONLY": 6, "DUAL_SOURCE": 6},
        "status": "DUAL_FORMATTER_NONINFERIOR_SMALL_SHADOW",
    }


class Run83VerifierTests(unittest.TestCase):
    def test_fixture_and_counterbalance(self):
        rows = f.fixtures()
        self.assertEqual(len(rows), 6)
        self.assertEqual([r["expected"] for r in rows],
                         ["A", "B", "NONE", "A", "B", "NONE"])
        self.assertEqual([r["arm_order"][0] for r in rows],
                         ["TYPED_ONLY", "DUAL_SOURCE"] * 3)

    def test_synthetic_structure_never_claims_native(self):
        result = verify.verify(synthetic_report())
        self.assertEqual(result["scores"],
                         {"TYPED_ONLY": 6, "DUAL_SOURCE": 6})
        self.assertTrue(result["synthetic_body_only"])
        self.assertFalse(result["step2_promoted"])
        self.assertEqual(result["delivery_authority"], 0)

    def test_native_body_forgery_rejected(self):
        report = synthetic_report()
        report["body_native_call_count"] = 12
        with self.assertRaisesRegex(ValueError, "AUTHORITY_RED"):
            verify.verify(report)

    def test_missing_and_swapped_arm_rejected(self):
        report = synthetic_report()
        report["cases"].pop()
        with self.assertRaisesRegex(ValueError, "CASE_COUNT_RED"):
            verify.verify(report)
        report = synthetic_report()
        report["cases"][0], report["cases"][1] = (
            report["cases"][1], report["cases"][0])
        with self.assertRaisesRegex(ValueError, "CASE_BINDING_RED"):
            verify.verify(report)

    def test_typed_action_and_body_hypothesis_forgery_rejected(self):
        report = synthetic_report()
        report["cases"][0]["input_messages"][1]["content"] = dumps(
            {"typed_jef_action": "B", "human_source_lineage_verified": True})
        report["cases"][0]["input_sha256"] = f.sha(dumps(
            report["cases"][0]["input_messages"]).encode())
        with self.assertRaisesRegex(ValueError, "TYPED_ACTION_RED"):
            verify.verify(report)
        report = synthetic_report()
        case = report["cases"][1]
        payload = __import__("json").loads(
            case["input_messages"][1]["content"])
        payload["body_observations"][0]["hypothesis"]["summary"] = "No clue"
        case["input_messages"][1]["content"] = dumps(payload)
        case["input_sha256"] = f.sha(dumps(case["input_messages"]).encode())
        with self.assertRaisesRegex(ValueError, "BODY_HYPOTHESIS_RED"):
            verify.verify(report)

    def test_source_hash_and_score_tamper_rejected(self):
        report = synthetic_report()
        report["cases"][0]["source_sha256"]["current"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "CASE_BINDING_RED"):
            verify.verify(report)
        report = synthetic_report()
        report["cases"][0]["strict"] = 0
        with self.assertRaisesRegex(ValueError, "OUTPUT_SCORE_RED"):
            verify.verify(report)

    def test_registered_negative_verdicts(self):
        self.assertEqual(f.verdict({"TYPED_ONLY": 6, "DUAL_SOURCE": 4}),
                         "DUAL_INTERFERENCE_RED")
        self.assertEqual(f.verdict({"TYPED_ONLY": 4, "DUAL_SOURCE": 6}),
                         "BASELINE_FORMATTER_RED")
        self.assertEqual(f.verdict({"TYPED_ONLY": 6, "DUAL_SOURCE": 5}),
                         "DUAL_FORMATTER_NONINFERIOR_SMALL_SHADOW")


if __name__ == "__main__":
    unittest.main()
