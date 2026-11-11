"""Synthetic GitHub API reconciliation tests; no network calls."""
import unittest
from scripts.verify_actions_evidence import verify

SHA = "a" * 40
URL = "https://github.com/RedMentos/Aii/actions/runs/123"


def manifest():
    return {
        "claim": "REVIEW_ONLY",
        "gates": {g: "UNVERIFIED" for g in ("STEP2_UTILITY", "B3_PROMOTION", "BODY_JEPA", "REDMI_PROOF")},
        "chains": {organ: {"head_sha": SHA, "status": "SHADOW",
                          "runs": [{"head_sha": SHA, "conclusion": "success", "url": URL, "level": "synthetic"}]}
                   for organ in ("core", "jepa", "qa", "perception")},
    }


def run():
    return {"id": 123, "head_sha": SHA, "status": "completed", "conclusion": "success",
            "html_url": URL, "repository": {"full_name": "RedMentos/Aii"}}


class ReconcileTests(unittest.TestCase):
    def test_exact_success_and_cached_fetch(self):
        calls = []
        def fetch(i):
            calls.append(i)
            return run()
        self.assertEqual(verify(manifest(), fetch), [])
        self.assertEqual(calls, [123])

    def test_forged_and_stale_runs_fail_closed(self):
        for field, value in (("id", 124), ("head_sha", "b" * 40),
                             ("status", "queued"), ("conclusion", "failure"),
                             ("html_url", URL + "/evil")):
            with self.subTest(field=field):
                item = run()
                item[field] = value
                self.assertTrue(verify(manifest(), lambda _: item))
        item = run()
        item["repository"] = {"full_name": "attacker/Aii"}
        self.assertTrue(verify(manifest(), lambda _: item))

    def test_unavailable_api_and_malformed_response_fail_closed(self):
        def fail(_):
            raise TimeoutError("offline")
        self.assertTrue(verify(manifest(), fail))
        self.assertTrue(verify(manifest(), lambda _: None))

    def test_manifest_rejected_before_network(self):
        data = manifest()
        data["claim"] = "ACTIVE"
        def fail(_):
            raise AssertionError("must not fetch")
        self.assertIn("promotion forbidden", verify(data, fail))


if __name__ == "__main__":
    unittest.main()
