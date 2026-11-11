"""Integration-stage smoke against REAL pinned repository sources, not mock builders.

Run: cd v13/code && python -m unittest -v tests.test_integrated_stage_real_smoke
This tests staging/pins/compilation/isolation only; it is NOT a multi-organ turn.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

CODE_DIR = Path(__file__).resolve().parents[1]
STAGER = CODE_DIR / "scripts" / "stage_integrated_candidate.py"
spec = importlib.util.spec_from_file_location("v13_stage_smoke", STAGER)
stage_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage_module)


class RealIntegratedStageSmoke(unittest.TestCase):
    def test_real_pinned_builder_stages_compilable_isolated_candidate(self):
        # Unlike the mock staging tests, this exercises the actual nested
        # source-pin builders and their composed replacement payloads.
        source_runtime = CODE_DIR / "v13" / "runtime.py"
        before = hashlib.sha256(source_runtime.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix="v13-real-stage-qa-") as td:
            dest = Path(td) / "candidate"
            manifest = stage_module.stage(CODE_DIR, dest)
            self.assertEqual(manifest["status"], "SHADOW_REVIEW_ONLY")
            self.assertTrue(manifest["replaced_files"])
            self.assertEqual(
                json.loads((dest / "INTEGRATION_STAGE.json").read_text()),
                manifest,
            )
            for relative in manifest["replaced_files"]:
                self.assertTrue(relative.startswith("v13/"), relative)
                path = dest / relative
                self.assertTrue(path.is_file(), relative)
                if path.suffix == ".py":
                    compile(path.read_bytes(), str(path), "exec")
            self.assertTrue((dest / "v13" / "runtime.py").is_file())
            self.assertFalse(any(dest.rglob("*.gguf")))
            self.assertFalse(any(dest.rglob("*.sqlite")))
        self.assertEqual(
            hashlib.sha256(source_runtime.read_bytes()).hexdigest(), before,
            "staging mutated the frozen source Runtime",
        )


if __name__ == "__main__":
    unittest.main()
