"""Run49 source→JEF→fake C3→final Store gate software preflight and replay."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run49_jef_c3_final_shadow_native as runner
from scripts import run49_jef_c3_final_shadow_verify as verify
from scripts.run47_jef_c3_typed_receiver_native import ARMS, messages, score
from v13.common import dumps
from v13.config import initialize
from v13.store import Store
from v13.agi.jef_eligibility_source_shadow_run46b import propose
from v13.agi.jef_c3_final_agreement_shadow_run48 import check

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run49_jef_c3_final_shadow_seed431.json"


def fake_row(home, installed, fixture, wrong=False):
    initialize(home)
    store = Store(home)
    try:
        session = store.new_session()
        prior = store.event(session, fixture["prior"])
        current = store.event(session, fixture["current"])
        p, c = prior["source_ref"], current["source_ref"]
        jef = propose(store, p, c)
        msgs = messages(ARMS[1], fixture, jef)
        answer = ('{"choice":"B","remaining":null}' if wrong
                  else dumps(fixture["oracle"]))
        before = runner._counts(store)
        gate = check(store, p, c, current["event_id"], session, answer)
        return {"fixture": fixture["id"], "status": "RECORDED",
                "prior_sha256": runner.sha(fixture["prior"].encode("utf-8")),
                "current_sha256": runner.sha(fixture["current"].encode("utf-8")),
                "prior_source_ref": p, "current_source_ref": c,
                "current_event_id": current["event_id"], "session_id": session,
                "oracle_visible_to_native": False, "jef_candidate": jef,
                "jef_matches_oracle": jef["candidate"] == fixture["oracle"],
                "native_prompt": msgs,
                "native_prompt_sha256": runner.sha(dumps(msgs).encode("utf-8")),
                "native_answer": answer, "native_c3_final": True,
                "native_c3_metrics": {"status": "FINAL"},
                "native_score": score(answer, fixture["oracle"]),
                "final_agreement": gate, "gate_store_unchanged": before == runner._counts(store),
                "process_releases": [{"process_reaped": True}],
                "processes_reaped": True}
    finally:
        store.close()


class Run49Preflight(unittest.TestCase):
    def test_frozen_disjoint_fixture_hash_and_ids(self):
        f = runner.load_fixture(FIXTURE)
        self.assertEqual(f["seed"], 431)
        self.assertEqual(tuple(x["id"] for x in f["fixtures"]), runner.IDS)
        self.assertEqual(runner.FIXTURE_SHA, verify.FIXTURE_SHA)

    def test_fake_six_real_store_gate_and_independent_replay(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "fake"
            binding = {"model_sha256": verify.MODELS, "runner_sha256": verify.RUNNER_SHA}
            with patch.object(runner, "installed_artifacts", return_value=binding):
                with patch.object(runner, "run_row", side_effect=fake_row):
                    report = runner.run(Path(td) / "installed", out, FIXTURE)
            self.assertEqual(report["status"], "END_TO_END_SHADOW_SIGNAL_ONLY")
            self.assertEqual(report["summary"]["gate_matched"], 6)
            self.assertEqual(report["summary"]["native_correct"], 6)
            replay = verify.replay(out / "report.json", FIXTURE)
            self.assertTrue(replay["structural_valid"])
            self.assertTrue(replay["end_to_end_shadow_signal"])
            self.assertEqual(replay["negative_gates"]["step2"], "UTILITY_FAIL")

    def test_wrong_c3_keeps_utility_fail_and_no_gate_match(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "fake"
            binding = {"model_sha256": verify.MODELS, "runner_sha256": verify.RUNNER_SHA}
            with patch.object(runner, "installed_artifacts", return_value=binding):
                with patch.object(runner, "run_row", side_effect=lambda h,i,f: fake_row(h,i,f,wrong=True)):
                    report = runner.run(Path(td) / "installed", out, FIXTURE)
            self.assertEqual(report["status"], "UTILITY_FAIL")
            self.assertEqual(report["summary"]["gate_matched"], 0)
            self.assertFalse(verify.replay(out / "report.json", FIXTURE)["end_to_end_shadow_signal"])

    def test_original_row_digest_tamper_rejected(self):
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

    def test_oracle_not_in_model_prompt_and_gate_no_authority(self):
        f = runner.load_fixture(FIXTURE)["fixtures"][0]
        with tempfile.TemporaryDirectory() as td:
            row = fake_row(Path(td) / "test", None, f)
        self.assertNotIn('"oracle"', dumps(row["native_prompt"]))
        self.assertEqual(row["final_agreement"]["delivery_authority"], 0)
        self.assertFalse(row["final_agreement"]["live_enabled"])
        self.assertEqual(row["final_agreement"]["store_writes"], 0)
        self.assertEqual(row["final_agreement"]["tool_dispatches"], 0)
        self.assertTrue(row["gate_store_unchanged"])

    def test_negative_gates_and_duplicate_scoring(self):
        self.assertEqual(runner.NEGATIVE, verify.NEGATIVE)
        self.assertEqual(runner.NEGATIVE["jepa_weight"], 0)
        f = runner.load_fixture(FIXTURE)["fixtures"][0]
        self.assertEqual(score('{"choice":"A","choice":"A","remaining":16}',
                               f["oracle"])["correct"], 0)


if __name__ == "__main__":
    unittest.main()
