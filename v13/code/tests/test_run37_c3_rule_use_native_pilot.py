"""Run37 native pilot source-only guards; all fabricated rows are synthetic."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import run33_b2_c3_counterfactual_envelopes as cf
from scripts import run37_c3_rule_use_hint_envelopes as study
from scripts import run37_c3_rule_use_native_pilot as pilot
from v13.common import dumps
from v13.utility import score_decision


class Run37NativePreflight(unittest.TestCase):
    def test_pinned_source_model_runner_and_negative_gates(self):
        reg = pilot.prereg()
        self.assertEqual(reg["fixture_id"], "Elyndra")
        self.assertEqual(reg["seed"], 20261122)
        self.assertEqual(reg["arms"], list(study.ARMS))
        self.assertEqual(reg["model_sha256"], pilot.base.C3_GGUF_SHA256)
        self.assertEqual(reg["runner_tar_sha256"], pilot.base.RUNNER_TAR_SHA256)
        self.assertFalse(reg["native_executed"])
        self.assertFalse(reg["canonical_gate_pass"])
        self.assertEqual(reg["jepa_weight"], 0)

    def test_missing_installed_home_never_opens_native(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "missing-home"
            evidence = Path(temp) / "evidence"
            with mock.patch.object(pilot.base.LlamaRunner, "__init__",
                                   side_effect=AssertionError("native opened")):
                with self.assertRaises(ValueError):
                    pilot.run(home, evidence)
            self.assertFalse(evidence.exists())
            self.assertFalse(home.exists())

    def test_synthetic_rehashed_swapped_arm_envelope_refused(self):
        oracle = next(f["oracle"] for f in cf.FIXTURES if f["id"] == study.FIXTURE)
        rows = []
        for arm in study.ARMS:
            raw = "{}"
            rows.append({
                "arm": arm, "envelope": study.build_envelope(arm),
                "raw_answer": raw,
                "raw_answer_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "score": score_decision(raw, oracle), "native_status": "FINAL",
                "native_metrics": {"status": "FINAL",
                                   "actual_model": "LFM2.5-350M-QAD-Q4_0.gguf"},
                "process_reaped": True, "oracle_visible_to_native": False,
                "model_sha256": pilot.base.C3_GGUF_SHA256,
                "runner_sha256": "a" * 64, "envelope_verified": True,
            })
        rows[0]["envelope"], rows[1]["envelope"] = rows[1]["envelope"], rows[0]["envelope"]
        report = {
            "schema": pilot.SCHEMA, "fixture_id": study.FIXTURE,
            "seed": study.SEED, "model_sha256": pilot.base.C3_GGUF_SHA256,
            "runner_sha256": "a" * 64, "rows": rows,
            "row_sha256": {
                row["arm"]: hashlib.sha256(dumps(row).encode()).hexdigest()
                for row in rows
            },
            "failed_attempts": [], "canonical_gate_pass": False,
            "phone_measured": False, "jepa_weight": 0,
        }
        with self.assertRaisesRegex(ValueError, "run37_native_envelope_arm_mismatch"):
            pilot.verify_report(report, pilot.base.C3_GGUF_SHA256, "a" * 64)

    def test_false_envelope_verifier_refused_before_native(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            evidence = home / "fresh-evidence"
            with (
                mock.patch.object(pilot, "prereg", return_value={"schema": "synthetic"}),
                mock.patch.object(pilot.base, "_installed",
                                  return_value=(None, home / "fake.gguf", "a" * 64)),
                mock.patch.object(pilot.study, "verify_envelope", return_value=False),
                mock.patch.object(pilot.base, "LlamaRunner") as native,
            ):
                with self.assertRaisesRegex(ValueError, "run37_native_envelope_invalid"):
                    pilot._run_unlocked(home, evidence)
                native.assert_not_called()
            receipt = json.loads((evidence / "RECEIPT.json").read_text())
            self.assertEqual(receipt["status"], "FAIL_RETAIN_RAW")


if __name__ == "__main__":
    unittest.main()
