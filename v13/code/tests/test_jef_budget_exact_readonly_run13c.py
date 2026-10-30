"""Run13C real-Store, existing-home, no-native read-only operator CLI."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zlib

from scripts import c2_body_disjoint_paired181_run11v as frozen
from scripts.jef_budget_exact_readonly_run13c import ReadOnlySourceStore
from v13.agi.budget_answer_shadow_run13b import propose_text
from v13.runtime import Runtime

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/c2_body_fulltask_run13a_seed211_20261030.json")
SHA = "e6718093ccd83d556019223eca2d5317668d1ada25659519a699aee681a8b97f"


def case():
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    assert hashlib.sha256(json.dumps(
        tuple(cases), sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest() == SHA
    return cases[0]


def refs(runtime, fixture=None):
    c = fixture or case()
    q = runtime.store.source(
        f"Calculate both remaining budgets and faster option for Project {c['project']}.",
        "USER")
    s = runtime.store.source(frozen.prompt(c), "USER")
    return q, s


class Run13CReadOnlyCli(unittest.TestCase):
    def test_existing_home_cli_with_live_coordinator_and_no_source_writes(self):
        with TemporaryDirectory() as td:
            home = Path(td)
            runtime = Runtime(home)
            try:
                runtime.sleep.cycle.set_policy("enabled", "off")
                q, s = refs(runtime)
                before = runtime.store.one("SELECT count(*) AS n FROM sources")["n"]
                cmd = [sys.executable, "-m",
                       "scripts.jef_budget_exact_readonly_run13c",
                       "--home", str(home),
                       "--query-ref", json.dumps(q),
                       "--source-ref", json.dumps(s)]
                result = subprocess.run(cmd, capture_output=True, text=True,
                                        timeout=20, check=False)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                output = json.loads(result.stdout)
                self.assertIn("Cedar leaves 169 Euro remaining.", output["answer"])
                self.assertIn("Quartz leaves 58 Euro remaining.", output["answer"])
                self.assertIn("Quartz finishes sooner.", output["answer"])
                self.assertEqual(output["delivery_authority"], 0)
                self.assertEqual(output["native_calls"], 0)
                self.assertEqual(before, runtime.store.one(
                    "SELECT count(*) AS n FROM sources")["n"])
            finally:
                runtime.close()

    def test_revoked_or_foreign_home_refs_fail_closed(self):
        with TemporaryDirectory() as td, TemporaryDirectory() as foreign:
            runtime = Runtime(Path(td))
            other = Runtime(Path(foreign))
            try:
                q, s = refs(runtime)
                _, alien = refs(other)
                with ReadOnlySourceStore(td) as reader:
                    self.assertIsNone(propose_text(reader, q, alien)["answer"])
                with runtime.store.tx() as db:
                    db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                               (s["source_id"],))
                with ReadOnlySourceStore(td) as reader:
                    got = propose_text(reader, q, s)
                    self.assertIsNone(got["answer"])
                    self.assertEqual(got["delivery_authority"], 0)
            finally:
                other.close()
                runtime.close()

    def test_archived_source_blob_is_verified_and_usable(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                q, s = refs(runtime)
                blob = Path(td) / "data/blobs" / s["sha256"]
                data = blob.read_bytes()
                blob.with_name(blob.name + ".z").write_bytes(zlib.compress(data))
                blob.unlink()
                with ReadOnlySourceStore(td) as reader:
                    got = propose_text(reader, q, s)
                self.assertIsNotNone(got["answer"])
                self.assertEqual(got["native_calls"], 0)
            finally:
                runtime.close()

    def test_corrupt_and_symlink_source_blob_are_rejected(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                q, s = refs(runtime)
                blob = Path(td) / "data/blobs" / s["sha256"]
                original = blob.read_bytes()
                blob.write_bytes(original + b"x")
                with ReadOnlySourceStore(td) as reader:
                    self.assertIsNone(propose_text(reader, q, s)["answer"])
                blob.write_bytes(original)
                backup = blob.with_name(blob.name + ".saved")
                blob.rename(backup)
                blob.symlink_to(backup)
                with ReadOnlySourceStore(td) as reader:
                    self.assertIsNone(propose_text(reader, q, s)["answer"])
                blob.unlink()
                backup.rename(blob)
            finally:
                runtime.close()

    def test_invalid_json_and_missing_home_are_rejected_without_model(self):
        with TemporaryDirectory() as td:
            cmd = [sys.executable, "-m",
                   "scripts.jef_budget_exact_readonly_run13c",
                   "--home", td, "--query-ref", "[]",
                   "--source-ref", "{}"]
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=20, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIsNone(json.loads(result.stdout)["answer"])
            self.assertEqual(json.loads(result.stdout)["native_calls"], 0)


    def test_corrupt_zlib_archive_fails_closed_through_python_api(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                q, s = refs(runtime)
                blob = Path(td) / "data/blobs" / s["sha256"]
                blob.with_name(blob.name + ".z").write_bytes(b"not-a-zlib-stream")
                blob.unlink()
                with ReadOnlySourceStore(td) as reader:
                    got = propose_text(reader, q, s)
                self.assertIsNone(got["answer"])
                self.assertEqual(got["delivery_authority"], 0)
            finally:
                runtime.close()

    def test_closed_sqlite_connection_fails_closed_through_python_api(self):
        with TemporaryDirectory() as td:
            runtime = Runtime(Path(td))
            try:
                q, s = refs(runtime)
                with ReadOnlySourceStore(td) as reader:
                    reader.db.close()
                    got = propose_text(reader, q, s)
                self.assertIsNone(got["answer"])
                self.assertEqual(got["delivery_authority"], 0)
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
