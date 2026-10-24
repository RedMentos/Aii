"""Run90 real filesystem BodyTrainPort descriptor/artifact symlink counterexamples.

The port is still non-authoritative even when valid. No model training or
native process is launched. See Run90 PREREG.
"""
import json
import tempfile
import unittest
from pathlib import Path

from v13.body_training import inspect_train_port
from v13.common import file_hash


def fixture(home):
    for directory in ("config", "models", "bin"):
        (home / directory).mkdir(parents=True)
    files = {
        "model": "models/body.gguf",
        "master": "models/body-master.bin",
        "runner": "bin/train-body",
        "requantizer": "bin/requantize-body",
    }
    for name, relative in files.items():
        path = home / relative
        path.write_bytes((name + "-distinct").encode())
        if name in {"runner", "requantizer"}:
            path.chmod(0o755)
    descriptor = {
        "schema": "v13-native-body-train-port-v1",
        "role": "B1_DETAIL",
        "master_dtype": "float16",
        "trainable_parameter_ids": ["layer.1.expert.2.w1"],
        **{name + "_artifact": relative for name, relative in files.items()},
        **{name + "_sha256": file_hash(home / relative)
           for name, relative in files.items()},
    }
    (home / "config/native-body-train-port.json").write_text(
        json.dumps(descriptor))
    return descriptor


class BodyTrainPortPathsRun90(unittest.TestCase):
    def test_regular_bound_port_remains_non_authoritative(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()
            fixture(home)
            report = inspect_train_port(home, "B1_DETAIL")
            self.assertEqual(report["reason"], "PORT_BOUND_PROOF_REQUIRED")
            self.assertEqual(report["update_authority"], 0)

    def test_external_artifact_symlink_with_matching_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            descriptor = fixture(home)
            outside = root / "outside-master.bin"
            outside.write_bytes(b"master-distinct")
            path = home / descriptor["master_artifact"]
            path.unlink()
            path.symlink_to(outside)
            report = inspect_train_port(home, "B1_DETAIL")
            self.assertEqual(report["reason"], "INVALID_ARTIFACT_BINDING")
            self.assertEqual(report["update_authority"], 0)
            self.assertFalse(report.get("port_bound", False))

    def test_parent_directory_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            fixture(home)
            moved = root / "external-models"
            (home / "models").rename(moved)
            (home / "models").symlink_to(moved, target_is_directory=True)
            report = inspect_train_port(home, "B1_DETAIL")
            self.assertEqual(report["reason"], "INVALID_ARTIFACT_BINDING")
            self.assertFalse(report.get("port_bound", False))

    def test_descriptor_symlink_outside_home_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            fixture(home)
            descriptor = home / "config/native-body-train-port.json"
            outside = root / "outside-descriptor.json"
            descriptor.rename(outside)
            descriptor.symlink_to(outside)
            report = inspect_train_port(home, "B1_DETAIL")
            self.assertEqual(report["reason"], "INVALID_TRAIN_PORT_DESCRIPTOR")
            self.assertFalse(report.get("port_bound", False))

    def test_descriptor_dotdot_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            descriptor = fixture(home)
            (root / "outside-descriptor.json").write_text(
                json.dumps(descriptor))
            report = inspect_train_port(
                home, "B1_DETAIL", "../outside-descriptor.json")
            self.assertEqual(report["reason"], "INVALID_TRAIN_PORT_DESCRIPTOR")
            self.assertFalse(report.get("port_bound", False))


if __name__ == "__main__":
    unittest.main()
