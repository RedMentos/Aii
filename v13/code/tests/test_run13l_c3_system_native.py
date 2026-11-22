"""Run13L seed251 source-verified native C3 system contrast preflight; no model calls."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import run13l_c3_system_native as l
from scripts import run13l_c3_system_native_verify as verifier
from scripts import run13k_c3_copy_native as k
from scripts import run13j_c3_jef_native as j
from v13.runtime import Runtime

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/run13l_c3_system_seed251_20261030.json")


class Run13LPreflight(unittest.TestCase):
    def test_preregistered_disjoint_and_balanced(self):
        cases = l.load_fixture(FIXTURE)
        self.assertEqual(len(cases), 6)
        self.assertEqual(j.fixture_hash(cases), l.FIXTURE_SHA256)
        self.assertEqual([l.arm_order(i)[0] for i in range(6)],
                         ["SYSTEM_ABSTAIN", "SYSTEM_COPY"] * 3)
        prior = (j.load_fixture(FIXTURE.parent /
                 "run13j_c3_jef_native_seed227_20261030.json") +
                 k.load_fixture(FIXTURE.parent /
                 "run13k_c3_copy_seed239_20261030.json"))
        self.assertFalse({c["project"] for c in cases} &
                         {c["project"] for c in prior})

    def test_fixture_mutation_and_wrong_seed_fail(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "mutated.json"
            data = json.loads(FIXTURE.read_text())
            data["cases"][0]["budget"] += 1
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE"):
                l.load_fixture(p)
            data = json.loads(FIXTURE.read_text())
            data["seed"] = 239
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE"):
                l.load_fixture(p)

    def test_exact_same_user_prompt_but_different_system(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                case = l.load_fixture(FIXTURE)[0]
                before = runtime.store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
                with patch.object(runtime.pool, "get",
                                  side_effect=AssertionError("NATIVE_CALLED")):
                    data = j.prepare_case(runtime, case)
                answer = data["linked"]["answer"]
                self.assertIn("Juniper leaves 531 Euro remaining.", answer)
                self.assertIn("Silver leaves 345 Euro remaining.", answer)
                self.assertIn("Silver finishes sooner.", answer)
                self.assertEqual(l.prompt_for(data["linked"], "SYSTEM_ABSTAIN"),
                                 l.prompt_for(data["linked"], "SYSTEM_COPY"))
                self.assertEqual(l.prompt_for(data["linked"], "SYSTEM_COPY"),
                                 k.COPY_PREFIX + answer + k.COPY_SUFFIX)
                self.assertNotEqual(l.sha(j.SYSTEM), l.sha(l.SYSTEM_COPY))
                self.assertEqual(before, runtime.store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"])
            finally:
                runtime.close()

    def test_invalid_witness_or_arm_fails_before_native(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                data = j.prepare_case(runtime, l.load_fixture(FIXTURE)[1])
                linked = data["linked"]
                with self.assertRaisesRegex(ValueError, "SOURCE_BINDING"):
                    l.prompt_for(dict(linked, answer_sha256="0"*64),
                                 "SYSTEM_COPY")
                with self.assertRaisesRegex(ValueError, "ARM_RED"):
                    l.prompt_for(linked, "UNREGISTERED_ARM")
            finally:
                runtime.close()

    def test_exact_answer_score_and_no_false_promotion(self):
        case = l.load_fixture(FIXTURE)[0]
        answer = verifier.expected_answer(case)
        self.assertTrue(j.score(case, answer, True)["strict_full"])
        self.assertFalse(j.score(case, answer, False)["strict_full"])
        self.assertNotEqual(answer, "ABSTAIN.")
        self.assertEqual(l.MODEL_SHA, k.MODEL_SHA)

    def test_missing_native_raw_refused(self):
        with TemporaryDirectory() as td:
            p = Path(td)
            (p / "raw").mkdir()
            with self.assertRaisesRegex(ValueError, "RAW_COVERAGE"):
                verifier.verify(p, FIXTURE)


if __name__ == "__main__":
    unittest.main()
