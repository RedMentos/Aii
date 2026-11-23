"""Run35 synthetic counterexample: report row arm must bind to exact C3 envelope."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import run33_b2_c3_counterfactual_envelopes as cf
from scripts import run34_c3_native_quote_intervention_pilot as pilot
from v13.common import dumps
from v13.utility import score_decision


def fake_report():
    """Synthetic structural rows ONLY; no model executed and no utility claim."""
    oracle = next(f["oracle"] for f in cf.FIXTURES if f["id"] == pilot.FIXTURE)
    rows = []
    for arm in pilot.ARMS:
        raw = "{}"
        rows.append({
            "arm": arm, "envelope": cf.build_envelope(pilot.FIXTURE, arm, pilot.SEED),
            "raw_answer": raw,
            "raw_answer_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "score": score_decision(raw, oracle), "native_status": "FINAL",
            "native_metrics": {"status": "FINAL",
                               "actual_model": "LFM2.5-350M-QAD-Q4_0.gguf"},
            "process_reaped": True, "oracle_visible_to_native": False,
            "model_sha256": pilot.C3_GGUF_SHA256, "runner_sha256": "a" * 64,
            "envelope_verified": True,
        })
    return {
        "schema": "v13.run34.c3_only.native_pilot.raw.v1",
        "fixture_id": pilot.FIXTURE, "seed": pilot.SEED,
        "model_sha256": pilot.C3_GGUF_SHA256, "runner_sha256": "a" * 64,
        "rows": rows, "row_sha256": {}, "failed_attempts": [],
        "canonical_gate_pass": False, "phone_measured": False, "jepa_weight": 0,
    }


class Run35ArmBinding(unittest.TestCase):
    def test_rehashed_swapped_envelopes_refused(self):
        report = fake_report()
        report["rows"][0]["envelope"], report["rows"][1]["envelope"] = (
            report["rows"][1]["envelope"], report["rows"][0]["envelope"]
        )
        for row in report["rows"]:
            self.assertTrue(cf.verify_envelope(row["envelope"]))
        report["row_sha256"] = {
            row["arm"]: hashlib.sha256(dumps(row).encode()).hexdigest()
            for row in report["rows"]
        }
        with self.assertRaisesRegex(ValueError, "native_envelope_arm_mismatch"):
            pilot.verify_report(report, pilot.C3_GGUF_SHA256, "a" * 64)

    def test_false_source_verifier_refused_before_native_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            evidence = home / "fresh-evidence"
            with (
                mock.patch.object(pilot, "prereg", return_value={"schema": "synthetic"}),
                mock.patch.object(pilot, "_installed",
                                  return_value=(None, home / "fake.gguf", "a" * 64)),
                mock.patch.object(pilot.cf, "verify_envelope", return_value=False),
                mock.patch.object(pilot, "LlamaRunner") as native,
            ):
                with self.assertRaisesRegex(ValueError, "native_envelope_invalid"):
                    pilot._run_unlocked(home, evidence)
                native.assert_not_called()
            receipt = json.loads((evidence / "RECEIPT.json").read_text())
            self.assertEqual(receipt["status"], "FAIL_RETAIN_RAW")
            self.assertEqual(receipt["error_type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
