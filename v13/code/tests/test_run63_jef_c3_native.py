"""Run63 native receiver prereg and independent false-proof software controls."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts import p2x_disjoint_receiver_trainset as p2x
from scripts import run63_jef_c3_native as runner
from scripts import run63_jef_c3_native_verify as verifier


class Run63NativeControls(unittest.TestCase):
    def test_three_fixed_balanced_calibration_cases(self):
        rows = runner.cohort()
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["oracle_action"] for r in rows],
                         ["A", "B", "NONE"])
        self.assertEqual(len({r["id"] for r in rows}), 3)
        self.assertTrue(all(r["partition"] == "calibration" for r in rows))
        self.assertEqual(rows, verifier.selected())
        self.assertEqual(runner.ORDER, verifier.ORDER)
        self.assertEqual(p2x.SEED, 2026102921)

    def test_raw_source_prompt_no_oracle_leak(self):
        for row in runner.cohort():
            messages = runner.raw_messages(row)
            self.assertEqual([x["role"] for x in messages],
                             ["system", "user"])
            payload = json.loads(messages[1]["content"])
            self.assertEqual(payload["current_source"], row["current"])
            self.assertEqual(payload["policy_source"], row["b2_source"])
            self.assertEqual(payload["sheet_source"], row["b1_source"])
            self.assertNotIn("oracle", payload)
            self.assertNotIn("oracle_action", payload)
            self.assertNotIn("typed_jef_action", payload)

    def test_forged_success_without_real_native_rows_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"forged.json"
            p.write_text(json.dumps({
                "schema":"v13.run63.jef_c3_native_report.v1",
                "seed":p2x.SEED, "model_seed":13,
                "claim":"P2X_CALIBRATION_JEF_C3_ENGINEERING_NOT_DISJOINT_UTILITY",
                "negative_gates":runner.NEGATIVE,
                "binding":{"model_sha256":{"C3_LANGUAGE":runner.C3_SHA256},
                           "runner_sha256":runner.RUNNER_SHA256},
                "installed_binding_unchanged":True,
                "selected_ids":[r["id"] for r in runner.cohort()],
                "scores":{"RAW":0,"TYPED":3},
                "rows":[], "status":"RECEIVER_PILOT_PASS"}))
            result = verifier.verify(p)
            self.assertEqual(result["status"], "STRUCTURAL_RED")
            self.assertIn("row_count", result["errors"])

    def test_pinned_native_and_no_claims(self):
        self.assertEqual(runner.C3_SHA256, verifier.C3_SHA)
        self.assertEqual(runner.RUNNER_SHA256, verifier.RUNNER_SHA)
        self.assertEqual(runner.RUN_CONFIG["learning_mode"], "RECORD_ONLY")
        self.assertEqual(runner.RUN_CONFIG["temperature"], 0.)
        self.assertEqual(runner.RUN_CONFIG["seed"], 13)
        self.assertEqual(runner.RUN_CONFIG["answer_tokens"], 32)
        self.assertEqual(runner.NEGATIVE["step2"], "UTILITY_FAIL")
        self.assertEqual(runner.NEGATIVE["jepa_weight"], 0)


if __name__ == "__main__":
    unittest.main()
