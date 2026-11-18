"""Regression: acceptance verifier must not follow evidence symlinks.

Run: python -m unittest discover -s v13/code/tests -p 'test_verify_acceptance_artifact_boundary.py'
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_acceptance.py"
spec = importlib.util.spec_from_file_location("v13_verify_acceptance", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ArtifactBoundaryTests(unittest.TestCase):
    def test_regular_file_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proof.json"
            path.write_text("{}")
            self.assertTrue(module.regular_artifact(path))

    def test_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(module.regular_artifact(Path(directory) / "missing.json"))

    def test_external_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside.json"
            outside.write_text('{"status":"PASS"}')
            evidence = root / "evidence"
            evidence.mkdir()
            link = evidence / "proof.json"
            link.symlink_to(outside)
            self.assertFalse(module.regular_artifact(link))
            with self.assertRaisesRegex(ValueError, "symlinked"):
                module.verify(link, evidence)

    def test_broken_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / "proof.json"
            link.symlink_to("missing.json")
            self.assertFalse(module.regular_artifact(link))


if __name__ == "__main__":
    unittest.main()
