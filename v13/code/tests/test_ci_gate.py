import unittest
from ci_gate import evaluate

SHA = "a" * 40


class TestEvidence(unittest.TestCase):
    def test_missing(self):
        self.assertEqual(evaluate({"workflow_runs": []}, SHA, ["required"]), {"required": "MISSING"})

    def test_other_commit_does_not_count(self):
        self.assertEqual(evaluate({"workflow_runs": [{"name": "x", "head_sha": "b"*40, "conclusion": "success", "status": "completed"}]}, SHA, ["x"])["x"], "MISSING")

    def test_success(self):
        self.assertEqual(evaluate({"workflow_runs": [{"name": "x", "head_sha": SHA, "conclusion": "success", "status": "completed"}]}, SHA, ["x"])["x"], "PASS")

    def test_failure_overrides_old_success(self):
        r = [{"name": "x", "head_sha": SHA, "conclusion": c, "status": "completed", "id": i} for i,c in [(1,"success"), (2,"failure")]]
        self.assertEqual(evaluate({"workflow_runs": r}, SHA, ["x"])["x"], "BLOCKED")

    def test_running_not_success(self):
        self.assertEqual(evaluate({"workflow_runs": [{"name": "x", "head_sha": SHA, "status": "in_progress"}]}, SHA, ["x"])["x"], "BLOCKED")

    def test_unpinned_rejected(self):
        with self.assertRaises(ValueError): evaluate({"workflow_runs": []}, "abc", ["x"])

    def test_malformed_rejected(self):
        with self.assertRaises(ValueError): evaluate({}, SHA, ["x"])


if __name__ == "__main__":
    unittest.main()
