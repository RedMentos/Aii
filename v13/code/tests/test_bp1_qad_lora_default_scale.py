"""Software-only pinned b10964 default LoRA scale/descriptor regression.

No model/adapter is loaded by these tests. Real native proof remains separate.
"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import bp1_qad_lora_eval as E


class FakeProc:
    def poll(self):
        return None


class NativeLoRADefaultScaleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binary = self.root / "llama-server"
        self.base = self.root / "base.gguf"
        self.adapter = self.root / "adapter.gguf"
        self.log = self.root / "server.log"
        for p in (self.binary, self.base, self.adapter):
            p.write_bytes(b"fixture")

    def launch(self, descriptor):
        with patch.object(E.N, "assert_loopback_port_available"), \
             patch.object(E.subprocess, "Popen", return_value=FakeProc()) as popen, \
             patch.object(E.C, "stop") as stop, \
             patch.object(E, "_http_json", side_effect=[
                 {"status": "ok"}, [descriptor]
             ]) as http:
            with E.serve(self.binary, self.base, self.adapter, 8832, self.log):
                pass
        return popen.call_args.args[0], stop, http

    def test_server_declares_zero_default_scale_not_unapplied_one(self):
        argv, stop, http = self.launch(
            {"id": 0, "path": str(self.adapter), "scale": 0.0})
        self.assertEqual(argv[argv.index("--lora-scaled") + 1],
                         str(self.adapter) + ":0")
        self.assertNotIn("--lora", argv)
        self.assertIn("--lora-init-without-apply", argv)
        self.assertEqual(argv[argv.index("--host") + 1], "127.0.0.1")
        self.assertEqual(argv[argv.index("--port") + 1], "8832")
        self.assertEqual(http.call_args_list[-1].args[2], "/lora-adapters")
        stop.assert_called_once()

    def test_native_reported_default_one_still_fails_closed(self):
        for scale in (1.0, True, False, "0", None):
            with self.subTest(scale=scale):
                with patch.object(E.N, "assert_loopback_port_available"), \
                     patch.object(E.subprocess, "Popen", return_value=FakeProc()), \
                     patch.object(E.C, "stop") as stop, \
                     patch.object(E, "_http_json", side_effect=[
                         {"status": "ok"},
                         [{"id": 0, "path": str(self.adapter), "scale": scale}],
                     ]):
                    with self.assertRaisesRegex(RuntimeError, "ID/path/default-scale"):
                        with E.serve(self.binary, self.base, self.adapter, 8832, self.log):
                            pass
                    stop.assert_called_once()

    def test_wrong_or_boolean_id_and_wrong_path_fail_closed(self):
        for descriptor in (
            {"id": False, "path": str(self.adapter), "scale": 0.0},
            {"id": 0.0, "path": str(self.adapter), "scale": 0.0},
            {"id": 1, "path": str(self.adapter), "scale": 0.0},
            {"id": 0, "path": "different.gguf", "scale": 0.0},
            {"id": 0, "path": None, "scale": 0.0},
            {"id": 0, "path": str(self.adapter)},
        ):
            with self.subTest(descriptor=descriptor):
                with patch.object(E.N, "assert_loopback_port_available"), \
                     patch.object(E.subprocess, "Popen", return_value=FakeProc()), \
                     patch.object(E.C, "stop"), \
                     patch.object(E, "_http_json", side_effect=[
                         {"status": "ok"}, [descriptor],
                     ]):
                    with self.assertRaisesRegex(RuntimeError, "ID/path/default-scale"):
                        with E.serve(self.binary, self.base, self.adapter, 8832, self.log):
                            pass


if __name__ == "__main__":
    unittest.main()
