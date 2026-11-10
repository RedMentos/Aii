"""Regression tests for fail-closed V13 contract changes."""
import copy
import unittest
from v13.contract_audit import validate, compare


def fixture():
    return {
        "schema_version": 1, "canon_sha256": "verified-canon",
        "canonical_architecture_complete": False,
        "components": [{
            "component_id": "B1", "name": "Detail", "current_mode": "PARTIAL",
            "implementation_files": ["v13/body_jepa.py", "v13/online_world.py"],
            "runtime_owner": "B1", "state_owner": "T8",
            "known_limits": "synthetic-only", "canon_source": "31.2"
        }]
    }


class ContractHardeningTests(unittest.TestCase):
    def test_unchanged(self):
        a = fixture()
        self.assertEqual(compare(a, copy.deepcopy(a)), [])

    def test_schema_version_change_requires_review(self):
        a = fixture(); b = copy.deepcopy(a)
        b["schema_version"] = 2
        self.assertIn("SCHEMA_CHANGE_REQUIRES_REVIEW", compare(a, b))

    def test_owner_and_source_change_require_review(self):
        a = fixture(); b = copy.deepcopy(a)
        b["components"][0]["runtime_owner"] = "C2"
        b["components"][0]["state_owner"] = "C2"
        b["components"][0]["canon_source"] = "revised"
        findings = compare(a, b)
        for key in ("RUNTIME_OWNER", "STATE_OWNER", "CANON_SOURCE"):
            self.assertIn(key + "_CHANGED_REQUIRES_REVIEW B1", findings)

    def test_replaced_file_requires_review(self):
        a = fixture(); b = copy.deepcopy(a)
        b["components"][0]["implementation_files"] = ["v13/new.py"]
        self.assertIn("IMPLEMENTATION_REFERENCES_CHANGED_REQUIRES_REVIEW B1", compare(a, b))

    def test_additive_file_does_not_flag(self):
        a = fixture(); b = copy.deepcopy(a)
        b["components"][0]["implementation_files"].append("v13/extra.py")
        self.assertEqual(compare(a, b), [])

    def test_reject_unsafe_paths(self):
        for path in ("../escape", "/absolute", "C:\\windows\\path", "", 4):
            with self.subTest(path=path):
                a = fixture()
                a["components"][0]["implementation_files"] = [path]
                with self.assertRaises(ValueError):
                    validate(a)

    def test_reject_missing_canon_and_owner(self):
        a = fixture(); a["canon_sha256"] = ""
        with self.assertRaises(ValueError):
            validate(a)
        a = fixture(); a["components"][0]["state_owner"] = None
        with self.assertRaises(ValueError):
            validate(a)


if __name__ == "__main__":
    unittest.main()
