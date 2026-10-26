"""Run510 strict synthetic quote matrix and fail-closed adversarial cases."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run509_b2_rule_quote_prereg as frozen
import run510_b2_quote_metric as metric


def synthetic_observations():
    reg = frozen.registration()
    rows = []
    for fixture in reg["fixtures"]:
        prior = fixture["history"][0]
        prior_sha = hashlib.sha256(prior.encode()).hexdigest()
        for arm in reg["arms"]:
            for seed in reg["seeds"]:
                quotes = []
                if arm == "RULE_FOCUS" and fixture["type"] in ("SPLIT", "RULE"):
                    quotes = [{"source_slot": "history0",
                               "source_sha256": prior_sha, "text": fragment}
                              for fragment in metric.rule_fragments(fixture)]
                rows.append({"fixture": fixture["id"], "arm": arm, "seed": seed,
                             "status": "RECORDED",
                             "source_history0_sha256": prior_sha,
                             "quotes": quotes})
    return rows


class StrictQuoteMetric(unittest.TestCase):
    def test_synthetic_full_paired_coverage_and_no_gate_promotion(self):
        result = metric.score(frozen.registration(), synthetic_observations())
        self.assertEqual(result["observations"], 60)
        self.assertEqual(result["primary_paired_observations"], 24)
        self.assertEqual(result["primary_all_three_rule_quotes"],
                         {"BASE": 0, "RULE_FOCUS": 24})
        self.assertEqual(result["primary_focus_minus_base_rows"], 24)
        self.assertEqual(result["source_quote_records_verified"], 72)
        self.assertTrue(result["preregistered_descriptive_gain_reached"])
        self.assertFalse(result["native_evidence_verified"])
        self.assertFalse(result["false_prior_rule_assertions_in_summaries_evaluated"])
        self.assertFalse(result["canonical_gate_pass"])
        self.assertEqual(result["step2_exit"], "UTILITY_FAIL")

    def test_fabricated_quote_and_wrong_source_slot_fail(self):
        rows = synthetic_observations()
        target = next(r for r in rows if r["quotes"])
        target["quotes"][0]["text"] = "Budget 999 euros."
        with self.assertRaisesRegex(ValueError, "FABRICATED_OR_UNVERIFIED_QUOTE"):
            metric.score(frozen.registration(), rows)
        rows = synthetic_observations()
        target = next(r for r in rows if r["quotes"])
        target["quotes"][0]["source_slot"] = "current"
        with self.assertRaisesRegex(ValueError, "FABRICATED_OR_UNVERIFIED_QUOTE"):
            metric.score(frozen.registration(), rows)

    def test_missing_duplicate_and_source_hash_tamper_fail(self):
        rows = synthetic_observations()
        with self.assertRaisesRegex(ValueError, "EXACT_SIXTY_OBSERVATIONS_REQUIRED"):
            metric.score(frozen.registration(), rows[:-1])
        rows[-1] = copy.deepcopy(rows[0])
        with self.assertRaisesRegex(ValueError, "UNKNOWN_DUPLICATE_OR_INVALID_ROW"):
            metric.score(frozen.registration(), rows)
        rows = synthetic_observations()
        rows[0]["source_history0_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "OBSERVATION_SOURCE_HASH_DRIFT"):
            metric.score(frozen.registration(), rows)

    def test_registration_tamper_and_detail_current_quote_not_prior(self):
        reg = frozen.registration()
        altered = copy.deepcopy(reg)
        altered["seeds"] = [41, 42, 99]
        with self.assertRaisesRegex(ValueError, "RUN509_FROZEN_REGISTRATION_REQUIRED"):
            metric.score(altered, synthetic_observations())
        rows = synthetic_observations()
        detail = next(f for f in reg["fixtures"] if f["type"] == "DETAIL")
        target = next(r for r in rows if r["fixture"] == detail["id"] and
                      r["arm"] == "RULE_FOCUS")
        source = detail["current"]
        target["quotes"] = [{"source_slot": "current",
                             "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                             "text": "budget "}]
        result = metric.score(reg, rows)
        self.assertEqual(result["per_fixture"][detail["id"]]["RULE_FOCUS"], 0)

    def test_cli_source_only_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reg = root / "registration.json"
            obs = root / "observations.json"
            out = root / "metric.json"
            reg.write_text(json.dumps(frozen.registration()))
            obs.write_text(json.dumps(synthetic_observations()))
            cmd = [sys.executable, str(ROOT / "scripts" /
                   "run510_b2_quote_metric.py"), "--registration", str(reg),
                   "--observations", str(obs), "--output", str(out)]
            first = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertFalse(json.loads(out.read_text())["native_evidence_verified"])
            again = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(again.returncode, 0)
            self.assertIn("FileExistsError", again.stderr)
            native = subprocess.run(cmd + ["--execute"], capture_output=True,
                                    text=True, timeout=60)
            self.assertNotEqual(native.returncode, 0)
            self.assertIn("unrecognized arguments", native.stderr)


if __name__ == "__main__":
    unittest.main()
