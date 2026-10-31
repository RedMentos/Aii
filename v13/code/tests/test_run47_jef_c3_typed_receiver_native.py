"""Run47 seed409 prereg, fake runner and independent original replay software tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run47_jef_c3_typed_receiver_native as runner
from scripts import run47_jef_c3_typed_receiver_verify as verify
from v13.common import dumps

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run47_jef_c3_typed_receiver_seed409.json"


def ref(source, ident):
    return {"source_id": ident, "sha256": hashlib.sha256(source.encode()).hexdigest(),
            "char_start": 0, "char_end": len(source), "modality": "text"}


def fake_row(home, installed, fixture, arm):
    p = ref(fixture["prior"], "prior-" + fixture["id"])
    c = ref(fixture["current"], "current-" + fixture["id"])
    jef = {"reason": "EXACT_USER_SOURCE_RECIPE_SHADOW",
           "status": "SHADOW_NO_AUTHORITY", "authority": 0,
           "model_called": False, "native_calls": 0,
           "candidate": fixture["oracle"],
           "source_ref_sha256": [verify.sha(verify.canonical(x)) for x in (p, c)]}
    msgs = runner.messages(arm, fixture, jef if arm == runner.ARMS[1] else None)
    answer = (fixture["oracle"] if arm == runner.ARMS[1]
              else {"choice": "B", "remaining": None})
    raw = dumps(answer)
    row = {"fixture": fixture["id"], "arm": arm, "status": "RECORDED",
           "prior_sha256": hashlib.sha256(fixture["prior"].encode()).hexdigest(),
           "current_sha256": hashlib.sha256(fixture["current"].encode()).hexdigest(),
           "prior_source_ref": p, "current_source_ref": c,
           "oracle_visible_to_native": False, "native_prompt": msgs,
           "native_prompt_sha256": hashlib.sha256(dumps(msgs).encode()).hexdigest(),
           "native_answer": raw, "native_c3_final": True,
           "native_c3_metrics": {"status": "FINAL"},
           "process_releases": [{"process_reaped": True}],
           "processes_reaped": True, "score": runner.score(raw, fixture["oracle"])}
    if arm == runner.ARMS[1]:
        row["jef_candidate"] = jef
        row["jef_matches_oracle"] = True
    return row


class Run47Preflight(unittest.TestCase):
    def test_fixture_disjoint_and_hash(self):
        f = runner.load_fixture(FIXTURE)
        self.assertEqual(f["seed"], 409)
        self.assertEqual(len(f["fixtures"]), 6)
        self.assertEqual(len(set(x["id"] for x in f["fixtures"])), 6)
        self.assertEqual(runner.FIXTURE_SHA256, verify.FIXTURE_SHA)

    def test_oracle_not_supplied_to_native_messages(self):
        for f in runner.load_fixture(FIXTURE)["fixtures"]:
            for arm in runner.ARMS:
                msgs = fake_row(None, None, f, arm)["native_prompt"]
                self.assertNotIn('"oracle"', dumps(msgs))
                self.assertIn(f["current"], msgs[1]["content"])
                if arm == runner.ARMS[0]:
                    self.assertIn(f["prior"], msgs[1]["content"])
                else:
                    self.assertNotIn(f["prior"], msgs[1]["content"])
                    self.assertIn("typed_jef_candidate", msgs[1]["content"])

    def test_missing_or_unauthorized_jef_candidate_rejected(self):
        f = runner.load_fixture(FIXTURE)["fixtures"][0]
        for bad in (None, {}, {"candidate": f["oracle"]},
                    {"candidate": f["oracle"], "authority": 1}):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "JEF_SOURCE_SHADOW_REQUIRED"):
                    runner.messages(runner.ARMS[1], f, bad)

    def test_strict_duplicate_nonfinite_bool_and_extra_keys(self):
        oracle = {"choice": "A", "remaining": 10}
        self.assertEqual(runner.score('{"choice":"A","remaining":10}', oracle)["correct"], 1)
        for raw in ('{"choice":"B","choice":"A","remaining":10}',
                    '{"choice":"A","remaining":NaN}',
                    '{"choice":"A","remaining":true}',
                    '{"choice":"A","remaining":10,"extra":0}',
                    '{"choice":"A","remaining":"10"}'):
            self.assertEqual(runner.score(raw, oracle)["correct"], 0)

    def test_fake_full_run_and_independent_replay(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "fake"
            binding = {"model_sha256": verify.MODELS, "runner_sha256": verify.RUNNER_SHA}
            with patch.object(runner, "installed_artifacts", return_value=binding):
                with patch.object(runner, "run_row", side_effect=fake_row):
                    report = runner.run(Path(td) / "installed", out, FIXTURE)
            self.assertEqual(report["status"], "RECEIVER_COPY_SIGNAL_ONLY")
            self.assertEqual(report["summary"][runner.ARMS[1]]["correct"], 6)
            result = verify.replay(out / "report.json", FIXTURE)
            self.assertTrue(result["structural_valid"])
            self.assertTrue(result["receiver_copy_signal"])
            self.assertEqual(result["negative_gates"]["step2"], "UTILITY_FAIL")
            with self.assertRaises(FileExistsError):
                runner.run(Path(td) / "installed", out, FIXTURE)

    def test_original_wrong_answers_keep_utility_fail(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "fake"
            binding = {"model_sha256": verify.MODELS, "runner_sha256": verify.RUNNER_SHA}
            def wrong(home, installed, f, arm):
                row = fake_row(home, installed, f, arm)
                row["native_answer"] = '{"choice":"B","remaining":null}'
                row["score"] = runner.score(row["native_answer"], f["oracle"])
                return row
            with patch.object(runner, "installed_artifacts", return_value=binding):
                with patch.object(runner, "run_row", side_effect=wrong):
                    report = runner.run(Path(td) / "installed", out, FIXTURE)
            self.assertEqual(report["status"], "UTILITY_FAIL")
            result = verify.replay(out / "report.json", FIXTURE)
            self.assertTrue(result["structural_valid"])
            self.assertFalse(result["receiver_copy_signal"])

    def test_row_tamper_detected_by_independent_digest(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "fake"
            binding = {"model_sha256": verify.MODELS, "runner_sha256": verify.RUNNER_SHA}
            with patch.object(runner, "installed_artifacts", return_value=binding):
                with patch.object(runner, "run_row", side_effect=fake_row):
                    runner.run(Path(td) / "installed", out, FIXTURE)
            p = out / "report.json"
            report = json.loads(p.read_text())
            report["rows"][0]["native_answer"] = "TAMPER"
            p.write_text(dumps(report))
            with self.assertRaisesRegex(ValueError, "ROW_SHA"):
                verify.replay(p, FIXTURE)

    def test_original_negative_gates_and_threshold(self):
        self.assertEqual(runner.NEGATIVE, verify.NEGATIVE)
        self.assertEqual(runner.NEGATIVE["jepa_weight"], 0)
        summary = {a: {"rows": 6, "structural": 6, "correct": 0} for a in runner.ARMS}
        summary[runner.ARMS[1]]["correct"] = 5
        self.assertTrue(runner.signal(summary))
        summary[runner.ARMS[0]]["correct"] = 4
        self.assertFalse(runner.signal(summary))


if __name__ == "__main__":
    unittest.main()
