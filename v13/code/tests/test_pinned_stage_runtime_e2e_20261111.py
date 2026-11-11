"""Run actual synthetic Runtime/T8/World/restart turns in the PINNED staged tree.

Unlike compile-only staging, this executes the materialized Runtime in a
subprocess, including a real SQLite store and archive/revocation lifecycle.
C3 native inference is intentionally replaced by a deterministic test driver.
"""
import importlib.util
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest

CODE = Path(__file__).resolve().parents[1]
STAGER = CODE / "scripts/stage_integrated_candidate.py"


class PinnedStageRuntimeE2E(unittest.TestCase):
    def test_real_staged_runtime_turn_learning_restart_archive_revocation(self):
        spec = importlib.util.spec_from_file_location("pinned_stage_e2e", STAGER)
        stager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stager)
        with tempfile.TemporaryDirectory(prefix="v13-staged-runtime-e2e-") as td:
            dest = Path(td) / "staged"
            manifest = stager.stage(CODE, dest)
            self.assertEqual(manifest["status"], "SHADOW_REVIEW_ONLY")
            (dest / "tests").mkdir()
            # Copy existing real Runtime/T8/World tests rather than introducing
            # a second mock implementation of the learning/data path.
            for name in (
                "integrated_online_world_disposable_cases.py",
                "memory_world_disposable_cases_20261111.py",
            ):
                shutil.copyfile(CODE / "tests" / name, dest / "tests" / name)
            # Original integration uses a narrowly scoped test-only shim;
            # never install this into the production V13 package.
            shim_source = CODE / "tests/test_integrated_predictor_history_guard_20261110.py"
            shim = runpy.run_path(str(shim_source))["SYNTHETIC_ONLY_SHIM"]
            (dest / "tests/conftest.py").write_text(shim, encoding="utf-8")
            tests = [
                "tests/integrated_online_world_disposable_cases.py::test_real_operator_turn_update_restart_and_revocation",
                "tests/memory_world_disposable_cases_20261111.py::test_archived_user_source_remains_verified_for_world_then_revocation_quarantines",
            ]
            env = dict(os.environ)
            env["PYTHONPATH"] = str(dest)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", *tests],
                cwd=dest, env=env, capture_output=True, text=True, timeout=180,
                check=False,
            )
            self.assertEqual(
                result.returncode, 0,
                "Staged multi-organ Runtime turn FAILED (no promotion):\n"
                + result.stdout[-12000:] + "\n" + result.stderr[-12000:],
            )
            self.assertIn("2 passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
