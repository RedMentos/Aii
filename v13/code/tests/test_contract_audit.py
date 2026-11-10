"""Contract audit regression tests: no external dependencies."""
import copy
import unittest
from v13.contract_audit import validate, compare

def fixture():
    return {"schema_version": 1, "canon_sha256": "same",
            "canonical_architecture_complete": False,
            "components": [
                {"component_id": "A0", "name": "Raw", "current_mode": "PARTIAL",
                 "implementation_files": ["v13/store.py"], "runtime_owner": "A0",
                 "state_owner": "A0", "known_limits": "text only", "canon_source": "31.1"},
                {"component_id": "B1", "name": "Detail", "current_mode": "UNAVAILABLE",
                 "implementation_files": [], "runtime_owner": "B1",
                 "state_owner": "B1", "known_limits": "no weights", "canon_source": "31.2"}
            ]}

class ContractAuditTests(unittest.TestCase):
    def test_unchanged(self):
        a = fixture()
        self.assertEqual(compare(a, copy.deepcopy(a)), [])
    def test_removed_organ(self):
        a = fixture(); b = copy.deepcopy(a); b["components"].pop()
        self.assertIn("REMOVED_COMPONENT B1", compare(a, b))
    def test_unproven_promotion(self):
        a = fixture(); b = copy.deepcopy(a); b["components"][1]["current_mode"] = "IMPLEMENTED"
        self.assertTrue(any("MODE_CHANGE_REQUIRES_PROOF B1" in s for s in compare(a, b)))
    def test_duplicate_ids(self):
        a = fixture(); a["components"].append(copy.deepcopy(a["components"][0]))
        with self.assertRaises(ValueError): validate(a)
    def test_fabricated_completion(self):
        a = fixture(); a["canonical_architecture_complete"] = True
        with self.assertRaises(ValueError): validate(a)
    def test_lost_implementation(self):
        a = fixture(); b = copy.deepcopy(a); b["components"][0]["implementation_files"] = []
        self.assertIn("LOST_IMPLEMENTATION_REFERENCES A0", compare(a, b))
    def test_canon_change(self):
        a = fixture(); b = copy.deepcopy(a); b["canon_sha256"] = "different"
        self.assertIn("CANON_HASH_CHANGED_REQUIRES_REVIEW", compare(a, b))

if __name__ == "__main__":
    unittest.main()
