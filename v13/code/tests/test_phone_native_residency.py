"""Private Redmi native residency telemetry: only owned group, never expose PIDs/paths."""
import json
from pathlib import Path
import tempfile
import unittest

from v13 import phone_native_residency as n


class NativeResidencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "v13"
        (self.home / "config").mkdir(parents=True)
        self.proc = self.root / "proc"
        self.proc.mkdir()
        installed = {}
        for key in ("body", "gist", "language", "needle"):
            installed[key] = {"download_complete": True,
                              "main_file": key + ".gguf",
                              "files": {key + ".gguf": {"path": "models/" + key + ".gguf"}}}
        (self.home / "config/models.json").write_text(json.dumps(installed))
        (self.home / "models").mkdir()

    def child(self, pid, model, *, name="llama-server", rss=812000, pss=700000):
        d = self.proc / str(pid)
        d.mkdir()
        model_path = str(self.home / "models" / (model + ".gguf"))
        args = (["/home/termux/bin/" + name, model_path, "/private/specs.json"]
                if name == "needle-worker" else
                ["/home/termux/bin/" + name, "--model", model_path]
                if name == "needle" else
                ["/home/termux/bin/" + name, "-m", model_path])
        (d / "cmdline").write_bytes(b"\x00".join(x.encode() for x in args) + b"\x00")
        (d / "status").write_text("Name:\tllama-server\nVmRSS:\t%d kB\n" % rss)
        (d / "smaps_rollup").write_text("Pss:\t%d kB\n" % pss)
        return d

    def test_only_v13_owned_native_roles_are_counted(self):
        self.child(22, "body")
        self.child(23, "gist")
        self.child(24, "language")
        self.child(27, "needle", name="needle-worker")
        self.child(25, "body")  # unrelated foreign process
        self.child(26, "body", name="python")  # never count as native
        groups = {10: 10, 22: 10, 23: 10, 24: 10, 25: 25, 26: 10, 27: 10}
        report = n.snapshot(10, self.home, proc_root=self.proc, group_of=groups.__getitem__)
        self.assertEqual(report["availability"], "AVAILABLE")
        self.assertEqual({k: v["processes"] for k, v in report["roles"].items()},
                         {"B1_DETAIL": 1, "B2_GIST": 1, "C3_LANGUAGE": 1, "C2_CONTROL": 1})
        self.assertGreater(report["mapped_pss_mib"], 0)
        raw = json.dumps(report)
        for secret in (str(self.home), "/home/termux", "22", "23", "24", "25"):
            # Memory numbers may coincidentally contain PID digits; require no PID keys.
            if secret.isdigit():
                self.assertNotIn('"pid":', raw)
            else:
                self.assertNotIn(secret, raw)

    def test_c2_native_cli_is_identified_only_with_matching_model_path(self):
        self.child(31, "needle", name="needle")
        report = n.snapshot(10, self.home, proc_root=self.proc,
                            group_of=lambda x: 10)
        self.assertEqual(report["roles"]["C2_CONTROL"]["processes"], 1)
        self.assertEqual(report["roles"]["B1_DETAIL"]["processes"], 0)
        self.assertEqual(report["unmapped_native_processes"], 0)

    def test_no_supervisor_refuses_to_claim_no_models(self):
        status = n.snapshot(None, self.home, proc_root=self.proc)
        self.assertEqual(status["availability"], "UNAVAILABLE")
        self.assertEqual(status["reason"], "NO_VERIFIED_MODEL_SUPERVISOR")

    def test_no_children_observed_is_not_residency_proof(self):
        r = n.snapshot(10, self.home, proc_root=self.proc, group_of=lambda x: 10)
        self.assertEqual(r["readability"], "UNKNOWN_NO_GROUP_CHILDREN")
        self.assertEqual(r["mapped_native_processes"], 0)

    def test_unlisted_other_group_cannot_be_exposed(self):
        self.child(55, "body")
        r = n.snapshot(10, self.home, proc_root=self.proc, group_of=lambda pid: pid)
        self.assertEqual(r["roles"]["B1_DETAIL"]["processes"], 0)
        self.assertEqual(r["unmapped_native_processes"], 0)

    def test_mismatched_supervisor_group_fails_closed(self):
        r = n.snapshot(10, self.home, proc_root=self.proc, group_of=lambda pid: 99)
        self.assertEqual(r["availability"], "UNAVAILABLE")
        self.assertEqual(r["reason"], "SUPERVISOR_GROUP_MISMATCH")

    def test_unmapped_server_distinct_from_body(self):
        self.child(12, "different")
        r = n.snapshot(10, self.home, proc_root=self.proc, group_of=lambda x: 10)
        self.assertEqual(r["unmapped_native_processes"], 1)
        self.assertEqual(r["roles"]["B1_DETAIL"]["processes"], 0)


if __name__ == "__main__":
    unittest.main()
