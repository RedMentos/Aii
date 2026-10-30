"""Run24 software preflight for immutable C3/runner native cohort."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run24_ag12_german_c3_native as pilot


class Run24PinnedNativePreflight(unittest.TestCase):
    def test_current_public_catalog_matches_registered_bytes(self):
        specs, model, runner = pilot._pinned_catalog()
        self.assertEqual(model["model_id"], pilot.MODEL_ID)
        self.assertEqual(model["revision"], pilot.MODEL_REV)
        self.assertEqual(model["files"][0]["sha256"], pilot.MODEL_SHA)
        self.assertEqual(runner["sha256"], pilot.RUNNER_TAR_SHA)
        self.assertEqual(specs["runner"]["tag"], pilot.RUNNER_TAG)

    def test_changed_model_or_runner_identity_fails_closed(self):
        specs, _, _ = pilot._pinned_catalog()
        for which in ("model", "runner", "license"):
            with self.subTest(which=which):
                modified = copy.deepcopy(specs)
                if which == "model":
                    modified["models"]["language"]["files"][0]["sha256"] = "0" * 64
                elif which == "runner":
                    modified["runner"]["linux_binaries"]["linux-x86_64"]["sha256"] = "0" * 64
                else:
                    modified["models"]["language"]["license_id"] = "UNKNOWN"
                with patch.object(pilot, "catalog", return_value=modified):
                    with self.assertRaisesRegex(ValueError, "PINNED_PUBLIC_ARTIFACT"):
                        pilot._pinned_catalog()

    def test_nonofficial_model_or_runner_host_is_vetoed(self):
        specs, _, _ = pilot._pinned_catalog()
        for which in ("model", "runner"):
            modified = copy.deepcopy(specs)
            if which == "model":
                modified["models"]["language"]["files"][0]["url"] = "https://example.org/fake.gguf"
            else:
                modified["runner"]["linux_binaries"]["linux-x86_64"]["url"] = "http://github.com/unsafe"
            with patch.object(pilot, "catalog", return_value=modified):
                with self.assertRaisesRegex(ValueError, "OFFICIAL_SOURCE_URL"):
                    pilot._pinned_catalog()

    def test_nonfresh_paths_refused_before_download_or_state(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "existing"
            home.mkdir()
            out = Path(td) / "out"
            with patch.object(pilot, "_install", side_effect=AssertionError("download invoked")):
                with self.assertRaisesRegex(FileExistsError, "FRESH_PATHS"):
                    pilot.run(home, out)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
