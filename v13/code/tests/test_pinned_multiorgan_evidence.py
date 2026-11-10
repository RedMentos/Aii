"""Negative admissions for pinned multi-organ evidence."""
import unittest
from scripts.pinned_multiorgan_evidence import check


def fixture():
    sha = "a" * 40
    return {
        "claim": "REVIEW_ONLY",
        "gates": {key: "UNVERIFIED" for key in
                  ("STEP2_UTILITY", "B3_PROMOTION", "BODY_JEPA", "REDMI_PROOF")},
        "chains": {name: {"head_sha": sha, "status": "SHADOW",
                          "runs": [{"head_sha": sha, "conclusion": "success",
                                    "level": "synthetic",
                                    "url": "https://github.com/RedMentos/Aii/actions/runs/1"}]}
                   for name in ("core", "jepa", "qa", "perception")},
    }


class EvidenceTests(unittest.TestCase):
    def test_valid_synthetic_evidence_only_admits_review(self):
        self.assertEqual(check(fixture()), [])

    def test_stale_ci_refused(self):
        m = fixture()
        m["chains"]["jepa"]["runs"][0]["head_sha"] = "b" * 40
        self.assertIn("jepa: stale CI", check(m))

    def test_perception_without_ci_refused(self):
        m = fixture()
        m["chains"]["perception"]["runs"] = []
        self.assertIn("perception: missing CI", check(m))

    def test_promotion_refused(self):
        m = fixture()
        m["claim"] = "READY"
        self.assertIn("promotion forbidden", check(m))

    def test_negative_gate_override_refused(self):
        m = fixture()
        m["gates"]["BODY_JEPA"] = "PASS"
        self.assertIn("BODY_JEPA: negative gate overridden", check(m))


    def test_malformed_structures_fail_closed(self):
        cases = [
            (None, "manifest must be object"),
            ([], "manifest must be object"),
            (dict(fixture(), chains={"core": None, "jepa": {}, "qa": {}, "perception": {}}), "core: chain must be object"),
            (dict(fixture(), gates=None), "gates must be object"),
        ]
        for manifest, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, check(manifest))

    def test_invalid_runs_fail_closed(self):
        for runs, expected in [
            (None, "core: missing or invalid CI list"),
            ({"head_sha": "a" * 40}, "core: missing or invalid CI list"),
            ([None], "core: CI run must be object"),
            (["not a run"], "core: CI run must be object"),
        ]:
            with self.subTest(runs=runs):
                manifest = fixture()
                manifest["chains"]["core"]["runs"] = runs
                self.assertIn(expected, check(manifest))

if __name__ == "__main__":
    unittest.main()
