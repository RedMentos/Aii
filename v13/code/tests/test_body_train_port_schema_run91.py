"""Run91 malformed native BodyTrainPort descriptors must report zero authority.

Real JSON/SQLite-free filesystem fixtures; no model, runner, or training.
"""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tests.test_body_train_port_paths_run90 import fixture
from v13.body_training import inspect_train_port
from v13.verification import native_capability_profile


def write(home, descriptor):
    (home / "config/native-body-train-port.json").write_text(
        json.dumps(descriptor))


class BodyTrainPortSchemaRun91(unittest.TestCase):
    def test_unhashable_trainable_ids_return_reason_not_typeerror(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            descriptor = fixture(home)
            descriptor["trainable_parameter_ids"] = [{}]
            write(home, descriptor)
            report = inspect_train_port(home, "B1_DETAIL")
            self.assertEqual(report["reason"], "INVALID_TRAINABLE_PARAMETER_SET")
            self.assertEqual(report["update_authority"], 0)

    def test_unhashable_master_dtype_return_reason_not_typeerror(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            descriptor = fixture(home)
            descriptor["master_dtype"] = []
            write(home, descriptor)
            report = inspect_train_port(home, "B1_DETAIL")
            self.assertEqual(report["reason"], "MASTER_DTYPE_NOT_TRAINABLE")
            self.assertEqual(report["update_authority"], 0)

    def test_unhashable_fp32_exception_ids_return_reason_not_typeerror(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            descriptor = fixture(home)
            descriptor.update(
                master_dtype="float32",
                requantizer_artifact=None,
                requantizer_sha256=None,
                trainable_parameter_ids=["token_embd_norm.weight"],
                fp32_inference_parameter_ids=[{}])
            write(home, descriptor)
            report = inspect_train_port(home, "B1_DETAIL")
            self.assertEqual(report["reason"], "REQUANTIZER_EXCEPTION_NOT_FP32")
            self.assertEqual(report["update_authority"], 0)

    def test_native_capability_diagnostic_survives_malformed_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            descriptor = fixture(home)
            descriptor["trainable_parameter_ids"] = [{}]
            write(home, descriptor)
            report = native_capability_profile(SimpleNamespace(home=home))
            self.assertEqual(report["body_training"]["status"], "UNAVAILABLE")
            self.assertEqual(report["body_training"]["authority"], "NONE")
            port = report["body_training"]["ports"]["B1_DETAIL"]
            self.assertEqual(port["reason"], "INVALID_TRAINABLE_PARAMETER_SET")
            self.assertEqual(port["update_authority"], 0)


if __name__ == "__main__":
    unittest.main()
