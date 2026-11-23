"""Offline regression for phone runtime release source and symlink containment."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13 import runtime_deploy as deploy


class RuntimeDeployIntegrityTests(unittest.TestCase):
    def test_nested_symlink_is_not_dereferenced_into_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "build"
            for subtree in deploy.COPY_SUBTREES:
                (source / subtree).mkdir(parents=True, exist_ok=True)
            secret = root / "private-token"
            secret.write_text("NOT_FOR_RELEASE")
            (source / "v13" / "subdir").mkdir()
            (source / "v13" / "subdir" / "leak").symlink_to(secret)
            with self.assertRaisesRegex(deploy.RuntimeDeployError, "Symlink inside"):
                deploy._copy(source, target)
            self.assertFalse((target / "v13" / "subdir" / "leak").exists())

    def test_directory_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "build"
            for subtree in deploy.COPY_SUBTREES:
                (source / subtree).mkdir(parents=True, exist_ok=True)
            (source / "v13" / "outside").symlink_to(root, target_is_directory=True)
            with self.assertRaises(deploy.RuntimeDeployError):
                deploy._copy(source, target)

    def test_cli_uses_real_phone_runtime_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(deploy.Path, "home", return_value=Path(tmp)):
                with patch.object(deploy, "deploy", return_value={"status": "UP_TO_DATE"}) as call:
                    self.assertIsNone(deploy.main([]))
            self.assertEqual(call.call_args.args[0], str(Path(tmp) / ".v13-runtime-source"))


if __name__ == "__main__":
    unittest.main()
