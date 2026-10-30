"""Fail-closed native Body training port home containment, no training."""
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_body_training_port import BodyTrainingPortContract
from v13.body_training import inspect_train_port
from v13.common import file_hash


class NativeBodyPortContainment(unittest.TestCase):
    def make(self, home):
        return BodyTrainingPortContract().make(home)

    def write(self, home, desc):
        (home / "config/native-body-train-port.json").write_text(json.dumps(desc))

    def test_external_master_symlink_rejected_even_with_matching_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            d = self.make(home)
            outside = root / "outside-master.bin"
            outside.write_bytes((home / d["master_artifact"]).read_bytes())
            (home / d["master_artifact"]).unlink()
            (home / d["master_artifact"]).symlink_to(outside)
            d["master_sha256"] = file_hash(outside)
            self.write(home, d)
            got = inspect_train_port(home, "B1_DETAIL")
            self.assertEqual(got["reason"], "ARTIFACT_OUTSIDE_HOME")
            self.assertEqual(got["update_authority"], 0)
            self.assertFalse(got.get("port_bound", False))

    def test_external_parent_directory_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            self.make(home)
            outside = root / "outside-models"
            (home / "models").rename(outside)
            (home / "models").symlink_to(outside, target_is_directory=True)
            got = inspect_train_port(home, "B1_DETAIL")
            self.assertEqual(got["reason"], "ARTIFACT_OUTSIDE_HOME")
            self.assertFalse(got.get("port_bound", False))

    def test_external_descriptor_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            home = root / "home"
            home.mkdir()
            self.make(home)
            descriptor = home / "config/native-body-train-port.json"
            outside = root / "outside-descriptor.json"
            outside.write_bytes(descriptor.read_bytes())
            descriptor.unlink()
            descriptor.symlink_to(outside)
            got = inspect_train_port(home, "B1_DETAIL")
            self.assertEqual(got["reason"], "INVALID_TRAIN_PORT_DESCRIPTOR_PATH")
            self.assertEqual(got["update_authority"], 0)

    def test_internal_symlink_to_pinned_master_remains_bound_without_authority(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            d = self.make(home)
            master = home / d["master_artifact"]
            target = home / "models/internal-master-copy.bin"
            target.write_bytes(master.read_bytes())
            master.unlink()
            master.symlink_to(target)
            got = inspect_train_port(home, "B1_DETAIL")
            self.assertTrue(got["port_bound"])
            self.assertEqual(got["reason"], "PORT_BOUND_PROOF_REQUIRED")
            self.assertEqual(got["update_authority"], 0)

    def test_relative_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            d = self.make(home)
            d["master_artifact"] = "../external.bin"
            self.write(home, d)
            self.assertEqual(inspect_train_port(home, "B1_DETAIL")["reason"],
                             "INVALID_ARTIFACT_BINDING")

    def test_absolute_artifact_path_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            d = self.make(home)
            d["model_artifact"] = "/tmp/external.gguf"
            self.write(home, d)
            self.assertEqual(inspect_train_port(home, "B1_DETAIL")["reason"],
                             "INVALID_ARTIFACT_BINDING")

    def test_descriptor_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            self.make(home)
            self.assertEqual(inspect_train_port(home, "B1_DETAIL", "../outside.json")["reason"],
                             "INVALID_TRAIN_PORT_DESCRIPTOR_PATH")

    def test_missing_artifact_keeps_distinct_reason(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            d = self.make(home)
            (home / d["model_artifact"]).unlink()
            self.assertEqual(inspect_train_port(home, "B1_DETAIL")["reason"],
                             "MISSING_MODEL_ARTIFACT")


if __name__ == "__main__":
    unittest.main()
