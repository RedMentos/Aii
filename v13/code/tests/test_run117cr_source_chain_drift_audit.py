"""Run117CR exact source-chain drift audit tests; no acceptance modifications."""
import hashlib
import unittest

from scripts import run117cr_source_chain_drift_audit as A


class SourceChainDriftAudit(unittest.TestCase):
    def test_exact_small_source_set(self):
        expected = {"a.py": "a=1\n", "b.py": "b=2\n"}
        result = A.compare(expected, dict(expected), ("a.py", "b.py"))
        self.assertEqual(result["status"], "EXACT_REVIEWED_CHAIN")
        self.assertEqual(result["changed_files"], [])
        self.assertTrue(all(x["exact"] for x in result["files"]))
        self.assertFalse(result["acceptance_modified"])
        self.assertEqual(result["jepa_weight"], 0)

    def test_changed_single_file_reports_complete_deterministic_hashes(self):
        expected = {"a.py": "a=1\n", "b.py": "b=2\n"}
        actual = dict(expected, **{"b.py": "b=3\n"})
        first = A.compare(expected, actual, ("a.py", "b.py"))
        second = A.compare(expected, actual, ("a.py", "b.py"))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "CHAIN_DRIFT_REQUIRES_REVIEW")
        self.assertEqual(first["changed_files"], ["b.py"])
        self.assertEqual(first["checked_files"], 2)
        self.assertEqual(first["files"][0]["diff_lines"], 0)
        self.assertGreater(first["files"][1]["diff_lines"], 0)
        self.assertEqual(first["files"][1]["live_sha256"],
                         hashlib.sha256(b"b=3\n").hexdigest())
        text = "".join(A.unified_diffs(expected, actual, ("a.py", "b.py")))
        self.assertIn("-b=2", text)
        self.assertIn("+b=3", text)
        self.assertNotIn("-a=1", text)
        self.assertFalse(first["full_suite_promoted"])

    def test_incomplete_malformed_or_duplicate_source_set_red(self):
        valid = {"a.py": "a=1\n"}
        for expected, actual, names in (
            ({}, valid, ("a.py",)),
            (valid, {}, ("a.py",)),
            (valid, valid, ("a.py", "a.py")),
            (valid, {"a.py": b"binary"}, ("a.py",)),
            (valid, valid, ()),
        ):
            with self.subTest(expected=expected, actual=actual, names=names):
                with self.assertRaises(ValueError):
                    A.compare(expected, actual, names)
        with self.assertRaises(ValueError):
            list(A.unified_diffs(valid, {}, ("a.py",)))

    def test_actual_integrated_baseline_and_live_sources_are_read_only(self):
        before = {name: (A.ROOT / name).read_bytes() for name in A.NAMES}
        result, expected, actual = A.audit(A.ROOT)
        after = {name: (A.ROOT / name).read_bytes() for name in A.NAMES}
        self.assertEqual(before, after)
        self.assertEqual(set(expected), set(A.NAMES))
        self.assertEqual(set(actual), set(A.NAMES))
        self.assertEqual(result["checked_files"], len(A.NAMES))
        self.assertEqual(result["changed_files"],
                         [n for n in A.NAMES if expected[n] != actual[n]])
        self.assertIn(result["status"],
                      ("EXACT_REVIEWED_CHAIN", "CHAIN_DRIFT_REQUIRES_REVIEW"))
        self.assertEqual(result["native_calls"], 0)
        self.assertEqual(result["model_calls"], 0)
        self.assertFalse(result["whole_system_complete"])


if __name__ == "__main__":
    unittest.main()
