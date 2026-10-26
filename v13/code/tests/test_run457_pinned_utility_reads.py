"""Run457: adversarial post-verification read tests (software/synthetic only)."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run456_native252_utility as audit


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(obj):
    return (json.dumps(obj, sort_keys=True) + "\n").encode()


class PinnedUtilityReads(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "safe"
        self.root.mkdir()
        self.copied = {}
        completed = {}
        for arm, seed in audit.IDS:
            rid = f"{arm}_s{seed}"
            attempt = f"attempts/{rid}/attempt-1"
            completed[rid] = {"attempt": attempt}
            self.write(attempt + f"/tool_{rid}.json",
                       dump({"utility": {"O": .2, "P": .6, "S": .4}[arm]}))
        self.write("RUN397_PROGRESS.json", dump({"completed": completed}))
        self.manifest_path = self.root / audit.verified252.gate.MANIFEST
        self.manifest_path.write_bytes(dump({"copied": self.copied}))
        self.checked = {
            "status": "RUN453_NATIVE_252_INDEPENDENTLY_VERIFIED",
            "rows_verified": 252,
            "manifest_sha256": sha(self.manifest_path.read_bytes()),
            "progress_sha256": self.copied["RUN397_PROGRESS.json"]["sha256"],
            "receipt_sha256": {f"{arm}_s{seed}": "a" * 64
                               for arm, seed in audit.IDS},
        }

    def write(self, rel, data):
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self.copied[rel] = {"bytes": len(data), "sha256": sha(data)}
        return target

    def run_audit(self, mutation=None):
        def verified(root, report):
            self.assertEqual(Path(root), self.root)
            if mutation:
                mutation()
            return self.checked

        def rows(tool, expected, label):
            return {key: {"score": {"utility": tool["utility"]}}
                    for key in expected}

        with (patch.object(audit.verified252, "verify", side_effect=verified),
              patch.object(audit, "validated_rows", side_effect=rows)):
            return audit.analyze(self.root, {})

    def test_unchanged_attested_export_is_readable_without_gate_promotion(self):
        result = self.run_audit()
        self.assertEqual(result["rows_verified"], 252)
        self.assertFalse(result["canonical_gate_pass"])
        self.assertEqual(result["step2_exit"], "UTILITY_FAIL")
        for variant in audit.VARIANTS:
            self.assertAlmostEqual(result["paired_differences"]
                                   ["pointer_minus_off"][variant]["mean"], .4)

    def test_post_verify_same_size_tool_tamper_is_refused(self):
        path = self.root / "attempts/O_s20/attempt-1/tool_O_s20.json"
        def tamper():
            data = path.read_bytes()
            self.assertIn(b"0.2", data)
            path.write_bytes(data.replace(b"0.2", b"0.8"))
        with self.assertRaisesRegex(ValueError, "PINNED_READ_HASH_CHANGED"):
            self.run_audit(tamper)

    def test_post_verify_progress_tamper_is_refused(self):
        path = self.root / "RUN397_PROGRESS.json"
        def tamper():
            data = path.read_bytes()
            path.write_bytes(data.replace(b"O_s20", b"X_s20"))
        with self.assertRaisesRegex(ValueError, "PINNED_READ_HASH_CHANGED"):
            self.run_audit(tamper)

    def test_post_verify_manifest_tamper_is_refused(self):
        def tamper():
            self.manifest_path.write_bytes(dump({"copied": {}}))
        with self.assertRaisesRegex(ValueError, "PINNED_READ_"):
            self.run_audit(tamper)

    def test_post_verify_symlink_swap_is_refused(self):
        path = self.root / "attempts/O_s20/attempt-1/tool_O_s20.json"
        other = Path(self.tmp.name) / "outside.json"
        other.write_bytes(path.read_bytes())
        def tamper():
            path.unlink()
            path.symlink_to(other)
        with self.assertRaises(OSError):
            self.run_audit(tamper)

    def test_post_verify_directory_symlink_swap_is_refused(self):
        original = self.root / "attempts/O_s20/attempt-1"
        other = Path(self.tmp.name) / "outside"
        def tamper():
            original.rename(other)
            original.symlink_to(other, target_is_directory=True)
        with self.assertRaises(OSError):
            self.run_audit(tamper)

    def test_post_verify_hardlink_swap_is_refused(self):
        path = self.root / "attempts/O_s20/attempt-1/tool_O_s20.json"
        other = Path(self.tmp.name) / "hardlink"
        def tamper():
            os.link(path, other)
        with self.assertRaisesRegex(ValueError, "PINNED_READ_FILE_UNSAFE"):
            self.run_audit(tamper)

    def test_pinned_reader_rejects_path_and_unpinned_inputs(self):
        with self.assertRaisesRegex(ValueError, "UNSAFE_EXPORT_PATH"):
            audit.read_pinned(self.root, "../escape", "a" * 64)
        with self.assertRaisesRegex(ValueError, "PINNED_READ_SHA_REQUIRED"):
            audit.read_pinned(self.root, "RUN397_PROGRESS.json", "not-a-sha")
        with self.assertRaisesRegex(ValueError, "PINNED_READ_SIZE_INVALID"):
            audit.read_pinned(self.root, "RUN397_PROGRESS.json",
                              self.checked["progress_sha256"], True)


if __name__ == "__main__":
    unittest.main()
