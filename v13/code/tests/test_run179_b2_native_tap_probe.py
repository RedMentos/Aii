"""Synthetic protocol-only checks for Run179, no model downloaded."""
import importlib.util
from pathlib import Path
import tempfile
import sys
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/run179_b2_native_tap_probe.py'


class ProbeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('run179_probe', SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        fake = types.ModuleType('v13')
        config = types.ModuleType('v13.config'); config.DEFAULTS = {}
        runners = types.ModuleType('v13.runners'); runners.LlamaRunner = object
        runners.TAP_SPECS = {'gist':('qwen35.result_norm.final.v1',1024)}
        with patch.dict(sys.modules, {'v13':fake,'v13.config':config,'v13.runners':runners}):
            spec.loader.exec_module(cls.module)

    def test_reject_wrong_model_before_runner_launch(self):
        with tempfile.TemporaryDirectory() as d:
            model = Path(d)/'wrong.gguf'; model.write_bytes(b'wrong')
            server = Path(d)/'server'; server.write_bytes(b'fake')
            with self.assertRaisesRegex(ValueError, 'model sha256 mismatch'):
                self.module.probe(model, server)

    def test_reject_wrong_archive_binding(self):
        with tempfile.TemporaryDirectory() as d:
            model = Path(d)/'fake.gguf'; model.write_bytes(b'x')
            server = Path(d)/'server'; server.write_bytes(b'fake')
            with patch.object(self.module, 'sha256', return_value=self.module.EXPECTED_MODEL_SHA):
                with self.assertRaisesRegex(ValueError, 'archive sha256 mismatch'):
                    self.module.probe(model, server, 'wrong')

    def test_locked_b2_spec_and_authority(self):
        self.assertEqual(self.module.EXPECTED_MODEL_SHA,
                         '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf')
        self.assertEqual(self.module.PROMPTS[0], self.module.PROMPTS[1])
        self.assertNotEqual(self.module.PROMPTS[0], self.module.PROMPTS[2])
        source = SCRIPT.read_text()
        self.assertIn("'CAN_TRAIN_BODY') is not False", source)
        self.assertIn("'CAN_LATENT_INJECT') is not False", source)
        self.assertIn('runner.unload()', source)


if __name__ == '__main__':
    unittest.main()
