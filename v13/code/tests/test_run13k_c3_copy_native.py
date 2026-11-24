"""Run13K prospective seed239 source/copy/native-proof preflight; no model calls."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import run13k_c3_copy_native as k
from scripts import run13k_c3_copy_native_verify as verify
from scripts import run13j_c3_jef_native as j
from v13.runtime import Runtime

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/run13k_c3_copy_seed239_20261030.json")


class Run13KPreflight(unittest.TestCase):
    def test_disjoint_preregistered_fixture_and_counterbalance(self):
        cases = k.load_fixture(FIXTURE)
        self.assertEqual(len(cases), 6)
        self.assertEqual(j.fixture_hash(cases), k.FIXTURE_SHA256)
        self.assertEqual([k.arm_order(i)[0] for i in range(6)],
                         ["ORIGINAL_SHADOW", "COPY_DIRECT"] * 3)
        prior = j.load_fixture(FIXTURE.parent /
            "run13j_c3_jef_native_seed227_20261030.json")
        self.assertFalse({c["project"] for c in cases} &
                         {c["project"] for c in prior})

    def test_tampered_fixture_and_wrong_seed_refused(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "fixture.json"
            obj = json.loads(FIXTURE.read_text())
            obj["cases"][0]["a_cost"] += 1
            p.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE"):
                k.load_fixture(p)
            obj = json.loads(FIXTURE.read_text())
            obj["seed"] = 227
            p.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE"):
                k.load_fixture(p)

    def test_store_context_verified_answer_and_no_native_call(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                case = k.load_fixture(FIXTURE)[0]
                before = runtime.store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
                with patch.object(runtime.pool, "get",
                                  side_effect=AssertionError("NATIVE_CALLED")):
                    data = j.prepare_case(runtime, case)
                answer = data["linked"]["answer"]
                self.assertIn("Moss leaves 444 Euro remaining.", answer)
                self.assertIn("Flint leaves 387 Euro remaining.", answer)
                self.assertIn("Flint finishes sooner.", answer)
                original = k.prompt_for(data["linked"], "ORIGINAL_SHADOW")
                copied = k.prompt_for(data["linked"], "COPY_DIRECT")
                self.assertEqual(original, data["linked"]["candidate_prompt"])
                self.assertEqual(copied, k.COPY_PREFIX + answer + k.COPY_SUFFIX)
                self.assertNotEqual(k.sha(original), k.sha(copied))
                self.assertEqual(before, runtime.store.one(
                    "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"])
            finally:
                runtime.close()

    def test_source_binding_tamper_abstains_before_native(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                data = j.prepare_case(runtime, k.load_fixture(FIXTURE)[1])
                linked = data["linked"]
                for key, bad in (("answer_sha256", "0" * 64),
                                 ("delivery_authority", 1),
                                 ("candidate_prompt", "forged"),
                                 ("context_authority", 1)):
                    forged = dict(linked, **{key: bad})
                    with self.assertRaisesRegex(ValueError, "SOURCE_BINDING"):
                        k.prompt_for(forged, "COPY_DIRECT")
                with self.assertRaisesRegex(ValueError, "ARM_RED"):
                    k.prompt_for(linked, "RAW_C3")
            finally:
                runtime.close()

    def test_exact_copy_strict_and_frozen_numeric_scoring(self):
        case = k.load_fixture(FIXTURE)[0]
        answer = verify.expected_answer(case)
        self.assertEqual(k.sha(answer), k.sha(answer))
        self.assertEqual(j.score(case, answer, True)["numeric"]["correct"], 2)
        self.assertTrue(j.score(case, answer, True)["strict_full"])
        self.assertFalse(j.score(case, answer, False)["strict_full"])
        self.assertNotEqual(answer + "\n", answer)

    def test_verifier_missing_raw_rejected_and_negative_gate(self):
        with TemporaryDirectory() as td:
            p = Path(td)
            (p / "raw").mkdir()
            with self.assertRaisesRegex(ValueError, "RAW_COVERAGE"):
                verify.verify(p, FIXTURE)
        self.assertEqual(k.MODEL_SHA, jverify_sha())


def jverify_sha():
    from scripts.run13j_c3_jef_native_verify import MODEL_SHA
    return MODEL_SHA


if __name__ == "__main__":
    unittest.main()
