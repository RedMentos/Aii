"""Run13J seed227 native pilot prereg and source-only preflight."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import run13j_c3_jef_native as j
from scripts import c2_body_disjoint_paired181_run11v as frozen
from v13.runtime import Runtime

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run13j_c3_jef_native_seed227_20261030.json"


class Run13JPreflight(unittest.TestCase):
    def test_frozen_fixture_six_sources_and_counterbalanced_arms(self):
        cases = j.load_fixture(FIXTURE)
        self.assertEqual(len(cases), 6)
        self.assertEqual(j.fixture_hash(cases), j.FIXTURE_SHA256)
        self.assertEqual([j.arm_order(i)[0] for i in range(6)],
                         ["RAW_C3", "JEF_C3"] * 3)
        projects = [c["project"] for c in cases]
        self.assertEqual(len(set(projects)), 6)
        prior = json.loads((FIXTURE.parent /
            "c2_body_fulltask_run13a_seed211_20261030.json").read_text())["cases"]
        self.assertFalse(set(projects) & {c["project"] for c in prior})
        for case in cases:
            source = frozen.prompt(case)
            self.assertNotIn(str(case["budget"] - case["a_cost"]), source)
            self.assertNotIn(str(case["budget"] - case["b_cost"]), source)

    def test_fixture_tamper_and_seed_change_fail_before_native(self):
        with TemporaryDirectory() as td:
            obj = json.loads(FIXTURE.read_text())
            obj["cases"][0]["budget"] += 1
            path = Path(td) / "tampered.json"
            path.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE"):
                j.load_fixture(path)
            obj = json.loads(FIXTURE.read_text())
            obj["seed"] = 228
            path.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE"):
                j.load_fixture(path)

    def test_actual_store_context_source_jef_prompt_without_native(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                case = j.load_fixture(FIXTURE)[0]
                before = runtime.store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
                with patch.object(runtime.pool, "get",
                                  side_effect=AssertionError("NATIVE_CALLED")):
                    result = j.prepare_case(runtime, case)
                self.assertEqual(result["linked"]["delivery_authority"], 0)
                self.assertEqual(result["linked"]["native_calls"], 0)
                self.assertIn("Indigo finishes sooner.", result["linked"]["answer"])
                self.assertIn("Amber leaves 462 Euro remaining.",
                              result["linked"]["answer"])
                self.assertIn("Indigo leaves 387 Euro remaining.",
                              result["linked"]["answer"])
                self.assertEqual(before, runtime.store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"])
            finally:
                runtime.close()

    def test_frozen_scoring_strict_full_and_negative_gates(self):
        case = j.load_fixture(FIXTURE)[0]
        answer = ("Project Pioneer227.\nAmber leaves 462 Euro remaining.\n"
                  "Indigo leaves 387 Euro remaining.\nIndigo finishes sooner.")
        good = j.score(case, answer, True)
        self.assertEqual(good["numeric"]["correct"], 2)
        self.assertTrue(good["faster_correct"])
        self.assertTrue(good["strict_full"])
        bad = j.score(case, answer, False)
        self.assertFalse(bad["strict_full"])
        self.assertEqual(bad["numeric"]["correct"], 0)
        wrong = j.score(case, answer.replace("Indigo finishes sooner.",
                                             "Amber finishes sooner."), True)
        self.assertFalse(wrong["strict_full"])


if __name__ == "__main__":
    unittest.main()
