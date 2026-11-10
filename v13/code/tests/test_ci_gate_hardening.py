"""Additional fail-closed CI evidence regression tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ci_gate import evaluate

SHA = "a" * 40


class TestCiEvidenceHardening(unittest.TestCase):
    def test_empty_required_is_not_success(self):
        with self.assertRaises(ValueError):
            evaluate({"workflow_runs": []}, SHA, [])

    def test_nonhex_commit_rejected(self):
        with self.assertRaises(ValueError):
            evaluate({"workflow_runs": []}, "z" * 40, ["x"])

    def test_malformed_run_rejected(self):
        with self.assertRaises(ValueError):
            evaluate({"workflow_runs": [None]}, SHA, ["x"])

    def test_duplicate_required_rejected(self):
        with self.assertRaises(ValueError):
            evaluate({"workflow_runs": []}, SHA, ["x", "x"])

    def test_later_success_cannot_mask_failed_run(self):
        runs = [
            {"name": "x", "head_sha": SHA, "status": "completed", "conclusion": "failure", "id": 1},
            {"name": "x", "head_sha": SHA, "status": "completed", "conclusion": "success", "id": 2},
        ]
        self.assertEqual(evaluate({"workflow_runs": runs}, SHA, ["x"])["x"], "BLOCKED")

    def test_running_attempt_blocks(self):
        runs = [
            {"name": "x", "head_sha": SHA, "status": "completed", "conclusion": "success", "id": 1},
            {"name": "x", "head_sha": SHA, "status": "in_progress", "id": 2},
        ]
        self.assertEqual(evaluate({"workflow_runs": runs}, SHA, ["x"])["x"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
