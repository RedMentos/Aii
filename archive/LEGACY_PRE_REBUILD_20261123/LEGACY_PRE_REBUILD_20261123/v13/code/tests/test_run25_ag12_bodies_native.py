"""Run25 software preflight; no downloaded models or native evidence in these tests."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run25_ag12_bodies_native as pilot
from v13.agi.generality import build_suite


class Run25PinnedBodyPreflight(unittest.TestCase):
    def test_exact_two_distinct_catalog_models_and_runner(self):
        runner, models = pilot.pinned_catalog()
        self.assertEqual(runner["sha256"], pilot.RUNNER_SHA)
        self.assertNotEqual(models["b1"]["model_id"], models["b2"]["model_id"])
        for name, expected in pilot.BODIES.items():
            self.assertEqual(models[name]["revision"], expected["revision"])
            self.assertEqual(models[name]["files"][0]["sha256"], expected["sha"])

    def test_model_runner_license_and_host_tamper_fail_closed(self):
        from v13.models import catalog
        original = catalog()
        for which in ("b1", "b2", "runner", "license", "model_host", "runner_host"):
            with self.subTest(which=which):
                spec = copy.deepcopy(original)
                if which in ("b1", "b2"):
                    spec["models"][pilot.BODIES[which]["key"]]["files"][0]["sha256"] = "0" * 64
                elif which == "runner":
                    spec["runner"]["linux_binaries"]["linux-x86_64"]["sha256"] = "0" * 64
                elif which == "license":
                    spec["models"]["gist"]["license_id"] = "unknown"
                elif which == "model_host":
                    spec["models"]["body"]["files"][0]["url"] = "https://example.org/not-official.gguf"
                else:
                    spec["runner"]["linux_binaries"]["linux-x86_64"]["url"] = "http://github.com/runner.tar.gz"
                with patch.object(pilot, "catalog", return_value=spec):
                    with self.assertRaisesRegex(ValueError, "PIN_RED"):
                        pilot.pinned_catalog()

    def test_exact_88_rows_and_no_prompt_answer_export(self):
        for lang in ("de", "en"):
            suite = build_suite(seed=13, lang=lang)
            rows = {"status": "DONE", "items": 88, "suite_hash": suite["hash"],
                    "results": [{"id": i["id"], "correct": 0, "confidence": 0.5}
                                for i in suite["items"]]}
            self.assertTrue(pilot._rows_valid(rows, lang))
            bad = copy.deepcopy(rows)
            bad["results"][0]["prompt"] = suite["items"][0]["prompt"]
            self.assertFalse(pilot._rows_valid(bad, lang))
            bad = copy.deepcopy(rows)
            bad["results"][0]["confidence"] = float("nan")
            self.assertFalse(pilot._rows_valid(bad, lang))
            bad = copy.deepcopy(rows)
            bad["results"][0]["id"] = "wrong"
            self.assertFalse(pilot._rows_valid(bad, lang))
            bad = copy.deepcopy(rows)
            bad["results"].pop()
            self.assertFalse(pilot._rows_valid(bad, lang))

    def test_nonfresh_paths_rejected_before_download(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "exists"
            root.mkdir()
            with patch.object(pilot, "pinned_catalog", side_effect=AssertionError("download path")):
                with self.assertRaisesRegex(FileExistsError, "FRESH_PATHS"):
                    pilot.run(root, Path(td) / "out")

    def test_failed_first_body_keeps_second_and_reports_red(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "homes"
            out = Path(td) / "out"
            calls = []
            def fake_observe(root_, out_, name):
                calls.append(name)
                if name == "b1":
                    raise RuntimeError("native B1 unavailable")
                return {"status": "DONE", "native_calls": 176}
            with patch.object(pilot, "observe_body", side_effect=fake_observe):
                with self.assertRaisesRegex(RuntimeError, "NATIVE_INCOMPLETE"):
                    pilot.run(root, out)
            self.assertEqual(calls, ["b1", "b2"])
            report = json.loads((out / "REPORT.json").read_text())
            self.assertEqual(report["models"]["b1"]["status"], "RED")
            self.assertEqual(report["models"]["b2"]["status"], "DONE")
            self.assertEqual(report["native_calls"], 176)
            self.assertEqual(report["jepa_weight"], 0)
            self.assertFalse(report["step2_promoted"])
            self.assertFalse(report["redmi_measured"])


if __name__ == "__main__":
    unittest.main()
