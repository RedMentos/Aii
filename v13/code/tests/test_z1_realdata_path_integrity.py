"""Independent fail-closed review of registered real_data file path integrity.

Software-only: a path within an evidence directory does not attest a real run.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13 import gates


class RealDataPathIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = Path(self.tmp.name) / "code"
        for rel in ("docs/proofs", "docs/canon", "tests", "v13"):
            (self.app / rel).mkdir(parents=True)
        (self.app.parent / "bench-results").mkdir()
        (self.app / "specs").mkdir()
        (self.app / "specs/gate-graph.json").write_text(
            json.dumps({"criteria": gates.spec()["criteria"]}))
        self.patch = mock.patch.object(gates, "APP", self.app)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        (self.app / "tests/test_evidence.py").write_text("not a run")
        (self.app / "docs/proofs/genuine.json").write_text('{"pass": true}')
        (self.app / "docs/canon/canon.md").write_text("# Canon")
        (self.app.parent / "bench-results/real.json").write_text('{"pass": true}')

    def checked(self, name):
        return gates.check({"real_data": [name]}, logged=set())["real_data"]

    def test_canonical_existing_files_in_all_three_roots(self):
        for name in ("docs/proofs/genuine.json", "docs/canon/canon.md", "../bench-results/real.json"):
            with self.subTest(name=name):
                self.assertTrue(self.checked(name)["present"])
                self.assertEqual(self.checked(name)["missing"], [])

    def test_directory_cannot_masquerade_as_real_data(self):
        (self.app / "docs/proofs/empty").mkdir()
        self.assertFalse(self.checked("docs/proofs/empty")["present"])

    def test_traversal_out_of_proofs_cannot_masquerade_as_real_data(self):
        for name in ("docs/proofs/../../tests/test_evidence.py",
                     "docs/proofs/../canon/canon.md",
                     "../bench-results/../code/tests/test_evidence.py",
                     "docs/canon/../../tests/test_evidence.py"):
            with self.subTest(name=name):
                self.assertFalse(self.checked(name)["present"])

    def test_symlinked_evidence_file_cannot_masquerade_as_real_data(self):
        (self.app / "docs/proofs/alias.json").symlink_to(self.app / "tests/test_evidence.py")
        self.assertFalse(self.checked("docs/proofs/alias.json")["present"])
        (self.app / "docs/proofs/internal.json").symlink_to(self.app / "docs/proofs/genuine.json")
        self.assertFalse(self.checked("docs/proofs/internal.json")["present"])

    def test_symlinked_intermediate_directory_cannot_masquerade_as_real_data(self):
        (self.app / "docs/proofs/link").symlink_to(self.app / "tests", target_is_directory=True)
        self.assertFalse(self.checked("docs/proofs/link/test_evidence.py")["present"])

    def test_symlinked_root_parent_cannot_masquerade_as_real_data(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "outside/proofs").mkdir(parents=True)
            (root / "outside/proofs/fake.json").write_text("{}")
            (root / "code").mkdir()
            (root / "code/docs").symlink_to(root / "outside", target_is_directory=True)
            with mock.patch.object(gates, "APP", root / "code"):
                self.assertFalse(gates._real_data_file("docs/proofs/fake.json"))

    def test_absolute_nonstring_null_and_missing_fail_closed(self):
        for name in (str(self.app / "docs/proofs/genuine.json"), None, 42,
                     "docs/proofs/ghost.json", "docs/proofs/" + chr(0) + "genuine.json",
                     "", "../bench-results"):
            with self.subTest(name=repr(name)):
                self.assertFalse(self.checked(name)["present"])

    def test_positive_verdict_cannot_override_invalid_real_data_path(self):
        criterion = {"code": None, "real_data": ["docs/proofs/../../tests/test_evidence.py"],
                     "persistence": None, "test": None, "telemetry": None,
                     "ablation": None, "limitations": None}
        one = {"title": "fake", "deps": [], **criterion,
               "verdict": [{"file": "docs/proofs/genuine.json", "path": "pass",
                            "op": "==", "value": True}]}
        spec = {"criteria": list(criterion), "gates": {"A": one}}
        with mock.patch.object(gates, "spec", return_value=spec), mock.patch.object(gates, "_code_logs", return_value=set()):
            ev = gates.evaluate()["A"]
            self.assertNotEqual(ev["status"], "GREEN")
            self.assertIn("real_data", ev["missing"])
            self.assertEqual(ev["verdict_failures"], [])
            spec["gates"]["A"]["real_data"] = ["docs/proofs/genuine.json"]
            self.assertEqual(gates.evaluate()["A"]["status"], "GREEN")


if __name__ == "__main__":
    unittest.main()
