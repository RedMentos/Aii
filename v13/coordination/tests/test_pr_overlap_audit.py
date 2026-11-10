"""Tests for PR changed-file overlap detector; no network or external packages."""
import unittest

from v13.coordination.pr_overlap_audit import audit


class OverlapAuditTests(unittest.TestCase):
    def test_identifies_shared_path_only(self):
        snapshot = {"pull_requests": [
            {"number": 12, "files": ["a.py", "unique.py"]},
            {"number": 13, "files": ["a.py", "other.py"]},
        ]}
        self.assertEqual(audit(snapshot), [{"path": "a.py", "prs": [12, 13]}])

    def test_no_false_overlap_from_duplicate_path_within_one_pr(self):
        self.assertEqual(audit({"pull_requests": [
            {"number": 1, "files": ["x", "x"]}]}), [])

    def test_stable_order(self):
        self.assertEqual(audit({"pull_requests": [
            {"number": 9, "files": ["z", "a"]},
            {"number": 2, "files": ["z", "a"]}]}), [
                {"path": "a", "prs": [2, 9]},
                {"path": "z", "prs": [2, 9]},
            ])

    def test_reject_duplicate_pr_numbers(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit({"pull_requests": [
                {"number": 1, "files": []},
                {"number": 1, "files": []}]})

    def test_reject_unsafe_paths(self):
        for path in ["/tmp/x", "../escape", "a/../b", "", "a\\x00b"]:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    audit({"pull_requests": [{"number": 1, "files": [path]}]})

    def test_reject_malformed_entries(self):
        for payload in [{}, {"pull_requests": "wrong"},
                        {"pull_requests": [{"number": True, "files": []}]},
                        {"pull_requests": [{"number": 1, "files": "x"}]}]:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    audit(payload)


if __name__ == "__main__":
    unittest.main()
