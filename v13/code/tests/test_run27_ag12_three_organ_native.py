"""Run27 isolated software tests; mocked native results never count as native proof."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run27_ag12_three_organ_native as pilot
from v13.agi.generality import build_suite


class FakeStore:
    def one(self, query):
        return {"n": 0}


class FakeModels:
    def __init__(self, paths):
        self.paths = paths
    def path_for(self, role):
        return self.paths[role]


class FakePool:
    def __init__(self):
        self.fabric = object()
        self.unloads = 0
    def unload(self):
        self.unloads += 1
    def pids(self):
        return []


class FakeSleep:
    class Cycle:
        def set_policy(self, *args):
            pass
    cycle = Cycle()


class FakeRuntime:
    def __init__(self, home, paths):
        self.home = home
        self.models = FakeModels(paths)
        self.pool = FakePool()
        self.sleep = FakeSleep()
        self.store = FakeStore()
        self.cfg = {
            "learning_mode": "RECORD_ONLY", "system_stage": 0,
            "jepa_weight": 0, "latents_enabled": False,
        }
        self.closed = False
    def close(self):
        self.closed = True


def _rows(lang):
    suite = build_suite(seed=13, lang=lang)
    return {
        "status": "DONE", "items": 88, "suite_hash": suite["hash"],
        "results": [{"id": i["id"], "correct": 0, "confidence": 0.5}
                    for i in suite["items"]],
    }


class Run27ThreeOrganSoftware(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()

    def test_pinned_three_distinct_roles_and_existing_catalog(self):
        runner, models = pilot.pinned_catalog()
        self.assertEqual(pilot.ROLES, ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE"))
        self.assertEqual(runner["sha256"], pilot.RUNNER_SHA)
        self.assertNotEqual(models["b1"]["model_id"], models["b2"]["model_id"])
        self.assertEqual(len(set(x["model_id"] for x in
                                 (models["b1"], models["b2"]))), 2)

    def test_exact_suite_rows_and_no_prompt_or_nonfinite(self):
        for lang in ("de", "en"):
            rows = _rows(lang)
            self.assertTrue(pilot._rows_valid(rows, lang))
            bad = json.loads(json.dumps(rows))
            bad["results"][0]["prompt"] = "private holdout"
            self.assertFalse(pilot._rows_valid(bad, lang))
            bad = json.loads(json.dumps(rows))
            bad["results"][0]["confidence"] = float("nan")
            self.assertFalse(pilot._rows_valid(bad, lang))
            bad = json.loads(json.dumps(rows))
            bad["results"][0]["id"] = "wrong"
            self.assertFalse(pilot._rows_valid(bad, lang))

    def test_nonfresh_paths_rejected_before_model_install(self):
        home = self.base / "home"
        home.mkdir()
        with patch.object(pilot, "install", side_effect=AssertionError("should not install")):
            with self.assertRaisesRegex(FileExistsError, "FRESH_PATHS"):
                pilot.run(home, self.base / "out")

    def test_failed_install_retains_red_report(self):
        home, out = self.base / "home", self.base / "out"
        with patch.object(pilot, "install", side_effect=RuntimeError("no model")):
            with self.assertRaisesRegex(RuntimeError, "NATIVE_INCOMPLETE"):
                pilot.run(home, out)
        r = json.loads((out / "REPORT.json").read_text())
        self.assertEqual(r["status"], "RED")
        self.assertEqual(r["native_role_calls"], 0)
        self.assertFalse(r["whole_system_complete"])

    def _fake(self, bad=False):
        home, out = self.base / "home", self.base / "out"
        home.mkdir()
        (home / "exports").mkdir()
        paths = {role: home / (role + ".gguf") for role in pilot.ROLES}
        for path in paths.values():
            path.write_bytes(b"synthetic")
        archive = home / "llama-native.tar.gz"
        archive.write_bytes(b"synthetic")
        binary = home / "llama-server"
        binary.write_bytes(b"synthetic")
        runtime = FakeRuntime(home, paths)
        calls = []
        def fake_run(growth, runtime_, name, *, lang, **kwargs):
            calls.append((name, lang))
            filename = "generality-last-de.json" if lang == "de" else "generality-last.json"
            (home / "exports" / filename).write_text(json.dumps(_rows(lang)))
            stats = {role: {"items": 88, "errors": 0} for role in pilot.ROLES}
            if bad and lang == "en":
                stats["B2_GIST"]["items"] = 87
            return {"status": "DONE", "roles": list(pilot.ROLES), "stats": stats}
        with patch.object(pilot, "install", return_value=(paths, archive, binary)), \
             patch.object(pilot, "Runtime", return_value=runtime), \
             patch.object(pilot, "hub", return_value=object()), \
             patch.object(pilot.sv, "run", side_effect=fake_run):
            if bad:
                with self.assertRaisesRegex(RuntimeError, "NATIVE_INCOMPLETE"):
                    pilot.run(home, out)
            else:
                result = pilot.run(home, out)
                self.assertEqual(result["native_role_calls"], 528)
                self.assertEqual(result["voted_items"], 176)
                self.assertEqual(result["status"], "DONE")
        self.assertEqual(calls, [("v13", "de"), ("v13", "en")])
        self.assertIsNone(runtime.pool.fabric)
        self.assertTrue(runtime.closed)
        return json.loads((out / "REPORT.json").read_text())

    def test_three_organ_528_calls_only_mocked_software(self):
        r = self._fake()
        self.assertTrue(r["exclusive_native_residency"])
        self.assertFalse(r["actual_live_jef_fusion_proven"])
        self.assertFalse(r["step2_promoted"])
        self.assertEqual(r["jepa_weight"], 0)

    def test_missing_one_role_item_is_red_not_partial_green(self):
        r = self._fake(bad=True)
        self.assertEqual(r["status"], "RED")
        self.assertFalse(r["whole_system_complete"])


if __name__ == "__main__":
    unittest.main()
