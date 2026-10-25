"""Run184 independent strict arithmetic SHADOW software tests."""
import importlib.util
import json
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / "scripts/run184_age0d_strict_shadow.py"
spec = importlib.util.spec_from_file_location("run184", SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture():
    return {"prior": "Project P. Budget 100 euros.",
            "current": "Option A: cost 40 euros. Option B: cost 70 euros."}


def answer(a=60, b=30):
    return json.dumps({"options": [{"entity": "A", "remaining": a},
                                   {"entity": "B", "remaining": b}]})


class StrictShadow(unittest.TestCase):
    def test_correct(self):
        self.assertEqual(m.check(fixture(), answer())["status"], "SHADOW_AGREES")

    def test_wrong_and_refs(self):
        f = fixture()
        result = m.check(f, answer(1, 30))
        self.assertEqual(result["status"], "SHADOW_ARITHMETIC_MISMATCH")
        self.assertEqual(result["mismatches"]["A"]["expected"], 60)
        for ref in [result["source_refs"]["budget"], *result["source_refs"]["options"].values()]:
            self.assertEqual(f[ref["field"]][ref["char_start"]:ref["char_end"]], ref["quote"])

    def test_updated_budget(self):
        f = fixture()
        f["current"] += " Updated rules, overriding the earlier rules: budget 75 euros."
        self.assertEqual(m.check(f, answer(35, 5))["status"], "SHADOW_AGREES")

    def test_decoy_abstains(self):
        f = fixture()
        f["current"] = "Outdated example: " + f["current"] + " Correct costs are A=30 euros and B=60 euros."
        self.assertEqual(m.check(f, answer(70, 40))["status"], "ABSTAIN")

    def test_duplicate_json_key_abstains(self):
        raw = '{"options":[{"entity":"A","remaining":60,"remaining":1},{"entity":"B","remaining":30}]}'
        self.assertEqual(m.check(fixture(), raw)["status"], "ABSTAIN")

    def test_extra_json_claim_abstains(self):
        j = json.loads(answer())
        j["summary"] = "remaining A 0"
        self.assertEqual(m.check(fixture(), json.dumps(j))["status"], "ABSTAIN")

    def test_ambiguous_budget_abstains(self):
        f = fixture()
        f["prior"] += " Budget 120 euros."
        self.assertEqual(m.check(f, answer())["status"], "ABSTAIN")

    def test_unsupported_monetary_source_abstains(self):
        f = fixture()
        f["current"] += " A may also cost 35 euros."
        self.assertEqual(m.check(f, answer())["status"], "ABSTAIN")

    def test_bad_type_and_nan_abstain(self):
        self.assertEqual(m.check({"prior": None, "current": ""}, answer())["status"], "ABSTAIN")
        self.assertEqual(m.check(fixture(), '{"options":NaN}')["status"], "ABSTAIN")

    def test_authority_zero(self):
        for raw in (answer(), answer(0, 0), "garbage"):
            result = m.check(fixture(), raw)
            self.assertTrue(result["shadow_only"])
            for key in ("delivery_authorized", "learning_authorized", "age_reopen_authorized"):
                self.assertFalse(result[key])

    def test_original_run183_counterexamples_if_present(self):
        """Document pre-existing non-abstention; do not silently change Run183."""
        old = Path(__file__).resolve().parents[1] / "scripts/run183_step2_arithmetic_shadow_replay.py"
        if not old.exists():
            self.skipTest("exact Run183 source unavailable in isolated local copy")
        ospec = importlib.util.spec_from_file_location("run183_exact", old)
        original = importlib.util.module_from_spec(ospec)
        ospec.loader.exec_module(original)
        f = fixture()
        f["current"] = "Outdated example: " + f["current"] + " Correct costs are A=30 euros and B=60 euros."
        self.assertEqual(original.check_answer(f, answer(70, 40))["status"], "SHADOW_ARITHMETIC_MISMATCH")
        raw = '{"options":[{"entity":"A","remaining":60,"remaining":1},{"entity":"B","remaining":30}]}'
        self.assertEqual(original.check_answer(fixture(), raw)["status"], "SHADOW_ARITHMETIC_MISMATCH")

    def test_type_fuzz_does_not_raise(self):
        cases = [None, False, 3, [], {}, {"prior": 1, "current": ""},
                 {"prior": "Budget 100 euros.", "current": None}]
        raws = [None, False, 1, [], {}, "", "NaN", "[]", "null", "{", answer()]
        for f in cases:
            for raw in raws:
                with self.subTest(f=f, raw=raw):
                    self.assertEqual(m.check(f, raw)["status"], "ABSTAIN")

    def test_balanced_cohort(self):
        report = m.audit(m.cohort())
        self.assertEqual(report["rows"], 120)
        self.assertEqual(report["counts"], {"correct": 40, "wrong": 40, "decoy": 20, "duplicate_json": 20})
        self.assertEqual(report["verdict"], "SOFTWARE_GUARD_PASS")
        self.assertFalse(report["v13_complete"])


if __name__ == "__main__":
    unittest.main()
