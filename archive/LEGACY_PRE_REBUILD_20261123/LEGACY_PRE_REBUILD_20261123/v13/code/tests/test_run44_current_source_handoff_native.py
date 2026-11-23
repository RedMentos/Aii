"""Run44 seed307 software prereg, fake-native and independent replay tests."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run44_current_source_handoff_native as runner
from scripts import run44_current_source_handoff_verify as verify
from v13.common import dumps

FIXTURE = Path(__file__).resolve().parents[1]/"docs/fixtures/run44_source_handoff_seed307.json"


def fake_row(home, installed, f, arm):
    if arm == "A_CURRENT_ONLY":
        answer = {"choice": "UNKNOWN", "remaining": None}
    else:
        answer = f["oracle"]
    quote = next((x for x in f["prior"].split(". ") if x.startswith("Budget ")), "")
    quote = quote + "." if quote and not quote.endswith(".") else quote
    if not quote:
        quote = "No budget has been supplied."
    analysts = [{"role": "B2_GIST", "verified_quotes": [{"text": quote}],
                 "hypothesis_authority": "MODEL_HYPOTHESIS_NOT_FACT"}]
    msgs = runner.messages(arm, f, analysts if arm == "B_VERIFIED_B2_TO_C3" else None)
    return {"fixture": f["id"], "arm": arm, "status": "RECORDED",
            "prior_sha256": hashlib.sha256(f["prior"].encode()).hexdigest(),
            "current_sha256": hashlib.sha256(f["current"].encode()).hexdigest(),
            "oracle_visible_to_native": False,
            "native_prompt": msgs,
            "native_prompt_sha256": hashlib.sha256(dumps(msgs).encode()).hexdigest(),
            "native_answer": dumps(answer),
            "native_c3_final": True, "native_c3_metrics": {"status": "FINAL"},
            "native_b2_finals": [True, True] if arm == "B_VERIFIED_B2_TO_C3" else [],
            "prior_quote_verified": arm == "B_VERIFIED_B2_TO_C3",
            "verified_quote_texts": [quote] if arm == "B_VERIFIED_B2_TO_C3" else [],
            "process_releases": [{"process_reaped": True}], "processes_reaped": True,
            "score": runner.score_answer(dumps(answer), f["oracle"])}


class Run44Seed307Preflight(unittest.TestCase):
    def test_fixture_is_frozen_and_source_disjoint(self):
        data = runner.load_fixture(FIXTURE)
        self.assertEqual(len(data["fixtures"]), 4)
        self.assertEqual(data["seed"], 307)
        self.assertEqual(len(set(f["id"] for f in data["fixtures"])), 4)
        for f in data["fixtures"]:
            self.assertNotIn("Budget "+str(f["oracle"].get("remaining")), f["current"])

    def test_oracle_never_in_any_arm_prompt(self):
        for f in runner.load_fixture(FIXTURE)["fixtures"]:
            for arm in runner.ARMS:
                analysts = [{"verified_quotes": []}] if arm == "B_VERIFIED_B2_TO_C3" else None
                msgs = runner.messages(arm, f, analysts)
                self.assertNotIn('"oracle"', dumps(msgs))
                self.assertIn(f["current"], msgs[-1]["content"])
                if arm == "A_CURRENT_ONLY":
                    self.assertNotIn(f["prior"], msgs[-1]["content"])
                if arm == "C_RAW_PRIOR_TO_C3":
                    self.assertIn(f["prior"], msgs[-1]["content"])

    def test_b_arm_requires_verified_analysts(self):
        f = runner.load_fixture(FIXTURE)["fixtures"][0]
        for a in (None, [], {}):
            with self.assertRaisesRegex(ValueError, "VERIFIED_ANALYSTS_REQUIRED"):
                runner.messages("B_VERIFIED_B2_TO_C3", f, a)

    def test_strict_json_score_and_nonfinite(self):
        oracle = {"choice": "A", "remaining": 12}
        self.assertEqual(runner.score_answer('{"choice":"A","remaining":12}', oracle)["correct"], 1)
        for s in ('{"choice":"A","remaining":true}', '{"choice":"A","remaining":"12"}',
                  '{"choice":"A","remaining":12,"extra":1}',
                  '{"choice":"A","remaining":NaN}', 'not json',
                  '{"choice":"B","remaining":12}'):
            with self.subTest(s=s):
                self.assertEqual(runner.score_answer(s, oracle)["correct"], 0)

    def test_pilot_signal_strict_threshold(self):
        s = {a: {"rows": 4, "correct": 0, "structural": 4} for a in runner.ARMS}
        s[runner.ARMS[1]]["correct"] = 3
        s[runner.ARMS[2]]["correct"] = 4
        self.assertTrue(runner.pilot_signal(s))
        s[runner.ARMS[0]]["correct"] = 2
        self.assertFalse(runner.pilot_signal(s))
        s[runner.ARMS[0]]["correct"] = 0
        s[runner.ARMS[1]]["structural"] = 3
        self.assertFalse(runner.pilot_signal(s))

    def test_fixture_hash_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"fixture.json"
            p.write_bytes(FIXTURE.read_bytes()+b" ")
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE_SHA256"):
                runner.load_fixture(p)

    def test_fake_run_and_independent_original_replay(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/"pilot"
            with patch.object(runner, "installed_artifacts", return_value={"model_sha256": {"c3": "pinned"}}):
                with patch.object(runner, "run_row", side_effect=fake_row):
                    result = runner.run(Path(td)/"installed", out, FIXTURE)
            self.assertEqual(result["status"], "PILOT_SIGNAL_ONLY_NO_PROMOTION")
            self.assertEqual(result["summary"]["B_VERIFIED_B2_TO_C3"]["correct"], 4)
            self.assertEqual(result["negative_gates"]["step2"], "UTILITY_FAIL")
            replay = verify.replay(out/"report.json", FIXTURE)
            self.assertTrue(replay["structural_valid"])
            self.assertTrue(replay["pilot_signal"])
            with self.assertRaises(FileExistsError):
                runner.run(Path(td)/"installed", out, FIXTURE)

    def test_tampered_original_report_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/"pilot"
            with patch.object(runner, "installed_artifacts", return_value={"model_sha256": {"c3": "pinned"}}):
                with patch.object(runner, "run_row", side_effect=fake_row):
                    runner.run(Path(td)/"installed", out, FIXTURE)
            p = out/"report.json"
            r = json.loads(p.read_text())
            r["rows"][0]["native_answer"] = '{"choice":"A","remaining":999}'
            p.write_text(dumps(r))
            with self.assertRaisesRegex(ValueError, "ROW_HASH"):
                verify.replay(p, FIXTURE)

    def test_original_negative_gates_not_promoted(self):
        self.assertEqual(runner.NEGATIVE, verify.NEGATIVE)
        self.assertFalse(runner.NEGATIVE["whole_system_complete"])
        self.assertEqual(runner.NEGATIVE["jepa_weight"], 0)


if __name__ == "__main__":
    unittest.main()
