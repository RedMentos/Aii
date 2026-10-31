"""Run117BG real Store preflight for new C3 causal-prior pilot; no native calls."""
from __future__ import annotations
import copy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run117bg_c3_source_only_native as pilot
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.common import dumps

FIXTURE = Path(__file__).resolve().parents[1] / (
    "docs/fixtures/RUN117BG_C3_SOURCE_ONLY_SEED1081.json")


class C3CausalPriorPreflight(unittest.TestCase):
    def setUp(self):
        self.rows = pilot.fixture(FIXTURE)
        self.tmp = tempfile.TemporaryDirectory()
        self.r = QuoteRuntime(Path(self.tmp.name) / "home", self.rows[0])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def prepare(self, runtime, row):
        prior = runtime.store.event(runtime.session, row["prior"])
        b2 = pilot._trusted_source_id(runtime, prior, "B2_GIST")
        current = runtime.store.event(runtime.session, row["current"])
        prompts, bridge = pilot._prompts(runtime, prior, current, row, b2)
        return prompts, bridge

    def test_frozen_six_row_fixture_and_oracle_recompute(self):
        self.assertEqual(sha256(FIXTURE.read_bytes()).hexdigest(), pilot.FIXTURE_SHA)
        self.assertEqual([r["id"] for r in self.rows], list(pilot.IDS))
        self.assertEqual([r["oracle"] for r in self.rows],
                         [{"choice": "A", "remaining": 40},
                          {"choice": "A", "remaining": 10},
                          {"choice": "NONE", "remaining": None},
                          {"choice": "B", "remaining": 30},
                          {"choice": "B", "remaining": 40},
                          {"choice": "NONE", "remaining": None}])

    def test_all_six_actual_store_paired_prompts_no_typed_leak(self):
        for row in self.rows:
            with self.subTest(project=row["id"]), tempfile.TemporaryDirectory() as td:
                runtime = QuoteRuntime(Path(td) / "home", row)
                try:
                    prompts, bridge = self.prepare(runtime, row)
                    self.assertEqual(bridge["status"], "SHADOW_C3_SOURCE_ID_EVIDENCE_READY")
                    both, current = [prompts[a] for a in pilot.ARMS]
                    self.assertEqual([m["role"] for m in both], ["system", "user"])
                    a = json.loads(both[1]["content"])
                    b = json.loads(current[1]["content"])
                    self.assertEqual([x["role"] for x in a["body_observations"]],
                                     ["B2_GIST", "B1_DETAIL"])
                    self.assertEqual([x["role"] for x in b["body_observations"]],
                                     ["B1_DETAIL"])
                    self.assertEqual(a["body_observations"][0]["exact_source_excerpt"],
                                     row["policy_span"])
                    self.assertEqual(b["body_observations"][0]["exact_source_excerpt"],
                                     row["option_span"])
                    self.assertNotIn(row["policy_span"], dumps(current))
                    self.assertIsNone(a["typed_jef_candidate"])
                    self.assertIsNone(b["typed_jef_candidate"])
                    self.assertNotIn("oracle", dumps(prompts))
                    self.assertFalse(bridge["output_committed"])
                    self.assertEqual(bridge["learning_authority"], 0)
                    self.assertEqual(runtime.store.one(
                        "SELECT COUNT(*) AS n FROM actions")["n"], 0)
                finally:
                    runtime.close()

    def test_selector_is_synthetic_and_no_native_body(self):
        with unittest.mock.patch.object(self.r.pool, "get",
                                        side_effect=AssertionError("NATIVE_BODY_CALLED")):
            prompts, bridge = self.prepare(self.r, self.rows[0])
        self.assertEqual(bridge["status"], "SHADOW_C3_SOURCE_ID_EVIDENCE_READY")
        self.assertEqual(set(prompts), set(pilot.ARMS))

    def test_wrong_event_order_refuses(self):
        prior = self.r.store.event(self.r.session, self.rows[0]["prior"])
        current = self.r.store.event(self.r.session, self.rows[0]["current"])
        with self.assertRaises(ValueError):
            pilot._trusted_source_id(self.r, prior, "B2_GIST")

    def test_modified_fixture_hash_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "changed.json"
            p.write_bytes(FIXTURE.read_bytes().replace(b"Sirius", b"Syrius"))
            with self.assertRaisesRegex(ValueError, "RUN117BG_FIXTURE_SHA_RED"):
                pilot.fixture(p)

    def test_score_controls_are_exact_not_partial(self):
        from scripts.run47_jef_c3_typed_receiver_native import score
        self.assertEqual(score('{"choice":"NONE","remaining":null}',
                               {"choice": "NONE", "remaining": None})["correct"], 1)
        self.assertEqual(score('{"choice":"A","remaining":40}',
                               {"choice": "NONE", "remaining": None})["correct"], 0)
        self.assertEqual(score('{"choice":"A","remaining":41}',
                               {"choice": "A", "remaining": 40})["correct"], 0)
        self.assertEqual(score('{"choice":"A","remaining":40,"extra":1}',
                               {"choice": "A", "remaining": 40})["correct"], 0)

    def test_summary_no_promotion_and_structural_refusal(self):
        self.assertEqual(pilot._summarize({"rows": [], "native_c3_calls": 0}),
                         pilot.RED)
        report = {"rows": [], "native_c3_calls": 12}
        for i, row in enumerate(self.rows):
            arms = []
            for arm in pilot.ARMS:
                arms.append({"arm": arm, "status": "RECORDED", "native_final": True,
                             "process_reaped": True, "native_metrics": {
                                 "actual_model": pilot.C3_FILE},
                             "score": {"correct": 1}})
            report["rows"].append({"id": row["id"], "status": "RECORDED",
                                   "closed_store_ok": True, "no_live_output": True,
                                   "arms": arms})
        self.assertEqual(pilot._summarize(report), pilot.GOOD[0])
        self.assertTrue(report["exploratory_causal_prior_signal"])
        report["rows"][0]["arms"][0]["process_reaped"] = False
        self.assertEqual(pilot._summarize(report), pilot.RED)


if __name__ == "__main__":
    unittest.main()
