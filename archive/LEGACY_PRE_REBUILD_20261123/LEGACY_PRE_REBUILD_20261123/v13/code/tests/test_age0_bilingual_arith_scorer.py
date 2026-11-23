"""Software-only counterexamples for frozen bilingual Age0 arithmetic scoring."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts import age0_bilingual_arith_scorer as S


class HeldoutScorerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.items = S.fixture()
        self.manifest = {
            "schema": "v13.age0.bilingual_numeric_answers.v1",
            "prompt_git_blob": S.CANDIDATE_PROMPT,
            "source_commit": "b99ce3ef8dd772130c3a56a1ec02e7ea203f3b5c",
            "model_catalog_git_blob": S.CATALOG_BLOB,
            "rows": [{
                "id": item["id"], "prompt": item["prompt"],
                "answer": ("The answer is " + item["expected"] + ".")
                          if item["kind"] == "numeric" else "Not stated in the note.",
                "status": "FINAL", "runner_role": "B1_DETAIL",
                "runner_model_sha256": S.ROLE_MODELS["B1_DETAIL"],
                "tool_call": None, "tool_shadow": None,
                "learning_mode": "RECORD_ONLY", "jepa_weight": 0
            } for item in self.items]
        }

    def tearDown(self):
        self.tmp.cleanup()

    def save(self, data=None, name="answers.json"):
        path = self.root / name
        path.write_text(json.dumps(self.manifest if data is None else data), encoding="utf-8")
        return path

    def test_frozen_fixture_and_author_labels(self):
        self.assertEqual(len(self.items), 16)
        self.assertEqual(sum(x["kind"] == "numeric" for x in self.items), 12)
        self.assertEqual(sum(x["kind"] == "unsupported" for x in self.items), 4)
        self.assertNotIn("Budget 120 Euro. Berechne die Hälfte.",
                         [x["prompt"] for x in self.items])

    def test_lexical_proxy_exactness_and_conflicting_numbers(self):
        item = self.items[0]
        self.assertTrue(S.numeric_proxy("Half of 74 is 37.", item))
        self.assertTrue(S.numeric_proxy("37.0", item))
        self.assertFalse(S.numeric_proxy("137", item))
        self.assertFalse(S.numeric_proxy("37 and 39", item))
        self.assertFalse(S.numeric_proxy("It is not 37.", item))
        self.assertFalse(S.numeric_proxy("Maybe 37.", item))
        self.assertFalse(S.numeric_proxy("74", item))
        fractional = self.items[2]
        self.assertTrue(S.numeric_proxy("67,5", fractional))
        self.assertFalse(S.numeric_proxy("675", fractional))

    def test_offline_scoring_never_promotes_gates(self):
        report = S.evaluate(self.save())
        self.assertEqual(report["evidence_kind"], "SOFTWARE_OFFLINE_SCORER_ONLY")
        self.assertFalse(report["external_native_claims_verified"])
        self.assertFalse(report["whole_system_complete"])
        self.assertFalse(report["age0_tool_authority"])
        self.assertEqual(report["step2_utility"], "FAIL")
        self.assertEqual(report["b3_l1"], "FAIL")
        self.assertEqual(report["body_jepa"], "UNAVAILABLE")
        self.assertEqual(report["runs"][0]["counts"]["numeric_proxy_match"], 12)
        self.assertEqual(report["runs"][0]["counts"]["unsupported_uncertainty_marker"], 4)
        self.assertNotIn("answer", report["runs"][0]["items"][0])

    def test_wrong_numeric_and_unsupported_name_count_as_fail(self):
        self.manifest["rows"][0]["answer"] = "The result is 137."
        self.manifest["rows"][12]["answer"] = "Bob."
        result = S.evaluate(self.save())["runs"][0]["counts"]
        self.assertEqual(result["numeric_proxy_match"], 11)
        self.assertEqual(result["unsupported_uncertainty_marker"], 3)

    def test_missing_duplicate_unknown_and_question_drift_fail_closed(self):
        for mutate in (
            lambda d: d["rows"].pop(),
            lambda d: d["rows"].append(dict(d["rows"][0])),
            lambda d: d["rows"][0].update(id="unregistered"),
            lambda d: d["rows"][0].update(prompt="Changed question"),
        ):
            d = json.loads(json.dumps(self.manifest))
            mutate(d)
            with self.assertRaises(ValueError):
                S.evaluate(self.save(d))

    def test_age0_and_final_metadata_fail_closed(self):
        for field, bad in (
            ("status", "PARTIAL"), ("runner_role", "UNKNOWN"),
            ("tool_call", {"tool": "calc"}), ("learning_mode", "COMMIT"),
            ("jepa_weight", 0.1), ("jepa_weight", True),
            ("answer", ""), ("answer", None),
        ):
            d = json.loads(json.dumps(self.manifest))
            d["rows"][0][field] = bad
            with self.subTest(field=field, bad=bad), self.assertRaises(ValueError):
                S.evaluate(self.save(d))

    def test_unpinned_source_prompt_and_model_identity_rejected(self):
        for field, bad in (
            ("prompt_git_blob", "0"*40), ("source_commit", "unknown"),
            ("model_catalog_git_blob", "unknown"), ("schema", "bad"),
        ):
            d = json.loads(json.dumps(self.manifest))
            d[field] = bad
            with self.subTest(field=field), self.assertRaises(ValueError):
                S.evaluate(self.save(d))

    def test_pairing_requires_distinct_prompts_and_same_model(self):
        first = self.save()
        baseline = json.loads(json.dumps(self.manifest))
        baseline["prompt_git_blob"] = S.BASELINE_PROMPT
        second = self.save(baseline, "baseline.json")
        report = S.evaluate(first, second)
        self.assertEqual(len(report["runs"]), 2)
        with self.assertRaises(ValueError):
            S.evaluate(first, first)
        baseline["rows"][0]["runner_model_sha256"] = "0"*64
        with self.assertRaises(ValueError):
            S.evaluate(first, self.save(baseline, "other-model.json"))
        baseline["rows"][0]["runner_role"] = "C3_LANGUAGE"
        baseline["rows"][0]["runner_model_sha256"] = S.ROLE_MODELS["C3_LANGUAGE"]
        changed = S.evaluate(first, self.save(baseline, "other-route.json"))
        self.assertEqual(changed["paired_route_changed_ids"], ["a01"])

    def test_runner_role_model_hash_mismatch_rejected(self):
        self.manifest["rows"][0]["runner_model_sha256"] = S.ROLE_MODELS["C3_LANGUAGE"]
        with self.assertRaises(ValueError):
            S.evaluate(self.save())

    def test_refuse_to_overwrite_existing_score(self):
        path = self.save()
        out = self.root / "score.json"
        out.write_text("existing")
        with self.assertRaises(FileExistsError):
            S.main(["--answers", str(path), "--out", str(out)])
        self.assertEqual(out.read_text(), "existing")


if __name__ == "__main__":
    unittest.main()
