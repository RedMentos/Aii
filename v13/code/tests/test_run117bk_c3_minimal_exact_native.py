"""Run117BK real Store preflight for three-arm C3 minimal exact-source pilot."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run117bk_c3_minimal_exact_native as p
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.common import dumps

FIXTURE = Path(__file__).resolve().parents[1] / (
    "docs/fixtures/RUN117BK_C3_MINIMAL_EXACT_SEED1091.json")


class C3MinimalSourcePreflight(unittest.TestCase):
    def setUp(self):
        self.rows = p.fixture(FIXTURE)
        self.tmp = tempfile.TemporaryDirectory()
        self.r = QuoteRuntime(Path(self.tmp.name) / "home", self.rows[0])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def prepare(self, runtime, row):
        runtime.models = p._SyntheticBodyModelRevisions(runtime.models)
        prior = runtime.store.event(runtime.session, row["prior"])
        b2 = p._trusted_source_id(runtime, prior, "B2_GIST")
        current = runtime.store.event(runtime.session, row["current"])
        return p._prompts(runtime, prior, current, row, b2)

    def test_frozen_fixture_exact_sha_and_six_independent_oracles(self):
        self.assertEqual(sha256(FIXTURE.read_bytes()).hexdigest(), p.FIXTURE_SHA)
        self.assertEqual([r["id"] for r in self.rows], list(p.IDS))
        self.assertEqual([r["oracle"] for r in self.rows],
                         [{"choice": "A", "remaining": 10},
                          {"choice": "A", "remaining": 5},
                          {"choice": "NONE", "remaining": None},
                          {"choice": "B", "remaining": 10},
                          {"choice": "B", "remaining": 10},
                          {"choice": "NONE", "remaining": None}])
        self.assertEqual(p.SEED, 1091)
        self.assertEqual(p.ARMS, ("FULL_SOURCE_PACKET",
                                  "MINIMAL_EXACT_SPANS", "CURRENT_ONLY"))

    def test_all_six_actual_store_three_arm_exact_source_and_no_answer_leak(self):
        for row in self.rows:
            with self.subTest(project=row["id"]), tempfile.TemporaryDirectory() as td:
                runtime = QuoteRuntime(Path(td) / "home", row)
                try:
                    prompts, bridge = self.prepare(runtime, row)
                    self.assertEqual(bridge["status"], "SHADOW_C3_SOURCE_ID_EVIDENCE_READY")
                    full, minimal, current = [prompts[a] for a in p.ARMS]
                    self.assertEqual([m["role"] for m in full], ["system", "user"])
                    self.assertEqual(full[0], minimal[0])
                    self.assertEqual(full[0], current[0])
                    packet = json.loads(full[1]["content"])
                    self.assertEqual([x["role"] for x in packet["body_observations"]],
                                     ["B2_GIST", "B1_DETAIL"])
                    self.assertEqual([x["exact_source_excerpt"]
                                      for x in packet["body_observations"]],
                                     [row["policy_span"], row["option_span"]])
                    self.assertIn("Binding policy (exact source):\n" + row["policy_span"],
                                  minimal[1]["content"])
                    self.assertIn("Current options (exact source):\n" + row["option_span"],
                                  minimal[1]["content"])
                    self.assertIn(row["option_span"], current[1]["content"])
                    self.assertNotIn(row["policy_span"], current[1]["content"])
                    self.assertNotIn("Archive memo", minimal[1]["content"])
                    self.assertNotIn("Archive memo", current[1]["content"])
                    self.assertIsNone(packet["typed_jef_candidate"])
                    self.assertEqual(packet["typed_candidate_authority"], 0)
                    self.assertNotIn("oracle", dumps(prompts))
                    self.assertFalse(bridge["output_committed"])
                    self.assertEqual(bridge["learning_authority"], 0)
                    self.assertEqual(runtime.store.one(
                        "SELECT COUNT(*) AS n FROM actions")["n"], 0)
                finally:
                    runtime.close()

    def test_no_native_body_and_synthetic_revision(self):
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_BODY_CALLED")):
            prompts, bridge = self.prepare(self.r, self.rows[0])
        self.assertEqual(set(prompts), set(p.ARMS))
        from v13.b1b2_source_id_quote_candidate import KIND
        packets = self.r.store.rows(
            "SELECT payload FROM packets WHERE kind=?", (KIND,))
        self.assertEqual(len(packets), 2)
        self.assertTrue(all(json.loads(x["payload"])["model_revision"] ==
                            p.SYNTHETIC_BODY_REVISION for x in packets))

    def test_stale_event_and_fixture_mutation_refused(self):
        prior = self.r.store.event(self.r.session, self.rows[0]["prior"])
        self.r.store.event(self.r.session, self.rows[0]["current"])
        with self.assertRaises(ValueError):
            p._trusted_source_id(self.r, prior, "B2_GIST")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.json"
            path.write_bytes(FIXTURE.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "RUN117BK_FIXTURE_SHA_RED"):
                p.fixture(path)

    def test_strict_current_only_abstention_scoring(self):
        from scripts.run47_jef_c3_typed_receiver_native import score
        self.assertEqual(score('{"choice":"NONE","remaining":null}',
                               {"choice": "NONE", "remaining": None})["correct"], 1)
        self.assertEqual(score('{"choice":"NONE","remaining":0}',
                               {"choice": "NONE", "remaining": None})["correct"], 0)
        self.assertEqual(score('{"choice":"A","remaining":10}',
                               {"choice": "NONE", "remaining": None})["correct"], 0)
        self.assertEqual(score('{"choice":"A","remaining":10}',
                               {"choice": "A", "remaining": 10})["correct"], 1)

    def test_summary_requires_eighteen_final_reaped_calls_no_promotion(self):
        self.assertEqual(p._summarize({"rows": [], "native_c3_calls": 0}), p.RED)
        report = {"rows": [], "native_c3_calls": 18}
        for row in self.rows:
            arms = [{"arm": arm, "status": "RECORDED",
                     "native_final": True, "process_reaped": True,
                     "native_metrics": {"actual_model": p.C3_FILE},
                     "score": {"correct": 1}}
                    for arm in p.ARMS]
            report["rows"].append({"id": row["id"], "status": "RECORDED",
                                   "closed_store_ok": True, "no_live_output": True,
                                   "arms": arms})
        self.assertEqual(p._summarize(report), p.GOOD[1])
        # Minimal cannot beat FULL by two if both are 6/6.
        self.assertFalse(report["exploratory_minimal_source_signal"])
        for row in report["rows"]:
            row["arms"][0]["score"]["correct"] = 0
        self.assertEqual(p._summarize(report), p.GOOD[0])
        report["rows"][0]["arms"][1]["process_reaped"] = False
        self.assertEqual(p._summarize(report), p.RED)


if __name__ == "__main__":
    unittest.main()
