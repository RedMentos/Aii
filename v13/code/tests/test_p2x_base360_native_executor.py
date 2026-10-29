"""Source-only adversarial checks for default-off P2X base360 native executor."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "p2x_base360_native_executor", SCRIPTS / "p2x_base360_native_executor.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def prompt():
    return {"id": "P2X" + "A" * 16, "arm": "both_exact",
            "messages": [{"role": "user", "content": "Choose the current option."}]}


class Base360Tests(unittest.TestCase):
    def test_exact_user_message_hash_and_no_adapter(self):
        p = prompt()
        rec = native.record_call(p, '{"action":"A"}', .5, {"status": "FINAL"})
        self.assertEqual(rec["input_sha256"],
                         native.scorer.sha(native.scorer.canonical(p["messages"])))
        self.assertIsNone(rec["adapter_sha256"])
        self.assertEqual((rec["seed"], rec["native_calls"], rec["model_called"]),
                         (13, 1, True))
        self.assertEqual(rec["runtime_sha256"], native.scorer.RUNTIME_SHA)

    def test_extra_system_message_red(self):
        p = prompt()
        p["messages"].insert(0, {"role": "system", "content": "hidden oracle"})
        with self.assertRaisesRegex(ValueError, "ONE_USER"):
            native.record_call(p, "{}", .5, {"status": "FINAL"})

    def test_extra_prompt_field_red(self):
        p = prompt()
        p["oracle_action"] = "A"
        with self.assertRaisesRegex(ValueError, "ONE_USER"):
            native.record_call(p, "{}", .5, {"status": "FINAL"})

    def test_duration_nonfinal_and_malformed_red(self):
        for duration, metrics in ((-1, {"status": "FINAL"}),
                                  (91, {"status": "FINAL"}),
                                  (float("nan"), {"status": "FINAL"}),
                                  (.1, {"status": "PARTIAL"})):
            with self.subTest(duration=duration, metrics=metrics):
                with self.assertRaisesRegex(ValueError, "NONFINAL"):
                    native.record_call(prompt(), "{}", duration, metrics)

    def test_age0_default_pass_and_nonrecord_red(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = {"system_stage": 0, "learning_mode": "RECORD_ONLY",
                   "latents_enabled": False, "jepa_weight": 0}
            with patch.dict(os.environ, {"V13_LLAMA_SERVER": ""}):
                native.check_age0(cfg, d)
                cfg["learning_mode"] = "SHADOW_UPDATE"
                with self.assertRaisesRegex(ValueError, "AGE0"):
                    native.check_age0(cfg, d)

    def test_age0_adapter_mirror_red(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config"
            p.mkdir()
            (p / "lora-active.json").write_text(json.dumps(
                {"active": {"C3_LANGUAGE": {"path": "adapter.gguf"}}}))
            cfg = {"system_stage": 0, "learning_mode": "RECORD_ONLY",
                   "latents_enabled": False, "jepa_weight": 0}
            with patch.dict(os.environ, {"V13_LLAMA_SERVER": ""}):
                with self.assertRaisesRegex(ValueError, "ADAPTER"):
                    native.check_age0(cfg, d)

    def test_binary_override_red(self):
        cfg = {"system_stage": 0, "learning_mode": "RECORD_ONLY",
               "latents_enabled": False, "jepa_weight": 0}
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ, {"V13_LLAMA_SERVER": "/tmp/fake"}):
                with self.assertRaisesRegex(ValueError, "OVERRIDE"):
                    native.check_age0(cfg, d)

    def test_cli_requires_frozen_validation_and_out(self):
        with self.assertRaises(SystemExit) as caught:
            native.main(["--home", "/missing"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
