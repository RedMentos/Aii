"""Review-only regression: mid-operation revoke/disable/halt must not resurrect or emit module data.
Synthetic SQLite fixtures; no network, native model, or Redmi evidence.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13 import modules_gate as M, module_learn, prohibitions as P

H = M.HUMAN
URL = "https://example.org/lifecycle-cas.json"
DATA = json.dumps({
    "format": M.FORMAT, "name": "Synthetic", "version": "1",
    "license": "Apache-2.0", "source": "test only",
    "items": [{"title": "Planet", "text": "The synthetic test planet has exactly three moons."}],
}).encode("utf-8")


class ModuleLifecycleCASTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.store = self.runtime.store
        M.set_enabled(self.store, True, authority=H)
        self.mid = M.propose(self.store, URL, "Synthetic", origin="USER", clock=lambda: 1000.)

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def ready(self, active=False):
        M.fetch(self.store, self.mid, authority=H, fetcher=lambda _: DATA, clock=lambda: 1000.)
        if active:
            self.release()

    def release(self):
        sha8 = M.state(self.store)["mods"][self.mid]["sha256"][:8]
        return M.activate(self.store, self.mid, sha8, authority=H, clock=lambda: 1100.)

    def on_read(self, callback):
        path = M._file(self.store, self.mid)
        original = M._file

        class Intercept:
            def read_bytes(self):
                callback()
                return path.read_bytes()

        return patch.object(M, "_file", side_effect=lambda store, mid: Intercept() if mid == self.mid else original(store, mid))

    def test_check_does_not_resurrect_revoked_quarantine(self):
        original = M.scan

        def revoke_in_scan(items, store=None, guard=None):
            M.revoke(self.store, self.mid, authority=H)
            return original(items, store, guard)

        with patch.object(M, "scan", side_effect=revoke_in_scan):
            with self.assertRaises(PermissionError):
                M.fetch(self.store, self.mid, authority=H, fetcher=lambda _: DATA, clock=lambda: 1000.)
        self.assertEqual(M.state(self.store)["mods"][self.mid]["state"], "REVOKED")

    def test_activate_does_not_resurrect_revoked_module(self):
        self.ready()
        with self.on_read(lambda: M.revoke(self.store, self.mid, authority=H)):
            with self.assertRaises(PermissionError):
                self.release()
        self.assertEqual(M.state(self.store)["mods"][self.mid]["state"], "REVOKED")

    def test_activate_rechecks_disable(self):
        self.ready()
        with self.on_read(lambda: M.set_enabled(self.store, False, authority=H)):
            with self.assertRaises(PermissionError):
                self.release()
        self.assertFalse(M.state(self.store)["enabled"])
        self.assertNotEqual(M.state(self.store)["mods"][self.mid]["state"], "ACTIVE")

    def test_activate_rechecks_notaus(self):
        self.ready()
        with self.on_read(lambda: P.halt(self.store, True, authority=H)):
            with self.assertRaises(PermissionError):
                self.release()
        self.assertEqual(M.state(self.store)["mods"][self.mid]["state"], "SANDBOX_OK")

    def test_corpus_does_not_return_revoked_snapshot(self):
        self.ready(active=True)
        M.set_learn(self.store, True, authority=H)
        with self.on_read(lambda: M.revoke(self.store, self.mid, authority=H)):
            self.assertEqual(M.corpus(self.store), [])
        self.assertEqual(M.state(self.store)["mods"][self.mid]["state"], "REVOKED")

    def test_propose_cannot_record_after_disable_between_checks(self):
        original = M.check_url

        def disable_before_mutate(url):
            M.set_enabled(self.store, False, authority=H)
            return original(url)

        with patch.object(M, "check_url", side_effect=disable_before_mutate):
            with self.assertRaises(PermissionError):
                M.propose(self.store, "https://example.org/another.json", "Other")
        self.assertEqual(len(M.state(self.store)["mods"]), 1)

    def test_export_cannot_write_stale_revoked_corpus(self):
        self.ready(active=True)
        M.set_learn(self.store, True, authority=H)
        out = Path(self.tmp.name) / "stale.jsonl"
        original = M.corpus

        def revoke_after_corpus(store):
            items = original(store)
            M.revoke(self.store, self.mid, authority=H)
            return items

        with patch.object(M, "corpus", side_effect=revoke_after_corpus):
            with self.assertRaises(PermissionError):
                module_learn.export_dataset(self.store, out)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
